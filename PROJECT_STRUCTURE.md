# Project Structure (graphf-extractor)

This diagram shows the main components and data flow of the project.

```mermaid
flowchart TD
    %% Определение узлов
    A[PDF Файл в uploads/]
    B[extract_graph_image.py]
    C[Изображения в pdf_images/]
    D[main.py / CLI]
    E[graph_structure_extractor.py]
    F[model_manager.py]
    G[model_cache.json]
    H[gptunnel.ru API]
    I[Структура графа nodes, edges]
    J[generate_manim_advanced.py]
    K[run_manim.sh]
    L[Видео/анимация графа]
    M[Матрица смежности]
    
    %% Группировка и связи
    subgraph "Входные данные"
        A
    end
    
    subgraph "Подготовка"
        B
    end
    
    subgraph "Ядро: Извлечение графа"
        D
        E
        F
        G
        H
        I
        M
    end
    
    subgraph "Визуализация Manim"
        J
        K
        L
    end
    
    %% Связи между узлами
    A --> B
    B -- "Извлекает" --> C
    C --> E
    D -- "Запускает" --> E
    D -- "Запрашивает модель" --> F
    F -- "Загружает/Обновляет" --> G
    F -- "Запрашивает" --> H
    F -- "Возвращает ID модели" --> D
    E -- "Отправляет изображение" --> H
    H -- "Возвращает данные" --> I
    E -- "Анализирует" --> I
    I -- "Преобразуется в" --> M
    I -- "Передает структуру" --> J
    M -- "Передает матрицу" --> J
    K -- "Выполняет" --> J
    J -- "Генерирует" --> L
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
