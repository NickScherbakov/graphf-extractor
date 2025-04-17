#!/usr/bin/env python3
"""
Модуль для логирования операций в проекте graphf-extractor.
Обеспечивает отслеживание изменений кода, вызовов API и запусков тестов.
"""

import os
import sys
import json
import time
import logging
import functools
import inspect
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List, Union
import warnings

# Настройка базового логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Создание файлового хендлера для сохранения логов в файл
try:
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler(
        f'logs/graphf_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    )
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s')
    )
    # Получение корневого логгера и добавление файлового хендлера
    logger = logging.getLogger()
    logger.addHandler(file_handler)
except Exception as e:
    logging.warning(f"Не удалось настроить сохранение логов в файл: {e}")

# Константы для стоимости API моделей
API_COSTS = {
    "gpt-4o": {"input": 0.01, "output": 0.03},  # $ за 1K токенов
    "gpt-4": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "default": {"input": 0.01, "output": 0.03}  # По умолчанию предполагаем дорогую модель
}

# Глобальное состояние для отслеживания общей стоимости API-вызовов
_api_usage_stats = {
    "calls_count": 0,
    "total_cost_estimate": 0.0,
    "calls_by_model": {},
    "session_start": datetime.now().isoformat()
}

class APIUsageBudgetExceeded(Exception):
    """Исключение для случаев, когда превышен бюджет на использование API."""
    pass

class ChangesNotLogged(Exception):
    """Исключение для случаев, когда изменения не были должным образом залогированы."""
    pass

def log_api_call(model_id: str, tokens_input: int = 0, tokens_output: int = 0) -> Dict[str, Any]:
    """
    Регистрирует вызов API и оценивает его стоимость.
    
    Args:
        model_id: Идентификатор модели API
        tokens_input: Количество входных токенов
        tokens_output: Количество выходных токенов
        
    Returns:
        Dict с информацией о вызове и стоимости
    """
    model_costs = API_COSTS.get(model_id.lower(), API_COSTS["default"])
    
    # Оценка стоимости вызова
    cost_input = (tokens_input / 1000) * model_costs["input"]
    cost_output = (tokens_output / 1000) * model_costs["output"]
    total_cost = cost_input + cost_output
    
    # Обновление статистики
    _api_usage_stats["calls_count"] += 1
    _api_usage_stats["total_cost_estimate"] += total_cost
    
    if model_id not in _api_usage_stats["calls_by_model"]:
        _api_usage_stats["calls_by_model"][model_id] = {
            "count": 0,
            "total_cost": 0.0,
            "total_tokens_input": 0,
            "total_tokens_output": 0
        }
    
    _api_usage_stats["calls_by_model"][model_id]["count"] += 1
    _api_usage_stats["calls_by_model"][model_id]["total_cost"] += total_cost
    _api_usage_stats["calls_by_model"][model_id]["total_tokens_input"] += tokens_input
    _api_usage_stats["calls_by_model"][model_id]["total_tokens_output"] += tokens_output
    
    call_info = {
        "timestamp": datetime.now().isoformat(),
        "model_id": model_id,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "cost_estimate": total_cost,
        "cumulative_cost": _api_usage_stats["total_cost_estimate"]
    }
    
    # Логирование информации о вызове
    logging.info(
        f"API вызов: {model_id}, токены: {tokens_input}/{tokens_output}, "
        f"стоимость: ${total_cost:.4f}, всего: ${_api_usage_stats['total_cost_estimate']:.4f}"
    )
    
    # Сохранение статистики в файл
    try:
        with open('logs/api_usage_stats.json', 'w') as f:
            json.dump(_api_usage_stats, f, indent=2)
    except Exception as e:
        logging.warning(f"Не удалось сохранить статистику использования API: {e}")
    
    return call_info

def check_api_budget(model_id: str, tokens_input: int = 0, tokens_output: int = 0, 
                    budget_limit: float = 1.0, raise_error: bool = True) -> bool:
    """
    Проверяет, не будет ли превышен бюджет на API-вызовы после выполнения запроса.
    
    Args:
        model_id: Идентификатор модели API
        tokens_input: Количество входных токенов
        tokens_output: Количество выходных токенов
        budget_limit: Лимит бюджета в долларах
        raise_error: Если True, будет вызвано исключение при превышении бюджета
        
    Returns:
        True если бюджет не будет превышен, иначе False
    
    Raises:
        APIUsageBudgetExceeded: Если бюджет будет превышен и raise_error=True
    """
    model_costs = API_COSTS.get(model_id.lower(), API_COSTS["default"])
    
    # Оценка стоимости предстоящего вызова
    cost_input = (tokens_input / 1000) * model_costs["input"]
    cost_output = (tokens_output / 1000) * model_costs["output"]
    call_cost = cost_input + cost_output
    
    # Проверка на превышение бюджета
    future_total_cost = _api_usage_stats["total_cost_estimate"] + call_cost
    
    if future_total_cost > budget_limit:
        message = (
            f"⚠️ ПРЕДУПРЕЖДЕНИЕ О БЮДЖЕТЕ ⚠️\n"
            f"Запрос к модели {model_id} оценивается в ${call_cost:.4f}\n"
            f"Текущая общая стоимость: ${_api_usage_stats['total_cost_estimate']:.4f}\n"
            f"После этого запроса стоимость составит: ${future_total_cost:.4f}\n"
            f"Это превышает установленный лимит бюджета: ${budget_limit:.2f}"
        )
        
        logging.warning(message)
        print("\033[91m" + message + "\033[0m")  # Красный текст в консоли
        
        if raise_error:
            raise APIUsageBudgetExceeded(message)
        return False
    
    return True

