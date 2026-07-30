import argparse
import sys

from .collector import SafeStop, collect
from .config import ConfigError, load_config


def main():
    parser = argparse.ArgumentParser(description="Read-only Discord Selenium collector via an existing Edge CDP session.")
    parser.add_argument("command", choices=("validate", "collect"))
    parser.add_argument("--config", required=True)
    parser.add_argument("--refresh-source-names", help="comma-separated configured source names to recrawl and replace by message ID")
    parser.add_argument("--refresh-forum-catalogs", help="comma-separated Forum source names to rescan cards without recrawling completed threads")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.command == "validate": print("Configuration is valid.")
        else: collect(
            config,
            {name.strip() for name in (args.refresh_source_names or "").split(",") if name.strip()},
            {name.strip() for name in (args.refresh_forum_catalogs or "").split(",") if name.strip()},
        )
    except (ConfigError, SafeStop) as exc:
        print(f"Stopped safely: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__": raise SystemExit(main())
