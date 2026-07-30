"""Run the read-only browser-session source crawler and refresh its manifest."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from discord_collector.__main__ import main


if __name__ == "__main__":
    sys.argv.insert(1, "collect")
    raise SystemExit(main())
