"""
Конфигурация для pytest с интеграцией системы логирования.
Автоматически логирует запуск и результаты всех тестов.
"""
import os
import time
import pytest
import logging
from typing import Dict, Any, Optional, Union, List

# Пытаемся импортировать нашу систему логирования
try:
    from graph_pipeline.logger import log_test_run, init_logging
    CUSTOM_LOGGER_ENABLED = True
except ImportError:
    CUSTOM_LOGGER_ENABLED = False
    print("⚠️ Система логирования тестов недоступна")

# Глобальное хранилище для статистики тестов
test_stats = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "errors": 0,
    "skipped": 0,
    "start_time": time.time(),
    "tests": []
}

@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Инициализация логирования перед запуском тестов."""
    # Создаем директорию logs если её нет
    os.makedirs("logs", exist_ok=True)
    
    if CUSTOM_LOGGER_ENABLED:
        init_logging(logging.INFO)
        logging.info("🚀 Начало выполнения pytest тестов")
    
@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Логирование завершения тестов."""
    duration = time.time() - test_stats["start_time"]
    
    summary = (
        f"\n===== Отчет о тестировании =====\n"
        f"Всего тестов: {test_stats['total']}\n"
        f"✅ Успешно: {test_stats['passed']}\n"
        f"❌ Провалено: {test_stats['failed']}\n"
        f"⚠️ Ошибки: {test_stats['errors']}\n"
        f"⏭️ Пропущено: {test_stats['skipped']}\n"
        f"Общее время выполнения: {duration:.2f} секунд\n"
        f"================================="
    )
    
    print(summary)
    
    if CUSTOM_LOGGER_ENABLED:
        logging.info(f"🏁 Завершение выполнения тестов. Код выхода: {exitstatus}")
        logging.info(summary)
        
        # Сохраняем детальную информацию о тестах в файл
        try:
            import json
            with open("logs/test_summary.json", "w") as f:
                json.dump(test_stats, f, indent=2)
        except Exception as e:
            logging.error(f"Не удалось сохранить сводку по тестам: {e}")

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    """Отслеживание запуска каждого теста."""
    test_stats["total"] += 1
    return None  # продолжаем стандартное выполнение

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Логирование перед запуском теста."""
    if CUSTOM_LOGGER_ENABLED:
        logging.info(f"▶️ Запуск теста: {item.name}")

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_teardown(item):
    """Логирование после завершения теста."""
    if CUSTOM_LOGGER_ENABLED:
        logging.debug(f"⏹️ Завершение теста: {item.name}")

@pytest.hookimpl(trylast=True)
def pytest_runtest_logreport(report):
    """Обработка результатов теста."""
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        test_name = report.nodeid
        status = report.outcome.upper()
        duration_ms = report.duration * 1000 if hasattr(report, 'duration') else 0
        
        # Обновляем статистику
        if status == "PASSED":
            test_stats["passed"] += 1
        elif status == "FAILED":
            test_stats["failed"] += 1
        elif status == "SKIPPED":
            test_stats["skipped"] += 1
        elif status == "ERROR":
            test_stats["errors"] += 1
        
        # Формируем детали для логирования
        details = {}
        if hasattr(report, "longrepr") and report.longrepr:
            details["error_message"] = str(report.longrepr)
        
        # Добавляем информацию о тесте в общую статистику
        test_info = {
            "name": test_name,
            "status": status,
            "duration_ms": duration_ms,
            **details
        }
        test_stats["tests"].append(test_info)
        
        # Логируем результат выполнения теста
        if CUSTOM_LOGGER_ENABLED:
            log_test_run(test_name, status, duration_ms, details)
        else:
            # Простой вывод если логгер недоступен
            status_marker = "✓" if status == "PASSED" else "✗" if status == "FAILED" else "-"
            print(f"{status_marker} {test_name} ({duration_ms:.2f} ms) - {status}")

@pytest.fixture(scope="function")
def log_test_context(request):
    """Фикстура для логирования контекста теста."""
    test_name = request.node.name
    if CUSTOM_LOGGER_ENABLED:
        logging.info(f"📝 Контекст теста {test_name}: {request.function.__doc__ or 'Без описания'}")
    yield
    # Код после выполнения теста при необходимости

# Расширение стандартных маркеров pytest
def pytest_configure(config):
    config.addinivalue_line("markers", "api_call: маркер для тестов, использующих API-вызовы")
    config.addinivalue_line("markers", "expensive: маркер для дорогостоящих тестов")
    config.addinivalue_line("markers", "visual_check: маркер для тестов визуальных компонентов")

# Командная опция для запуска дорогих тестов
def pytest_addoption(parser):
    parser.addoption("--expensive", action="store_true", default=False, 
                     help="Запустить дорогостоящие тесты (API-вызовы)")
    parser.addoption("--api-budget", type=float, default=1.0,
                     help="Установить бюджет для API-вызовов (в долларах)")

# Пропуск дорогостоящих тестов если флаг не установлен
def pytest_collection_modifyitems(config, items):
    if not config.getoption("--expensive"):
        expensive_tests = pytest.mark.skip(reason="Нужна опция --expensive для запуска")
        for item in items:
            if "expensive" in item.keywords:
                item.add_marker(expensive_tests)
            if "api_call" in item.keywords:
                item.add_marker(expensive_tests)
