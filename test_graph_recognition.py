import os
from PIL import Image
import sys
from graph_recognition import GraphRecognizer

def test_graph_recognition():
    # Путь к тестовому изображению
    test_image_path = "testimages/testimage.png"
    
    # Проверяем существование файла
    if not os.path.exists(test_image_path):
        raise FileNotFoundError(f"Test image not found at {test_image_path}")
    
    # Инициализируем распознаватель
    recognizer = GraphRecognizer()
    
    # Загружаем изображение
    image = Image.open(test_image_path)
    
    # Выполняем распознавание
    result = recognizer.recognize(image)
    
    # Выводим результаты
    print("Распознанные вершины:", result.vertices)
    print("Распознанные рёбра:", result.edges)
    print("Матрица смежности:", result.adjacency_matrix)

if __name__ == "__main__":
    test_graph_recognition()