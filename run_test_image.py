#!/usr/bin/env python3
import os
import sys
import time
import json
from datetime import datetime
from graph_pipeline.graph_structure_extractor import extract_graph_structure
from graph_pipeline.model_manager import load_api_key, get_vision_models, DEFAULT_API_BASE_URL

# Импортируем нашу систему логирования
try:
    from graph_pipeline.logger import (
        log_api_call, log_function_calls, check_api_budget, 
        require_confirmation, api_cost_warning, init_logging,
        log_test_run
    )
    CUSTOM_LOGGER_ENABLED = True
except ImportError:
    CUSTOM_LOGGER_ENABLED = False
    print("⚠️ Система мониторинга API-вызовов недоступна", file=sys.stderr)

@log_function_calls(category="TEST") if CUSTOM_LOGGER_ENABLED else lambda x: x
def test_image_recognition(image_path, budget_limit=1.0, require_approval=True):
    """Тестирует распознавание изображения графа."""
    start_time = time.time()
    test_id = f"test_img_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"🔍 Тестирование распознавания изображения: {image_path}")
    if CUSTOM_LOGGER_ENABLED:
        init_logging()  # Инициализируем логгирование
    
    # Записываем информацию о начале теста
    os.makedirs("logs", exist_ok=True)
    with open(f"logs/test_request_{test_id}.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "test_type": "image_recognition",
            "image_path": image_path,
            "budget_limit": budget_limit
        }, f, indent=2)
    
    # Загружаем API ключ
    api_key = load_api_key()
    if not api_key:
        error_msg = "❌ OPENAI_API_KEY не найден в .env файле"
        print(error_msg)
        if CUSTOM_LOGGER_ENABLED:
            log_test_run("test_image_recognition", "ERROR", 
                         (time.time() - start_time) * 1000,
                         {"error_message": error_msg, "image_path": image_path})
        return False
    
    # Получаем доступную vision-модель
    vision_models = get_vision_models(api_base_url=DEFAULT_API_BASE_URL, api_key=api_key)
    if not vision_models:
        error_msg = "❌ Доступные vision-модели не найдены"
        print(error_msg)
        if CUSTOM_LOGGER_ENABLED:
            log_test_run("test_image_recognition", "ERROR", 
                         (time.time() - start_time) * 1000,
                         {"error_message": error_msg, "image_path": image_path})
        return False
    
    model_id = vision_models[0]['id']
    print(f"📊 Используем модель: {model_id}")
    
    # Проверка бюджета и запрос подтверждения перед API-вызовом
    if CUSTOM_LOGGER_ENABLED:
        # Выводим предупреждение о стоимости
        api_cost_warning(model_id, estimated_tokens=1200)
        
        # Проверяем, не превышен ли бюджет
        if not check_api_budget(model_id, 1000, 200, budget_limit, False):
            print(f"⛔ Тестирование отменено из-за ограничений бюджета (лимит: ${budget_limit})")
            log_test_run("test_image_recognition", "SKIP", 
                         (time.time() - start_time) * 1000,
                         {"reason": "budget_limit", "image_path": image_path})
            return False
        
        # Запрашиваем подтверждение пользователя если требуется
        if require_approval:
            if not require_confirmation(
                f"Продолжить тестирование изображения с использованием модели {model_id}?"
            ):
                print("⛔ Тестирование отменено пользователем")
                log_test_run("test_image_recognition", "SKIP", 
                             (time.time() - start_time) * 1000,
                             {"reason": "user_cancelled", "image_path": image_path})
                return False
    
    # Распознаем структуру графа
    try:
        start_api_time = time.time()
        
        # Записываем информацию о запросе перед вызовом API
        test_info = {
            "timestamp": datetime.now().isoformat(),
            "image_path": image_path,
            "model_id": model_id,
            "api_base_url": DEFAULT_API_BASE_URL
        }
        with open(f"logs/api_request_{test_id}.json", "w") as f:
            json.dump(test_info, f, indent=2)
        
        # Выполняем API-запрос для распознавания графа
        nodes, edges = extract_graph_structure(
            image_path=image_path,
            model_id=model_id,
            api_key=api_key,
            api_base_url=DEFAULT_API_BASE_URL
        )
        
        api_duration_ms = (time.time() - start_api_time) * 1000
        
        if nodes is None or edges is None:
            error_msg = "❌ Не удалось распознать структуру графа"
            print(error_msg)
            if CUSTOM_LOGGER_ENABLED:
                log_test_run("test_image_recognition", "FAIL", 
                             (time.time() - start_time) * 1000,
                             {"error_message": error_msg, "image_path": image_path, 
                              "api_duration_ms": api_duration_ms})
            return False
        
        # Записываем результаты в лог-файл
        result_info = {
            "timestamp": datetime.now().isoformat(),
            "image_path": image_path,
            "model_id": model_id,
            "api_duration_ms": api_duration_ms,
            "nodes": nodes,
            "edges": edges
        }
        with open(f"logs/api_result_{test_id}.json", "w") as f:
            json.dump(result_info, f, indent=2)
        
        print("\n✅ Результаты распознавания:")
        print(f"Вершины: {nodes}")
        print(f"Рёбра: {edges}")
        
        if CUSTOM_LOGGER_ENABLED:
            log_test_run("test_image_recognition", "PASS", 
                         (time.time() - start_time) * 1000,
                         {"nodes_count": len(nodes), "edges_count": len(edges), 
                          "image_path": image_path, "api_duration_ms": api_duration_ms})
        
        return True
    except Exception as e:
        error_msg = f"❌ Ошибка при распознавании: {e}"
        print(error_msg)
        
        if CUSTOM_LOGGER_ENABLED:
            log_test_run("test_image_recognition", "ERROR", 
                         (time.time() - start_time) * 1000,
                         {"error_message": str(e), "image_path": image_path})
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Использование: {sys.argv[0]} <путь_к_изображению>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"❌ Файл не существует: {image_path}")
        sys.exit(1)
    
    success = test_image_recognition(image_path)
    sys.exit(0 if success else 1)
