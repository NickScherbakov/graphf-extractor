import os
import json
import requests
import base64
import time
import re
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import logging
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_FILE = "model_cache.json"
CACHE_EXPIRY_HOURS = 24
DEFAULT_API_BASE_URL = "https://gptunnel.ru/v1"

# Minimal image for testing vision capability (1x1 white pixel PNG)
TINY_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/wcAAwAB/epv2AAAAABJRU5ErkJggg=="

def load_api_key(env_path: str = ".env") -> Optional[str]:
    """Loads the OpenAI API key from the .env file."""
    load_dotenv(dotenv_path=env_path)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning(f"OPENAI_API_KEY not found in {env_path}")
    return api_key

def get_available_models(api_base_url: str, api_key: str) -> Optional[List[Dict[str, Any]]]:
    """Fetches the list of available models from the API."""
    headers = {"Authorization": f"Bearer {api_key}"}
    models_url = f"{api_base_url}/models"
    try:
        response = requests.get(models_url, headers=headers, timeout=15)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching models from {models_url}: {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON response from {models_url}")
        return None

def check_vision_capability(model_id: str, api_base_url: str, api_key: str) -> bool:
    """
    Attempts to send a minimal vision request to check if the model supports it.
    Returns True if the model likely supports vision, False otherwise.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    chat_url = f"{api_base_url}/chat/completions"
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{TINY_PNG_BASE64}"
                        },
                    },
                ],
            }
        ],
        "max_tokens": 10, # Keep the request minimal
    }
    try:
        response = requests.post(chat_url, headers=headers, json=payload, timeout=30)
        # Check for specific errors indicating lack of vision support if possible,
        # otherwise assume success means vision is supported.
        # A 400 Bad Request might indicate the model doesn't support the image format/input type.
        if response.status_code == 400:
             # Try to inspect the error message if available
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "").lower()
                if "image" in error_msg or "vision" in error_msg or "input type" in error_msg:
                    logger.info(f"Model {model_id} likely does not support vision (API error: {response.status_code} - {error_msg})")
                    return False
            except json.JSONDecodeError:
                 logger.warning(f"Model {model_id} returned 400 Bad Request, potentially no vision support, but couldn't parse error details.")
                 return False # Assume no vision on ambiguous 400

        response.raise_for_status() # Raise for other errors (5xx, 401, 403 etc.)
        logger.info(f"Model {model_id} successfully processed a vision request.")
        return True
    except requests.exceptions.RequestException as e:
        # Handle specific errors if needed, e.g., timeout, connection error
        logger.warning(f"Could not confirm vision capability for {model_id} due to request error: {e}")
        return False # Cannot confirm vision capability
    except Exception as e:
        logger.error(f"Unexpected error checking vision for {model_id}: {e}")
        return False


def load_model_cache(cache_path: str = CACHE_FILE) -> Dict[str, Any]:
    """Loads the model cache from a JSON file."""
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading cache file {cache_path}: {e}. Returning empty cache.")
            return {"last_updated": None, "models": {}} # Return dict for models
    return {"last_updated": None, "models": {}} # Return dict for models

def save_model_cache(cache_data: Dict[str, Any], cache_path: str = CACHE_FILE):
    """Saves the model cache to a JSON file.""" # Corrected docstring format
    try:
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except IOError as e:
        logger.error(f"Error saving cache file {cache_path}: {e}")


def update_model_cache(api_base_url: str, api_key: str, force_update: bool = False, check_vision: bool = True, cache_path: str = CACHE_FILE) -> Dict[str, Any]:
    """
    Loads, updates (if necessary), and saves the model cache.
    Checks vision capabilities for new models if check_vision is True.
    Returns the updated cache data.
    """ # Corrected docstring format
    cache_data = load_model_cache(cache_path)
    models_dict = cache_data.get("models", {}) # Use dict: {model_id: model_data}
    last_updated_str = cache_data.get("last_updated")

    needs_update = force_update
    if not needs_update and last_updated_str:
        try:
            last_updated_dt = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) - last_updated_dt > timedelta(hours=CACHE_EXPIRY_HOURS):
                needs_update = True
                logger.info("Model cache expired. Refreshing.")
        except ValueError:
            logger.warning("Invalid date format in cache. Forcing refresh.")
            needs_update = True
    elif not last_updated_str:
        needs_update = True
        logger.info("No existing cache found or no last_updated time. Fetching models.")

    if not needs_update:
        logger.info("Model cache is up-to-date.")
        return cache_data # Return the loaded cache directly

    logger.info("Fetching available models from API...")
    fetched_models = get_available_models(api_base_url, api_key)

    if fetched_models is None:
        logger.error("Failed to fetch models from API. Returning potentially stale cache.")
        return cache_data # Return old cache if fetch failed

    logger.info(f"Fetched {len(fetched_models)} models from the API.")
    new_models_checked = 0
    updated_models_dict = {}
    total_models = len(fetched_models)

    for i, model_info in enumerate(fetched_models):
        model_id = model_info.get("id")
        if not model_id:
            continue

        existing_model_data = models_dict.get(model_id)

        # Preserve existing vision info if already checked unless force_update
        has_vision = existing_model_data.get("has_vision") if existing_model_data else None
        # Use "vision_checked" consistently
        vision_checked = existing_model_data.get("vision_checked", False) if existing_model_data else False

        # --- Vision Check Logic ---
        # Check vision only if check_vision is enabled AND (it's a new model OR force_update is true and it wasn't checked before)
        should_check_vision = check_vision and (existing_model_data is None or (force_update and not vision_checked))

        if should_check_vision:
            # Add a delay before checking vision capability to avoid rate limits
            if new_models_checked > 0: # Don't sleep before the very first check
                logger.debug(f"Waiting 1 second before checking next model ({i+1}/{total_models})...")
                time.sleep(1) # Sleep for 1 second

            logger.info(f"Checking vision capability via API for model: {model_id} ({i+1}/{total_models})...")
            has_vision = check_vision_capability(model_id, api_base_url, api_key)
            vision_checked = True # Mark as checked after the attempt
            new_models_checked += 1
        # If vision_checked is True from cache, keep the existing has_vision value unless force_update triggered a re-check above.
        # If check_vision is False, vision_checked remains False (or its cached value), and has_vision remains None (or its cached value).

        # Prepare the updated entry for the model
        current_model_data = {
            **model_info, # Add all fetched info from /v1/models (includes cost_context, cost_completion, title etc.)
            "has_vision": has_vision, # Use the determined/cached vision status
            "vision_checked": vision_checked, # Track if API check was done for this model in this run or previously
            "last_seen": datetime.now(timezone.utc).isoformat() + "Z"
        }
        # Clean up None values before saving (optional, but keeps cache cleaner)
        updated_models_dict[model_id] = {k: v for k, v in current_model_data.items() if v is not None}


    if new_models_checked > 0:
        logger.info(f"Checked vision capability for {new_models_checked} models.")

    new_cache_data = {
        "last_updated": datetime.now(timezone.utc).isoformat() + "Z",
        "models": updated_models_dict
    }

    save_model_cache(new_cache_data, cache_path)
    logger.info(f"Model cache updated and saved to {cache_path}")
    return new_cache_data


def get_vision_models(api_base_url: Optional[str] = None, api_key: Optional[str] = None, force_update: bool = False, check_vision: bool = True, cache_path: str = CACHE_FILE, env_path: str = ".env") -> List[Dict[str, Any]]:
    """
    Ensures the cache is updated and returns a list of model dictionaries
    that are believed to support vision.

    Returns:
        List of model dictionaries (containing id, costs, etc.) that support vision.
        Returns an empty list if no API key is found or no vision models are identified.
    """ # Corrected docstring format
    used_api_key = api_key or load_api_key(env_path)
    used_api_base_url = api_base_url or DEFAULT_API_BASE_URL

    if not used_api_key:
        logger.error("API key is required to get vision models.")
        return []
    if not used_api_base_url:
        logger.error("API base URL is required.")
        return []

    # Update cache (pass check_vision parameter)
    cache_data = update_model_cache(used_api_base_url, used_api_key, force_update=force_update, check_vision=check_vision, cache_path=cache_path)

    vision_models_list = []
    models_dict = cache_data.get("models", {})
    for model_id, model_data in models_dict.items():
        # Primary check: has_vision flag determined by API check (if performed and successful)
        if model_data.get("vision_checked") and model_data.get("has_vision") is True: # Explicitly check for True
             # Ensure cost data exists before adding
             if "cost_context" in model_data and "cost_completion" in model_data:
                 vision_models_list.append(model_data) # Add the full model data dict
             else:
                 logger.warning(f"Model {model_id} confirmed vision but missing cost data. Skipping.")
        # Fallback/Alternative: If vision check wasn't performed OR wasn't conclusive
        elif not model_data.get("vision_checked") or model_data.get("has_vision") is None:
             # Use name heuristic only if API check didn't confirm vision status
             name_suggests_vision = any(hint in model_id.lower() for hint in ["vision", "4o", "pixtral", "grok", "jamba", "o1", "o3", "o4"]) # Expanded heuristics
             if name_suggests_vision:
                 # Only add if not already added and vision wasn't explicitly confirmed as False
                 if model_data.get("has_vision") is not False:
                     # Ensure cost data exists before adding
                     if "cost_context" in model_data and "cost_completion" in model_data:
                         logger.warning(f"Vision capability for {model_id} wasn't confirmed via API check, but name suggests vision. Including it.")
                         vision_models_list.append(model_data) # Add the full model data dict
                     else:
                          logger.warning(f"Model {model_id} suggested vision by name but missing cost data. Skipping.")


    if not vision_models_list:
        logger.warning("No models confirmed or suspected to have vision capabilities (with cost data) were found.")

    # Return the list of model dictionaries
    return vision_models_list


if __name__ == "__main__":
    # Example usage when running the script directly
    print("Testing Model Manager...")
    key = load_api_key()
    if key:
        print("\\n--- Updating Cache (Force Update, Check Vision) ---")
        updated_cache = update_model_cache(DEFAULT_API_BASE_URL, key, force_update=True, check_vision=True)
        # print(json.dumps(updated_cache, indent=2)) # Keep commented unless debugging

        print("\\n--- Getting Vision Models (from updated cache, check_vision=True) ---")
        # Now returns list of dicts
        vision_models_data = get_vision_models(api_base_url=DEFAULT_API_BASE_URL, api_key=key, check_vision=True, force_update=False) # Use cache
        if vision_models_data:
            print(f"Found {len(vision_models_data)} vision models (checked). Example: {vision_models_data[0]['id']}")
            # print(json.dumps(vision_models_data, indent=2)) # Keep commented unless debugging
        else:
            print("No vision models found (checked).")


        print("\\n--- Getting Vision Models (using cache, no force update, no vision check - name heuristic only) ---")
        # This will use the cache, and only name heuristics if check_vision=False
        vision_models_heuristic = get_vision_models(api_base_url=DEFAULT_API_BASE_URL, api_key=key, force_update=False, check_vision=False)
        if vision_models_heuristic:
             print(f"Found {len(vision_models_heuristic)} vision models (heuristic). Example: {vision_models_heuristic[0]['id']}")
             # print(json.dumps(vision_models_heuristic, indent=2)) # Keep commented unless debugging
        else:
             print("No vision models found (heuristic).")

    else:
        print("Skipping API tests as OPENAI_API_KEY is not set in .env")

