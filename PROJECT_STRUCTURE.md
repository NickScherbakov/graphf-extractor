# Project Structure (graphf-extractor)

This diagram shows the main components and data flow of the project.

```mermaid
graph TD
    subgraph "Входные данные"
        A[PDF Файл в uploads/]
    end

    subgraph "Подготовка"
        B(graph_pipeline/extract_graph_image.py) -- Извлекает --> C{Изображения страниц в pdf_images/}
    end

    subgraph "Ядро: Извлечение графа"
        D(graph_pipeline/main.py / CLI) -- Запускает --> E(graph_pipeline/graph_structure_extractor.py)
        E -- Запрашивает модель --> F(graph_pipeline/model_manager.py)
        F -- Загружает/Обновляет --> G[model_cache.json]
        F -- Запрашивает API --> H{gptunnel.ru API (/v1/models, /v1/chat/completions)}
        F -- Возвращает ID модели --> E
        E -- Отправляет изображение + ID модели --> H
        H -- Возвращает --> I{Структура графа (nodes, edges)}
        E -- Получает --> I
    end

    subgraph "Визуализация (Manim)"
        I -- Передает структуру --> J(graph_pipeline/generate_manim_advanced.py)
        K(run_manim.sh) -- Выполняет --> J
        J -- Генерирует --> L[Видео/анимация графа]
    end

    A --> B
    B --> C
    C --> E
```

**Пояснения к схеме:**

1.  **Вход:** Пользователь помещает PDF-файл в папку `uploads/`.
2.  **Извлечение изображений:** Скрипт `graph_pipeline/extract_graph_image.py` обрабатывает PDF и сохраняет изображения его страниц в папку `pdf_images/`.
3.  **Запуск:** Основной процесс запускается через `graph_pipeline/main.py` (как CLI-инструмент), который инициирует извлечение структуры графа.
4.  **Извлечение структуры:**
    *   `graph_pipeline/graph_structure_extractor.py` берет изображение страницы.
    *   Он обращается к `graph_pipeline/model_manager.py`, чтобы получить подходящую *vision*-модель.
    *   `graph_pipeline/model_manager.py` отвечает за взаимодействие с API `gptunnel.ru`:
        *   Он загружает/обновляет кэш моделей (`model_cache.json`), запрашивая `/v1/models` у `gptunnel.ru`.
        *   Он может проверять *vision*-возможности моделей, отправляя тестовые запросы к `/v1/chat/completions`.
        *   Он возвращает ID подходящей модели (например, из списка `get_vision_models`).
    *   `graph_pipeline/graph_structure_extractor.py` отправляет изображение и выбранный ID модели в `gptunnel.ru` через эндпоинт `/v1/chat/completions` с запросом на извлечение узлов и ребер.
    *   API возвращает структуру графа.
5.  **Визуализация:**
    *   Полученная структура графа передается в `graph_pipeline/generate_manim_advanced.py`.
    *   Скрипт `run_manim.sh` запускает Manim для генерации анимации на основе этой структуры.
    *   Результатом является видеофайл анимации графа.

**Примечание:** Эта схема основана на анализе кода и может потребовать ручного обновления при значительных изменениях в структуре проекта.
