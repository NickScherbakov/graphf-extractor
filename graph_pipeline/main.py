import argparse
import os
import logging
import sys
import math

# Add project root to sys.path to allow imports from graph_pipeline
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from graph_pipeline.extract_graph_image import extract_images_from_pdf
    from graph_pipeline.graph_structure_extractor import extract_graph_structure, adjacency_matrix_from_edges
    from graph_pipeline.generate_manim_advanced import generate_graph_and_matrix_script
    from graph_pipeline.model_manager import update_model_cache, load_api_key, DEFAULT_API_BASE_URL, get_vision_models
except ImportError as e:
    print(f"ERROR DURING IMPORT: {e}") # Keep this basic error print just in case
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Helper function to calculate cost
def calculate_cost(model_data):
    try:
        # Costs are per 1M tokens in gptunnel API response, convert to float
        cost_context_str = model_data.get("cost_context")
        cost_completion_str = model_data.get("cost_completion")

        # Return infinity if cost data is missing or not a string
        if not isinstance(cost_context_str, str) or not isinstance(cost_completion_str, str):
             logger.warning(f"Missing or invalid type for cost data in model {model_data.get('id', 'N/A')}. Treating as high cost.")
             return math.inf

        cost_context = float(cost_context_str)
        cost_completion = float(cost_completion_str)

        # Simple cost metric: sum of context and completion cost. Adjust if needed.
        # Lower is better.
        return cost_context + cost_completion
    except (ValueError, TypeError) as e:
        # Return infinity if conversion to float fails
        logger.warning(f"Could not parse cost data for model {model_data.get('id', 'N/A')}: {e}. Treating as high cost.")
        return math.inf

