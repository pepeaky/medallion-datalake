"""CLI for the Medallion Data Lake."""

import argparse
import json
import logging

from src.config import get_config
from src.bronze import ingest
from src.silver import refine
from src.gold import aggregate


def cmd_run(args):
    cfg = get_config()
    lake = args.lake or cfg["lake_root"]
    input_dir = args.input or cfg["input_dir"]

    stages = args.stages.split(",") if args.stages else ["bronze", "silver", "gold"]

    for stage in stages:
        if stage == "bronze":
            result = ingest(input_dir, lake)
        elif stage == "silver":
            result = refine(lake)
        elif stage == "gold":
            result = aggregate(lake)
        else:
            print(f"Unknown stage: {stage}")
            continue
        print(json.dumps(result, indent=2))


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Medallion Data Lake Pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run lake pipeline")
    p_run.add_argument("--lake", help="Lake root directory")
    p_run.add_argument("--input", help="Raw input directory")
    p_run.add_argument("--stages", help="Comma-separated stages: bronze,silver,gold")

    args = parser.parse_args()
    {"run": cmd_run}[args.command](args)


if __name__ == "__main__":
    main()
