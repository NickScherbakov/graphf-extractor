# graph_pipeline/main.py

import argparse
import logging
import sys

from graph_pipeline import __version__
from graph_pipeline.api import update_model_cache

logger = logging.getLogger(__name__)


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Graph Pipeline - " + __version__, allow_abbrev=False
    )
    parser.add_argument(
        "--api-base-url",
        type=str,
        help="Base URL for the API",
        default="https://api.graphpipeline.io",
    )
    parser.add_argument(
        "--api-key", type=str, help="API key for authentication", required=True
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update the model cache, ignoring any checks",
    )
    parser.add_argument(
        "--skip-vision-check",
        action="store_true",
        help="Skip the vision model availability check",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subparser for the "update-models" command
    update_parser = subparsers.add_parser("update-models", help="Update model cache")

    # Subparser for the "run" command
    run_parser = subparsers.add_parser("run", help="Run the graph pipeline")

    args = parser.parse_args(args)

    logging.basicConfig(level=logging.INFO)

    if args.command == "update-models":
        logger.info("Updating model cache...")
        try:
            # Corrected call: removing scrape_docs
            update_model_cache(
                api_base_url=args.api_base_url,
                api_key=args.api_key,
                force_update=args.force,
                check_vision=not args.skip_vision_check
                # The line with scrape_docs is removed here.
            )
            logger.info("Model cache update process finished.")
        except Exception as e:
             logger.error(f"Error during model cache update: {e}", exc_info=True)
             sys.exit(1)

    elif args.command == "run":
        # ...existing code...