def main():
    parser = argparse.ArgumentParser(description="Graph Extraction and Animation Pipeline.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Main pipeline command
    run_parser = subparsers.add_parser("run", help="Run the full graph extraction pipeline")
    run_parser.add_argument("--pdf", required=True, help="Path to the input PDF file.")
    run_parser.add_argument("--page", type=int, default=1, help="Page number in the PDF to process (1-based). Default is 1.")
    run_parser.add_argument("--output-dir", default="pdf_images", help="Directory to save extracted images.")
    run_parser.add_argument("--manim-script-dir", default=".", help="Directory to save the generated Manim script.")
    run_parser.add_argument("--model", type=str, default=None, help="Specify the exact model ID to use for graph extraction.")
    run_parser.add_argument("--api-base-url", type=str, default=DEFAULT_API_BASE_URL, help=f"Base URL for the OpenAI-compatible API (default: {DEFAULT_API_BASE_URL}).")
    run_parser.add_argument("--force-model-update", action="store_true", help="Force refresh of the model cache before running.")
    run_parser.add_argument("--skip-vision-check", action="store_true", help="Skip API check for vision capability (use name heuristics).")
    run_parser.add_argument("--skip-manim", action="store_true", help="Skip generating the Manim script.")


    # Model management command
    model_parser = subparsers.add_parser("update-models", help="Update the local cache of available API models.")
    model_parser.add_argument("--api-base-url", type=str, default=DEFAULT_API_BASE_URL, help=f"Base URL for the OpenAI-compatible API (default: {DEFAULT_API_BASE_URL}).")
    model_parser.add_argument("--force", action="store_true", help="Force update even if cache is not expired.")
    model_parser.add_argument("--skip-vision-check", action="store_true", help="Skip checking vision capability via test API calls.")

    args = parser.parse_args()

    # Load API Key once
    api_key = load_api_key()
    if args.command in ["run", "update-models"] and not api_key:
         logger.error("OPENAI_API_KEY not found in .env file. Cannot proceed with API operations.")
         sys.exit(1)


    if args.command == "update-models":
        logger.info("Updating model cache...")
        try:
            update_model_cache(
                api_base_url=args.api_base_url,
                api_key=api_key,
                force_update=args.force,
                check_vision=not args.skip_vision_check
            )
            logger.info("Model cache update process finished.")
        except Exception as e:
             logger.error(f"Error during model cache update: {e}", exc_info=True)
             sys.exit(1)

    elif args.command == "run":
        logger.info("Starting 'run' command...")
        pdf_path = args.pdf
        page_num = args.page
        output_dir = args.output_dir
        manim_script_dir = args.manim_script_dir

        # --- Step 1: Extract image from PDF ---
        logger.info(f"Extracting image from page {page_num} of {pdf_path}...")
        os.makedirs(output_dir, exist_ok=True)
        try:
            image_paths = extract_images_from_pdf(pdf_path, output_dir=output_dir)
        except Exception as e:
            logger.error(f"Error during image extraction: {e}", exc_info=True)
            sys.exit(1)

        if not image_paths:
             logger.error(f"No images found or extracted from {pdf_path}.")
             sys.exit(1)

        expected_image_name = f"page{page_num}.png"
        image_path = os.path.join(output_dir, expected_image_name)

        if not os.path.exists(image_path):
             logger.error(f"Could not find extracted image '{expected_image_name}' in '{output_dir}'. Found images: {image_paths}")
             sys.exit(1)

        logger.info(f"Using image: {image_path}")

        # --- Step 1.5: Determine Model ID ---
        selected_model_id = args.model
        logger.info(f"User specified model: {selected_model_id}")

        if not selected_model_id:
            logger.info("No specific model requested. Selecting the cheapest available vision model...")
            try:
                available_vision_models = get_vision_models(
                    api_base_url=args.api_base_url,
                    api_key=api_key,
                    force_update=args.force_model_update,
                    check_vision=not args.skip_vision_check
                )
                logger.info(f"Found {len(available_vision_models)} potential vision models.")

                if not available_vision_models:
                    logger.error("No suitable vision models found. Cannot proceed.")
                    sys.exit(1)

                model_costs = []
                for model in available_vision_models:
                    cost = calculate_cost(model) # This should now always return float or inf
                    model_costs.append((cost, model))
                    logger.debug(f"Model: {model.get('id')}, Calculated Cost: {cost}")

                # Filter out models with infinite cost before finding min
                valid_cost_models = [(cost, model) for cost, model in model_costs if cost != math.inf]

                if not valid_cost_models:
                    logger.error("Could not determine valid costs for any available vision models. Cannot select cheapest.")
                    sys.exit(1)

                # This line should now work correctly as cost is always comparable
                min_cost, cheapest_model = min(valid_cost_models, key=lambda item: item[0])

                selected_model_id = cheapest_model.get("id")
                logger.info(f"Selected cheapest model: {selected_model_id} (Cost metric: {min_cost:.4f})")

            except Exception as e:
                logger.error(f"Error during model selection: {e}", exc_info=True)
                sys.exit(1)

        if not selected_model_id:
             logger.error("Could not determine a model ID to use.")
             sys.exit(1)

        # --- Step 2: Extract graph structure using Vision Model ---
        logger.info(f"Attempting to extract graph structure using model: {selected_model_id}...")
        try:
            nodes, edges = extract_graph_structure(
                image_path=image_path,
                model_id=selected_model_id,
                api_key=api_key,
                api_base_url=args.api_base_url
            )
        except Exception as e:
             logger.error(f"Error calling extract_graph_structure: {e}", exc_info=True)
             sys.exit(1)

        logger.info("Returned from extract_graph_structure.")

        if nodes is None or edges is None:
            logger.error("Failed to extract graph structure (extract_graph_structure returned None).")
            sys.exit(1)
        logger.info(f"Extracted Nodes: {nodes}")
        logger.info(f"Extracted Edges: {edges}")

        # --- Step 3: Create Adjacency Matrix ---
        logger.info("Creating graph object...")
        try:
            # Assuming adjacency_matrix_from_edges returns the matrix directly
            adj_matrix = adjacency_matrix_from_edges(nodes, edges)
        except Exception as e:
            logger.error(f"Error creating adjacency matrix: {e}", exc_info=True)
            sys.exit(1)

        if adj_matrix is None: # Check if matrix creation failed
            logger.error("Failed to create adjacency matrix (adjacency_matrix_from_edges returned None).")
            sys.exit(1)
        logger.info("Adjacency matrix created successfully.")
        # Optional: Print matrix
        # print("Adjacency Matrix:\\n", adj_matrix)


        if args.skip_manim:
            logger.info("Skipping Manim script generation as requested.")
            logger.info("Pipeline finished successfully (without Manim script).")
            sys.exit(0)

        # --- Step 4: Generate Manim Script ---
        logger.info("Generating Manim script...")
        os.makedirs(manim_script_dir, exist_ok=True)
        script_filename = f"animate_{os.path.splitext(os.path.basename(pdf_path))[0]}_p{page_num}.py"
        script_path = os.path.join(manim_script_dir, script_filename)

        try: # Add try/except for Manim script generation
            # Pass adj_matrix instead of graph object if generate_graph_and_matrix_script expects it
            success = generate_graph_and_matrix_script(nodes, edges, adj_matrix, script_path)
        except Exception as e:
            logger.error(f"Error generating Manim script: {e}", exc_info=True)
            sys.exit(1)


        if success:
            logger.info(f"Manim script generated successfully: {script_path}")
            logger.info("To render the animation, run:")
            logger.info(f"  bash run_manim.sh {script_path}")
        else:
            logger.error("Failed to generate Manim script (generate_graph_and_matrix_script returned False).")
            sys.exit(1)

        logger.info("Pipeline finished successfully.")

    else:
        logger.error(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            logger.exception("Unhandled exception in main()")
        except NameError:
            import traceback
            traceback.print_exc()
        sys.exit(1)