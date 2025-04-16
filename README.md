# Graph Pipeline

Комплекс для автоматизации: поиск графа в PDF → распознавание структуры → визуализация → анимация.

## Установка

1. Клонируйте репозиторий.
2. Установите зависимости:
   ```
   pip install -r requirements.txt
   ```

3. Для manim установите ffmpeg и LaTeX (см. [официальную документацию](https://docs.manim.community/en/stable/installation.html)).

## Быстрый старт

1. Запустите пайплайн:
   ```
   python -m graph_pipeline.main --pdf ваш_файл.pdf
   ```
   или с указанием страницы/изображения:
   ```
   python -m graph_pipeline.main --pdf ваш_файл.pdf --page 2
   ```

2. Запустите анимацию:
   ```
   bash run_manim.sh graph_manim.py
   ```

## Структура

- `extract_graph_image.py` — извлекает изображения из PDF.
- `graph_structure_extractor.py` — распознаёт вершины и рёбра.
- `generate_manim_advanced.py` — создаёт manim-скрипт с поэтапной анимацией.
- `main.py` — мастер-скрипт для CLI.
- `run_manim.sh` — запускает анимацию через manim.

## Зависимости

Всё необходимое указано в `requirements.txt`.
