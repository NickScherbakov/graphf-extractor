import networkx as nx
import os
import requests
import base64
import logging
import sys
from typing import List, Tuple, Optional, Any, Union
import numpy as np
from datetime import datetime

# Импортируем наш собственный логгер
try:
    from graph_pipeline.logger import (
        log_api_call, safe_api_call, log_function_calls, 
        log_code_change, check_api_budget, api_cost_warning
    )
    CUSTOM_LOGGER_ENABLED = True
except ImportError:
    CUSTOM_LOGGER_ENABLED = False
    print("⚠️ Система мониторинга API-вызовов недоступна", file=sys.stderr)

# Базовый логгер для совместимости с существующим кодом
logger = logging.getLogger(__name__)

@log_function_calls(category="API_REQUEST") if CUSTOM_LOGGER_ENABLED else lambda x: x
@safe_api_call(
    model_id="default",  # Будет перезаписано фактическим model_id из аргумента
    estimated_input_tokens=1000,  # Оценка токенов для изображения и текстового запроса
    estimated_output_tokens=200,  # Оценка токенов для ответа
    budget_limit=5.0,  # Лимит бюджета по умолчанию
    require_user_approval=True  # Требовать подтверждение пользователя
) if CUSTOM_LOGGER_ENABLED else lambda *args, **kwargs: lambda x: x
def extract_graph_structure(image_path: str, model_id: str, api_key: str, api_base_url: str) -> Tuple[Optional[List[Any]], Optional[List[Tuple[Any, Any]]]]:
    """
    Отправляет изображение графа на API (OpenAI-compatible) с промптом для извлечения вершин и рёбер.
    Использует указанную модель.
    Возвращает nodes, edges или None, None в случае ошибки.
    
    Внимание: Эта операция использует платный API, стоимость зависит от выбранной модели!
    """
    api_url = f"{api_base_url}/chat/completions"
    logger.info(f"Using model '{model_id}' for graph extraction via {api_url}.")
    
    # Предупреждение о потенциально дорогой операции
    if CUSTOM_LOGGER_ENABLED:
        api_cost_warning(model_id, estimated_tokens=1200)  # ~1000 на изображение и 200 на ответ

    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        logger.error(f"Image file not found: {image_path}")
        return None, None
    except Exception as e:
        logger.error(f"Error reading or encoding image {image_path}: {e}")
        return None, None

    prompt = (
        "На изображении представлен неориентированный граф. "
        "Определи список вершин и рёбер графа в формате Python:\\n"
        "nodes = [...]; edges = [...]\\n"
        "В ответе выведи только корректный валидный Python-код без пояснений."
    )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "Ты — эксперт по анализу графов."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]}
        ],
        "max_tokens": 512
    }

    try:
        # Запись события начала API-запроса
        start_time = datetime.now()
        request_id = f"api_req_{start_time.strftime('%Y%m%d%H%M%S')}"
        
        logger.debug(f"Sending request to {api_url} with model {model_id}")
        
        # Делаем запрос к API
        response = requests.post(api_url, headers=headers, json=data, timeout=120)
        
        # Логируем статус ответа
        logger.debug(f"Received response status: {response.status_code}")
        response.raise_for_status()
        
        # Извлекаем содержимое ответа
        content = response.json()["choices"][0]["message"]["content"]
        logger.debug(f"Received content: {content[:100]}...")
        
        # Логируем успешное завершение API-запроса
        if CUSTOM_LOGGER_ENABLED:
            # Примерная оценка размера токенов
            input_tokens = len(img_b64) // 100  # Очень грубая оценка токенов для изображения
            output_tokens = len(content) // 4    # Примерная оценка (1 токен ≈ 4 символа)
            
            log_api_call(
                model_id=model_id,
                tokens_input=input_tokens,
                tokens_output=output_tokens
            )
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        if CUSTOM_LOGGER_ENABLED:
            log_api_call(model_id=model_id, tokens_input=0, tokens_output=0)  # Логируем неудачный запрос
        return None, None
    except (KeyError, IndexError, TypeError) as e:
         logger.error(f"Failed to parse API response structure: {e}. Response: {response.text}")
         if CUSTOM_LOGGER_ENABLED:
             log_api_call(model_id=model_id, tokens_input=len(img_b64) // 100, tokens_output=0)
         return None, None
    except Exception as e:
        logger.error(f"An unexpected error occurred during API call: {e}")
        if CUSTOM_LOGGER_ENABLED:
            log_api_call(model_id=model_id, tokens_input=0, tokens_output=0)
        return None, None

    local_vars = {}
    try:
        logger.debug("Attempting to execute received content.")
        if "nodes =" not in content or "edges =" not in content:
            error_msg = "Response does not contain expected 'nodes =' or 'edges =' assignments."
            logger.error(error_msg)
            if CUSTOM_LOGGER_ENABLED:
                log_code_change(
                    file_path="API_RESPONSE", 
                    function_name="extract_graph_structure", 
                    description=f"Некорректный формат ответа API: {error_msg}",
                    change_type="ERROR"
                )
            raise ValueError(error_msg)
        exec(content, {}, local_vars)
        nodes = local_vars.get("nodes")
        edges = local_vars.get("edges")
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise TypeError("Parsed 'nodes' or 'edges' are not lists.")
        logger.debug(f"Successfully parsed nodes: {nodes}, edges: {edges}")
    except Exception as e:
        logger.error(f"Ошибка разбора ответа модели: {e}\\nОтвет: {content}")
        return None, None

    return nodes, edges

def adjacency_matrix_from_edges(nodes: List[Any], edges: List[Tuple[Any, Any]]) -> np.ndarray:
    G = nx.Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    adj_matrix = nx.adjacency_matrix(G, nodelist=nodes).todense()
    return adj_matrix

if __name__ == "__main__":
    import sys
    nodes, edges = extract_graph_structure(sys.argv[1])
    print("Вершины:", nodes)
    print("Рёбра:", edges)
    adj = adjacency_matrix_from_edges(nodes, edges)
    print("Матрица смежности:\n", adj)