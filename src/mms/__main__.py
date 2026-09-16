from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.logger import get_logger, LogConfig

from .config import AppConfig
from .main import main

if __name__ == "__main__":
    main()