def log_code_change(file_path: str, function_name: str, description: str, 
                   change_type: str = "EDIT") -> Dict[str, Any]:
    """
    Логирует изменение в коде проекта.
    
    Args:
        file_path: Путь к файлу, который был изменен
        function_name: Название функции, которая была изменена
        description: Описание изменения
        change_type: Тип изменения (EDIT, ADD, DELETE)
        
    Returns:
        Dict с информацией об изменении
    """
    caller_info = inspect.stack()[1]
    caller_file = os.path.basename(caller_info.filename)
    caller_line = caller_info.lineno
    caller_function = caller_info.function
    
    change_info = {
        "timestamp": datetime.now().isoformat(),
        "file": file_path,
        "function": function_name,
        "type": change_type,
        "description": description,
        "caller": f"{caller_file}:{caller_line} in {caller_function}",
        "stack_trace": traceback.format_stack()[:-1]  # Исключаем текущий фрейм
    }
    
    # Логирование информации об изменении
    logging.info(
        f"[{change_type}] {file_path}::{function_name} - {description} "
        f"(вызвано из {caller_file}:{caller_line})"
    )
    
    # Сохранение информации об изменении в файл
    try:
        changes_file = 'logs/code_changes.jsonl'
        with open(changes_file, 'a') as f:
            f.write(json.dumps(change_info) + '\n')
    except Exception as e:
        logging.warning(f"Не удалось сохранить информацию об изменении кода: {e}")
    
    return change_info

