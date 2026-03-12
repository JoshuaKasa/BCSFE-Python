"""Backward-compatible entrypoint for older scripts.

Use run_web_ui.py for the new, canonical web UI server entrypoint.
"""

from __future__ import annotations

from run_web_ui import main


if __name__ == "__main__":
    main()
