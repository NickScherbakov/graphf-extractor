import networkx as nx
import os
import requests
import base64

def extract_graph_structure(image_path):
    """
    Отправляет изображение графа на gptunnel.ru (OpenAI-compatible API) с промптом для извлечения вершин и рёбер.
    Возвращает nodes, edges.
    """
    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-...your-key...")
    api_url = "https://gptunnel.ru/v1/chat/completions"
    # Кодируем изображение в base64
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    # Формируем промпт для GPT
    prompt = (
        "На изображении представлен неориентированный граф. "
        "Определи список вершин и рёбер графа в формате Python:\n"
        "nodes = [...]; edges = [...]\n"
        "В ответе выведи только корректный валидный Python-код без пояснений."
    )
    # Формируем запрос
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {"role": "system", "content": "Ты — эксперт по анализу графов."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]}
        ],
        "max_tokens": 512
    }
    response = requests.post(api_url, headers=headers, json=data, timeout=120)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    # Парсим nodes и edges из ответа
    local_vars = {}
    try:
        exec(content, {}, local_vars)
        nodes = local_vars["nodes"]
        edges = local_vars["edges"]
    except Exception as e:
        raise RuntimeError(f"Ошибка разбора ответа GPT: {e}\nОтвет: {content}")
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