"""Read-only Discord collector attached to an already logged-in Edge session."""

from pathlib import Path
import socket
import time
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from . import selectors
from .manifest import build_manifest
from .parsing import parse_forum_posts, parse_text_messages
from .storage import Checkpoint, atomic_write_json, merge_records, read_records


class SafeStop(RuntimeError):
    pass


def should_stop(empty_scrolls, max_empty_scrolls, reached_limit):
    return reached_limit or empty_scrolls >= max_empty_scrolls


def _driver(cdp_url: str):
    parsed = urlparse(cdp_url)
    try:
        with socket.create_connection((parsed.hostname, parsed.port), timeout=2):
            pass
    except OSError as exc:
        raise SafeStop("Existing Edge CDP session is unavailable; start start_edge.ps1, log in to Discord, then rerun.") from exc
    options = Options()
    options.add_experimental_option("debuggerAddress", f"{parsed.hostname}:{parsed.port}")
    try:
        return webdriver.Edge(options=options)
    except WebDriverException as exc:
        raise SafeStop(f"Cannot attach Selenium to the existing Edge CDP session: {exc.msg}") from exc


def _check_access(driver):
    text = driver.find_element(By.TAG_NAME, "body").text.lower()
    phrases = ("login to discord", "verify you are human", "captcha", "access denied", "you must be logged")
    if any(phrase in text for phrase in phrases):
        raise SafeStop("Discord login, permission, or security check detected; progress was saved.")


def _open(driver, url: str, selector: str):
    driver.get(url)
    try:
        WebDriverWait(driver, 30).until(lambda browser: browser.find_elements(By.CSS_SELECTOR, selector))
    except TimeoutException as exc:
        raise SafeStop(f"Configured Discord URL did not expose the expected read-only view: {url}") from exc


def _scroll_up(driver):
    return bool(driver.execute_script("""
        let element = document.querySelector(arguments[0]);
        while (element) {
            const overflow = getComputedStyle(element).overflowY;
            if ((overflow === "auto" || overflow === "scroll") && element.scrollHeight > element.clientHeight) break;
            element = element.parentElement;
        }
        if (!element) return false;
        const before = element.scrollTop;
        const delta = Math.max(1, Math.floor(element.clientHeight * 0.8));
        element.focus({preventScroll: true});
        element.dispatchEvent(new WheelEvent("wheel", {bubbles: true, cancelable: true, deltaY: -delta}));
        element.scrollBy({top: -delta, behavior: "instant"});
        element.dispatchEvent(new Event("scroll", {bubbles: true}));
        return before !== element.scrollTop;
    """, selectors.SCROLL_CONTAINER))


def _scroll_forum(driver, channel_id):
    return bool(driver.execute_script("""
        const element = document.querySelector(`[data-list-id="${arguments[0]}"]`);
        if (!element || element.scrollHeight <= element.clientHeight) return false;
        const before = element.scrollTop;
        const delta = Math.max(1, Math.floor(element.clientHeight * 0.8));
        element.focus({preventScroll: true});
        element.dispatchEvent(new WheelEvent("wheel", {bubbles: true, cancelable: true, deltaY: delta}));
        element.scrollBy({top: delta, behavior: "instant"});
        element.dispatchEvent(new Event("scroll", {bubbles: true}));
        return before !== element.scrollTop;
    """, f"forum-channel-list-{channel_id}"))


def _scroll_forum_top(driver, channel_id):
    driver.execute_script("""
        const element = document.querySelector(`[data-list-id="${arguments[0]}"]`);
        if (element) {
            element.scrollTop = 0;
            element.dispatchEvent(new Event("scroll", {bubbles: true}));
        }
    """, f"forum-channel-list-{channel_id}")


