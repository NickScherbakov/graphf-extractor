import networkx as nx
import os
import requests
import base64
import logging

logger = logging.getLogger(__name__)

def extract_graph_structure(image_path: str, model_id: str, api_key: str, api_base_url: str):
    """
    Отправляет изображение графа на API (OpenAI-compatible) с промптом для извлечения вершин и рёбер.
    Использует указанную модель.
    Возвращает nodes, edges или None, None в случае ошибки.
    """
    api_url = f"{api_base_url}/chat/completions"
    logger.info(f"Using model '{model_id}' for graph extraction via {api_url}.")

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
        logger.debug(f"Sending request to {api_url} with model {model_id}")
        response = requests.post(api_url, headers=headers, json=data, timeout=120)
        logger.debug(f"Received response status: {response.status_code}")
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        logger.debug(f"Received content: {content[:100]}...")
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return None, None
    except (KeyError, IndexError, TypeError) as e:
         logger.error(f"Failed to parse API response structure: {e}. Response: {response.text}")
         return None, None
    except Exception as e:
        logger.error(f"An unexpected error occurred during API call: {e}")
        return None, None

    local_vars = {}
    try:
        logger.debug("Attempting to execute received content.")
        if "nodes =" not in content or "edges =" not in content:
             raise ValueError("Response does not contain expected 'nodes =' or 'edges =' assignments.")
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

def adjacency_matrix_from_edges(nodes, edges):
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