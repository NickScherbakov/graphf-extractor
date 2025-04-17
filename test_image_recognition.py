#!/usr/bin/env python3
from graph_pipeline.graph_structure_extractor import extract_graph_structure
from graph_pipeline.model_manager import load_api_key, DEFAULT_API_BASE_URL
import sys
import os

def main():
    image_path = "/workspaces/graphf-extractor/testimages/testimage.png"
    print(f"Тестирование распознавания изображения: {image_path}")
    
    # Проверяем существование файла
    if not os.path.exists(image_path):
        print(f"Файл не существует: {image_path}")
        return
    
    # Загружаем API ключ
    api_key = load_api_key()
    if not api_key:
        print("OPENAI_API_KEY не найден в .env файле")
        return
    
    print(f"Запускаем распознавание с моделью: gpt-4o")
    try:
        # Распознаём структуру графа
        nodes, edges = extract_graph_structure(
            image_path=image_path,
            model_id="gpt-4o",  # Используем gpt-4o как модель с vision-возможностями
            api_key=api_key,
            api_base_url=DEFAULT_API_BASE_URL
        )
        
        if nodes is None or edges is None:
            print("Не удалось распознать структуру графа")
            return
        
        print("\nРезультаты распознавания:")
        print(f"Вершины: {nodes}")
        print(f"Рёбра: {edges}")
        
        # Опционально: если нужно создать матрицу смежности
        from graph_pipeline.graph_structure_extractor import adjacency_matrix_from_edges
        adj_matrix = adjacency_matrix_from_edges(nodes, edges)
        print("\nМатрица смежности:")
        print(adj_matrix)
        
    except Exception as e:
        print(f"Ошибка при распознавании: {e}")

if __name__ == "__main__":
    main()