def log_test_run(test_name: str, status: str, duration_ms: float, 
                details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Логирует запуск и результат выполнения теста.
    
    Args:
        test_name: Название теста
        status: Статус выполнения (PASS, FAIL, ERROR, SKIP)
        duration_ms: Длительность выполнения в миллисекундах
        details: Дополнительная информация о тесте
        
    Returns:
        Dict с информацией о запуске теста
    """
    details = details or {}
    
    test_info = {
        "timestamp": datetime.now().isoformat(),
        "test_name": test_name,
        "status": status,
        "duration_ms": duration_ms,
        **details
    }
    
    # Определение уровня логирования в зависимости от статуса теста
    if status == "PASS":
        log_level = logging.INFO
        status_marker = "✓"
    elif status == "SKIP":
        log_level = logging.INFO
        status_marker = "-"
    else:  # FAIL или ERROR
        log_level = logging.ERROR
        status_marker = "✗"
    
    # Логирование информации о тесте
    logging.log(
        log_level, 
        f"[TEST {status}] {status_marker} {test_name} ({duration_ms:.2f} ms)"
    )
    
    if status in ("FAIL", "ERROR") and details.get("error_message"):
        logging.error(f"Детали ошибки: {details['error_message']}")
    
    # Сохранение информации о тесте в файл
    try:
        tests_file = 'logs/test_runs.jsonl'
        with open(tests_file, 'a') as f:
            f.write(json.dumps(test_info) + '\n')
    except Exception as e:
        logging.warning(f"Не удалось сохранить информацию о запуске теста: {e}")
    
    return test_info

def require_confirmation(prompt: str) -> bool:
    """
    Запрашивает у пользователя подтверждение для выполнения операции.
    
    Args:
        prompt: Сообщение для пользователя
        
    Returns:
        True если пользователь подтвердил, иначе False
    """
    confirmation = input(f"\n⚠️ {prompt} (y/n): ").lower().strip()
    return confirmation in ('y', 'yes', 'да')

def api_cost_warning(model_id: str, estimated_tokens: int = 1000) -> None:
    """
    Выводит предупреждение о стоимости вызова API.
    
    Args:
        model_id: Идентификатор модели API
        estimated_tokens: Примерное количество токенов запроса и ответа
    """
    model_costs = API_COSTS.get(model_id.lower(), API_COSTS["default"])
    total_cost = (estimated_tokens / 1000) * (model_costs["input"] + model_costs["output"])
    
    warning_message = (
        f"\n⚠️ ВНИМАНИЕ: Вы собираетесь использовать модель {model_id}\n"
        f"Примерная стоимость операции: ${total_cost:.4f} "
        f"(для ~{estimated_tokens} токенов)\n"
        f"Текущая общая стоимость сессии: ${_api_usage_stats['total_cost_estimate']:.4f}\n"
    )
    
    print("\033[93m" + warning_message + "\033[0m")  # Жёлтый текст в консоли

def safe_api_call(model_id: str, estimated_input_tokens: int = 500, 
                 estimated_output_tokens: int = 500, budget_limit: float = 1.0,
                 require_user_approval: bool = True) -> Callable:
    """
    Декоратор для безопасного выполнения API-вызовов с проверкой бюджета.
    
    Args:
        model_id: Идентификатор модели API
        estimated_input_tokens: Оценка количества входных токенов
        estimated_output_tokens: Оценка количества выходных токенов
        budget_limit: Лимит бюджета в долларах
        require_user_approval: Требовать подтверждение пользователя
        
    Returns:
        Декоратор функции
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            actual_model_id = kwargs.get('model_id', model_id)
            
            # Проверка бюджета
            try:
                check_api_budget(
                    actual_model_id, 
                    estimated_input_tokens, 
                    estimated_output_tokens,
                    budget_limit,
                    raise_error=False
                )
            except Exception as e:
                logging.warning(f"Не удалось проверить бюджет: {e}")
            
            # Предупреждение о стоимости
            api_cost_warning(actual_model_id, estimated_input_tokens + estimated_output_tokens)
            
            # Запрос подтверждения у пользователя
            if require_user_approval:
                if not require_confirmation(
                    f"Вы уверены, что хотите выполнить запрос к модели {actual_model_id}?"
                ):
                    logging.info(f"Пользователь отменил вызов API для {actual_model_id}")
                    print("Операция отменена пользователем.")
                    return None
            
            # Замер времени выполнения
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000  # в миллисекундах
                
                # Оцениваем количество токенов по размеру результата и запроса
                input_size = sum(sys.getsizeof(arg) for arg in args) + sum(sys.getsizeof(v) for v in kwargs.values())
                output_size = sys.getsizeof(result) if result else 0
                
                # Грубая оценка токенов: ~1 байт ≈ 0.25 токена
                actual_input_tokens = estimated_input_tokens or max(1, input_size // 4)
                actual_output_tokens = estimated_output_tokens or max(1, output_size // 4)
                
                # Логирование вызова API
                log_api_call(actual_model_id, actual_input_tokens, actual_output_tokens)
                
                logging.info(f"API вызов выполнен за {duration:.2f} мс")
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logging.error(f"API вызов завершился с ошибкой за {duration:.2f} мс: {e}")
                raise
        
        return wrapper
    return decorator

def log_test_execution() -> Callable:
    """
    Декоратор для логирования выполнения тестов.
    
    Returns:
        Декоратор функции
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            test_name = func.__name__
            logging.info(f"Запуск теста: {test_name}")
            
            start_time = time.time()
            status = "PASS"
            error_message = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except AssertionError as e:
                status = "FAIL"
                error_message = str(e)
                raise
            except Exception as e:
                status = "ERROR"
                error_message = str(e)
                raise
            finally:
                duration = (time.time() - start_time) * 1000
                details = {"error_message": error_message} if error_message else {}
                log_test_run(test_name, status, duration, details)
        
        return wrapper
    return decorator

def log_function_calls(category: str = "FUNCTION") -> Callable:
    """
    Декоратор для логирования вызовов функций.
    
    Args:
        category: Категория для логирования
        
    Returns:
        Декоратор функции
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            module_name = func.__module__
            
            # Получение информации о вызывающей функции
            caller_info = inspect.stack()[1]
            caller_file = os.path.basename(caller_info.filename)
            caller_line = caller_info.lineno
            caller_function = caller_info.function
            
            # Логирование начала выполнения функции
            logging.debug(
                f"[{category}] Вызов {module_name}.{func_name} "
                f"(из {caller_file}:{caller_line} в {caller_function})"
            )
            
            # Замер времени выполнения
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                
                # Логирование успешного завершения функции
                logging.debug(
                    f"[{category}] {module_name}.{func_name} выполнена за {duration:.2f} мс"
                )
                
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                
                # Логирование ошибки
                logging.error(
                    f"[{category}] {module_name}.{func_name} завершилась с ошибкой "
                    f"через {duration:.2f} мс: {e}"
                )
                
                raise
        
        return wrapper
    return decorator

def init_logging(log_level=logging.INFO) -> None:
    """
    Инициализирует систему логирования с заданными параметрами.
    
    Args:
        log_level: Уровень логирования
    """
    # Создание директории для логов, если она не существует
    os.makedirs('logs', exist_ok=True)
    
    # Установка глобального уровня логирования
    logging.getLogger().setLevel(log_level)
    
    # Вывод приветственного сообщения
    logging.info(f"Инициализирована система логирования графа (уровень: {logging.getLevelName(log_level)})")
    logging.info(f"Лог-файлы будут сохранены в папке 'logs'")

# Инициализация логирования при импорте модуля
init_logging()
