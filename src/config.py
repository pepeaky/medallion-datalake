import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def get_config() -> dict:
    return {
        "lake_root": os.getenv("LAKE_ROOT", "lake"),
        "input_dir": os.getenv("INPUT_DIR", "data/raw"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
    }