def _set_forum_sort(driver, channel_id, sort_id):
    """Switch only the local Forum view so both Discord catalog orders are read."""
    _scroll_forum_top(driver, channel_id)
    option = driver.find_elements(By.ID, sort_id)
    if not option:
        button = WebDriverWait(driver, 30).until(lambda browser: browser.find_elements(By.CSS_SELECTOR, selectors.FORUM_SORT_BUTTON))[0]
        driver.execute_script("arguments[0].click()", button)
        option = WebDriverWait(driver, 30).until(lambda browser: browser.find_elements(By.ID, sort_id))
    if option[0].get_attribute("aria-checked") != "true":
        driver.execute_script("arguments[0].click()", option[0])


def _scan_report(new_post_counts):
    return {"passes": len(new_post_counts), "new_post_counts": new_post_counts, "converged": len(new_post_counts) >= 2 and new_post_counts[-1] == 0}


def _collect_messages(driver, channel, output_file: Path, checkpoint, pause, maximum_empty, complete_channel=True, refresh=False, message_channel_id=None, open_url=True):
    if open_url:
        _open(driver, channel.url, selectors.MESSAGE_LIST)
    else:
        WebDriverWait(driver, 30).until(lambda browser: browser.find_elements(By.CSS_SELECTOR, selectors.MESSAGE_LIST))
    message_channel_id = message_channel_id or channel.channel_id
    empty = 0
    while True:
        _check_access(driver)
        records = parse_text_messages(driver.page_source, channel.name, message_channel_id, channel.guild_id)
        visible_ids = {record["message_id"] for record in records}
        existing = read_records(output_file)
        merged = merge_records(existing, reversed(records), channel.limit if channel.mode == "latest_messages" else None, replace_existing=refresh)
        atomic_write_json(output_file, merged)
        for record in merged:
            checkpoint.add(message_channel_id, record["message_id"])
        checkpoint.target(channel.name).save()
        reached_limit = channel.limit is not None and len(merged) >= channel.limit
        moved = _scroll_up(driver)
        if not moved:
            break
        time.sleep(pause)
        after_ids = {record["message_id"] for record in parse_text_messages(driver.page_source, channel.name, message_channel_id, channel.guild_id)}
        empty = empty + 1 if after_ids == visible_ids else 0
        if should_stop(empty, maximum_empty, reached_limit):
            break
    if complete_channel:
        checkpoint.complete(channel.name).save()


def _forum_posts(driver, channel, pause, maximum_empty):
    if channel.mode == "latest_posts":
        return _usable_forum_posts(channel, parse_forum_posts(driver.page_source, channel.post_limit)), {"passes": 1, "new_post_counts": [], "converged": True}
    posts, scans = {}, {}
    for sort_id in selectors.FORUM_SORT_IDS:
        _set_forum_sort(driver, channel.channel_id, sort_id)
        new_post_counts = []
        for _ in range(2):
            _scroll_forum_top(driver, channel.channel_id)
            time.sleep(pause * 2)
            before = len(posts)
            while True:
                visible = _usable_forum_posts(channel, parse_forum_posts(driver.page_source, None))
                posts.update({post["thread_id"]: post | {"_sort_id": sort_id} for post in visible})
                if not _scroll_forum(driver, channel.channel_id):
                    time.sleep(pause * 2)
                    visible = _usable_forum_posts(channel, parse_forum_posts(driver.page_source, None))
                    posts.update({post["thread_id"]: post | {"_sort_id": sort_id} for post in visible})
                    break
                time.sleep(pause)
            new_post_counts.append(len(posts) - before)
        scans[sort_id] = _scan_report(new_post_counts)
    scan = {"sorts": scans, "converged": all(item["converged"] for item in scans.values())}
    return sorted(posts.values(), key=lambda post: post["timestamp"] or "", reverse=True), scan


def _post_url(channel, post):
    return urljoin("https://discord.com", post.get("url") or f"/channels/{channel.guild_id}/{channel.channel_id}/{post['thread_id']}")


def _usable_forum_posts(channel, posts):
    return [post for post in posts if str(post.get("thread_id")) != str(channel.channel_id)]


