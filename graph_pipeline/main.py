import argparse
import os
from .extract_graph_image import extract_images_from_pdf
from .graph_structure_extractor import extract_graph_structure, adjacency_matrix_from_edges
from .generate_manim_advanced import generate_graph_and_matrix_script

def main():
    parser = argparse.ArgumentParser(description="Пайплайн: граф из PDF → матрица смежности → анимация")
    parser.add_argument("--pdf", help="Путь к PDF-файлу", required=True)
    parser.add_argument("--page", type=int, help="Номер страницы (по умолчанию все)", default=None)
    parser.add_argument("--image", help="Путь к картинке графа (если уже извлечена)", default=None)
    parser.add_argument("--output", help="Имя выходного manim-скрипта", default="graph_manim.py")
    args = parser.parse_args()

    # 1. Извлечение изображения
    if args.image:
        image_path = args.image
    else:
        print("Извлекаем изображения из PDF...")
        images = extract_images_from_pdf(args.pdf)
        if not images:
            print("Не найдено изображений в PDF!")
            return
        print("Извлечены изображения:", images)
        if args.page:
            image_path = [im for im in images if f"page{args.page}_" in im][0]
        else:
            print("Используется первое изображение.")
            image_path = images[0]

    print("Выбранное изображение:", image_path)

    # 2. Распознавание структуры графа
    print("Распознаём граф...")
    nodes, edges = extract_graph_structure(image_path)
    print("Вершины:", nodes)
    print("Рёбра:", edges)
    adj = adjacency_matrix_from_edges(nodes, edges)
    print("Матрица смежности:\n", adj)

    # 3. Генерация manim-скрипта
    print("Генерируем manim-скрипт...")
    generate_graph_and_matrix_script(nodes, edges, output_file=args.output)
    print(f"Готово. Файл для manim: {args.output}")
    print(f"Для анимации выполните:\n    bash run_manim.sh {args.output}")

if __name__ == "__main__":
    main()