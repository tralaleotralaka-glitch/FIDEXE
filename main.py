"""Entry point used by PyInstaller: python main.py"""
from __future__ import annotations

import sys

from app.main import main

if __name__ == "__main__":
    sys.exit(main())