def _open_forum_post(driver, channel, post, pause, maximum_empty):
    _open(driver, channel.url, selectors.FORUM_LIST)
    _set_forum_sort(driver, channel.channel_id, post["_sort_id"])
    selector = f'[data-list-item-id="forum-channel-list-{channel.channel_id}___{post["thread_id"]}"]'
    while True:
        matches = driver.find_elements(By.CSS_SELECTOR, selector)
        if matches:
            driver.execute_script("arguments[0].click()", matches[0])
            WebDriverWait(driver, 30).until(lambda browser: browser.find_elements(By.CSS_SELECTOR, selectors.MESSAGE_LIST))
            return
        if not _scroll_forum(driver, channel.channel_id):
            break
        time.sleep(pause)
    raise SafeStop(f"{channel.name}: forum post {post['thread_id']} was not available in the configured forum view.")


def _collect_forum(driver, channel, output_directory: Path, checkpoint, pause, maximum_empty, refresh=False):
    _open(driver, channel.url, selectors.FORUM_LIST)
    _check_access(driver)
    posts, scan = _forum_posts(driver, channel, pause, maximum_empty)
    if channel.mode == "latest_posts" and len(posts) < channel.post_limit:
        raise SafeStop(f"{channel.name}: only {len(posts)} visible forum posts; no other channels were explored.")
    catalog_file = output_directory / channel.name / "posts.json"
    catalog = {str(item.get("thread_id")): item for item in read_records(catalog_file) if item.get("thread_id")}
    catalog.update({str(post["thread_id"]): {"thread_id": str(post["thread_id"]), "title": post.get("title"), "url": _post_url(channel, post)} for post in posts})
    atomic_write_json(catalog_file, sorted(catalog.values(), key=lambda item: item["thread_id"]))
    atomic_write_json(output_directory / channel.name / "scan-report.json", scan)
    if channel.mode == "all_posts" and not scan["converged"]:
        raise SafeStop(f"{channel.name}: Forum scan did not converge; catalog was saved but not marked complete.")
    for post in posts:
        post["url"] = _post_url(channel, post)
        target = f"{channel.name}/{post['thread_id']}"
        if target in checkpoint.completed and not refresh:
            continue
        _open_forum_post(driver, channel, post, pause, maximum_empty)
        output_file = output_directory / channel.name / f"{post['thread_id']}.json"
        _collect_messages(driver, channel, output_file, checkpoint, pause, maximum_empty, complete_channel=False, refresh=refresh, message_channel_id=post["thread_id"], open_url=False)
        records = read_records(output_file)
        for record in records:
            record["post_thread_id"], record["post_title"], record["post_url"] = post["thread_id"], post["title"], post["url"]
        atomic_write_json(output_file, records)
        checkpoint.complete(target).save()
    checkpoint.complete(channel.name).save()


def collect(config, refresh_names: set[str] | None = None, catalog_refresh_names: set[str] | None = None):
    """Collect only the configured URLs. It never sends a Discord action."""
    checkpoint = Checkpoint.load(config.checkpoint_file)
    refresh_names = refresh_names or set()
    catalog_refresh_names = catalog_refresh_names or set()
    driver = _driver(config.cdp_url)
    try:
        for channel in config.channels:
            if channel.name in refresh_names:
                checkpoint.reopen(channel.name).save()
            elif channel.type == "forum" and channel.name in catalog_refresh_names:
                checkpoint.reopen(channel.name).save()
            elif channel.type == "forum" and channel.mode == "all_posts" and not (config.output_directory / channel.name / "posts.json").exists():
                checkpoint.reopen(channel.name).save()
            if channel.name in checkpoint.completed:
                continue
            if channel.type == "text":
                _collect_messages(driver, channel, config.output_directory / f"{channel.name}.json", checkpoint, config.scroll_pause_seconds, config.max_empty_scrolls, refresh=channel.name in refresh_names)
            else:
                _collect_forum(driver, channel, config.output_directory, checkpoint, config.scroll_pause_seconds, config.max_empty_scrolls, refresh=channel.name in refresh_names)
    finally:
        checkpoint.save()
        build_manifest(config)
        # Do not call driver.quit(): this is the user's pre-existing Edge session.
        driver.service.stop()
