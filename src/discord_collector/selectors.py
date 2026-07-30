"""All Discord DOM selectors live here; update this module when Discord changes its UI."""

MESSAGE_LIST = '[data-list-id="chat-messages"], ol[aria-label*="Messages"]'
MESSAGE = '[data-list-item-id^="chat-messages-"], [id^="chat-messages-"]'
SCROLL_CONTAINER = '[data-list-id="chat-messages"], ol[aria-label*="Messages"]'
FORUM_POST = 'a[data-thread-id], a[href*="/channels/"]'
FORUM_LIST = '[data-list-id^="forum-channel-list-"]'
FORUM_SORT_BUTTON = 'button[class*="sortDropdown"]'
FORUM_SORT_IDS = ("sort-and-view-sort-by-recent-activity",)
AUTHOR_CLASSES = ("username", "headerText", "messageUsername")
CONTENT_CLASSES = ("message-content", "markup", "messageContent")
