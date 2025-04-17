#!/usr/bin/env python3
"""
Утилита для анализа логов и статистики системы.
Отображает информацию об использовании API, запусках тестов 
и изменениях в коде проекта.
"""

import os
import sys
import json
import glob
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# ANSI цвета для вывода
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"

def load_json_file(file_path: str) -> Dict:
    """Загружает JSON файл с обработкой ошибок."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"{Colors.RED}Ошибка при загрузке файла {file_path}: {e}{Colors.RESET}")
        return {}

def load_jsonl_file(file_path: str) -> List[Dict]:
    """Загружает файл в формате JSON Lines."""
    results = []
    if not os.path.exists(file_path):
        return results
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:  # Пропускаем пустые строки
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass  # Пропускаем некорректные строки
    except Exception as e:
        print(f"{Colors.RED}Ошибка при загрузке файла {file_path}: {e}{Colors.RESET}")
    
    return results

def format_timestamp(timestamp: str) -> str:
    """Форматирует временную метку для удобного чтения."""
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except:
        return timestamp

def analyze_api_usage(api_stats_file: str = 'logs/api_usage_stats.json') -> None:
    """Анализирует использование API и выводит сводку."""
    if not os.path.exists(api_stats_file):
        print(f"{Colors.YELLOW}Файл статистики API не найден: {api_stats_file}{Colors.RESET}")
        return
    
    stats = load_json_file(api_stats_file)
    if not stats:
        return
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}===== Статистика использования API ====={Colors.RESET}")
    print(f"Сессия начата: {format_timestamp(stats.get('session_start', 'N/A'))}")
    print(f"Всего вызовов API: {stats.get('calls_count', 0)}")
    print(f"{Colors.YELLOW}Общая оценка стоимости: ${stats.get('total_cost_estimate', 0):.4f}{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}Вызовы по моделям:{Colors.RESET}")
    for model, model_stats in stats.get('calls_by_model', {}).items():
        print(f"  - {model}: {model_stats.get('count', 0)} вызовов, "
              f"${model_stats.get('total_cost', 0):.4f}")
        print(f"    Токенов: {model_stats.get('total_tokens_input', 0)} вход / "
              f"{model_stats.get('total_tokens_output', 0)} выход")
    
    print(f"\n{Colors.BOLD}Рекомендации по оптимизации:{Colors.RESET}")
    if stats.get('total_cost_estimate', 0) > 5.0:
        print(f"{Colors.RED}⚠️ Высокий расход на API. Рассмотрите возможность использования более "
              f"экономичных моделей или кэширование результатов.{Colors.RESET}")
    elif stats.get('total_cost_estimate', 0) > 1.0:
        print(f"{Colors.YELLOW}⚠️ Умеренный расход на API. При частом использовании рекомендуется "
              f"оптимизировать запросы.{Colors.RESET}")
    else:
        print(f"{Colors.GREEN}✓ Текущий расход на API находится в пределах нормы.{Colors.RESET}")

def analyze_test_runs(test_runs_file: str = 'logs/test_runs.jsonl') -> None:
    """Анализирует запуски тестов и выводит сводку."""
    if not os.path.exists(test_runs_file):
        print(f"{Colors.YELLOW}Файл запусков тестов не найден: {test_runs_file}{Colors.RESET}")
        return
    
    test_runs = load_jsonl_file(test_runs_file)
    if not test_runs:
        return
    
    # Группируем запуски по тестам
    tests_by_name = {}
    for run in test_runs:
        name = run.get('test_name', 'unknown')
        if name not in tests_by_name:
            tests_by_name[name] = []
        tests_by_name[name].append(run)
    
    # Подсчет статистики
    status_counts = {"PASS": 0, "FAIL": 0, "ERROR": 0, "SKIP": 0}
    for runs in tests_by_name.values():
        for run in runs:
            status = run.get('status', '').upper()
            if status in status_counts:
                status_counts[status] += 1
    
    # Сводка по последним запускам каждого теста
    print(f"\n{Colors.BOLD}{Colors.BLUE}===== Статистика тестов ====={Colors.RESET}")
    print(f"Всего записей о запусках: {len(test_runs)}")
    print(f"Уникальных тестов: {len(tests_by_name)}")
    print(f"Статус последних запусков: {Colors.GREEN}✓ Успешно: {status_counts['PASS']}{Colors.RESET}, "
          f"{Colors.RED}✗ Провалено: {status_counts['FAIL']}{Colors.RESET}, "
          f"{Colors.RED}⚠ Ошибки: {status_counts['ERROR']}{Colors.RESET}, "
          f"{Colors.YELLOW}- Пропущено: {status_counts['SKIP']}{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}Последние запуски тестов:{Colors.RESET}")
    for name, runs in tests_by_name.items():
        # Берем самый последний запуск по временной метке
        last_run = sorted(runs, key=lambda x: x.get('timestamp', ''), reverse=True)[0]
        status = last_run.get('status', '').upper()
        duration = last_run.get('duration_ms', 0)
        timestamp = format_timestamp(last_run.get('timestamp', 'N/A'))
        
        status_color = Colors.GREEN if status == 'PASS' else \
                      Colors.RED if status in ('FAIL', 'ERROR') else Colors.YELLOW
        status_marker = "✓" if status == 'PASS' else "✗" if status in ('FAIL', 'ERROR') else "-"
        
        short_name = name.split('::')[-1] if '::' in name else name
        print(f"  {status_color}{status_marker} {short_name}{Colors.RESET}: {status} "
              f"({duration:.2f} мс) - {timestamp}")
        
        # Показываем ошибки для неудачных тестов
        if status in ('FAIL', 'ERROR') and 'error_message' in last_run:
            error_msg = last_run['error_message']
            if len(error_msg) > 100:
                error_msg = error_msg[:97] + "..."
            print(f"    {Colors.RED}Ошибка: {error_msg}{Colors.RESET}")

def analyze_code_changes(changes_file: str = 'logs/code_changes.jsonl') -> None:
    """Анализирует изменения в коде и выводит сводку."""
    if not os.path.exists(changes_file):
        print(f"{Colors.YELLOW}Файл изменений кода не найден: {changes_file}{Colors.RESET}")
        return
    
    changes = load_jsonl_file(changes_file)
    if not changes:
        return
    
    # Группируем изменения по файлам и типам
    files_changed = {}
    change_types = {"EDIT": 0, "ADD": 0, "DELETE": 0, "ERROR": 0}
    
    for change in changes:
        file_path = change.get('file', 'unknown')
        change_type = change.get('type', 'unknown').upper()
        
        if file_path not in files_changed:
            files_changed[file_path] = []
        files_changed[file_path].append(change)
        
        if change_type in change_types:
            change_types[change_type] += 1
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}===== Изменения в коде ====={Colors.RESET}")
    print(f"Всего записей об изменениях: {len(changes)}")
    print(f"Затронуто файлов: {len(files_changed)}")
    print(f"Типы изменений: "
          f"{Colors.CYAN}Правки: {change_types['EDIT']}{Colors.RESET}, "
          f"{Colors.GREEN}Добавления: {change_types['ADD']}{Colors.RESET}, "
          f"{Colors.RED}Удаления: {change_types['DELETE']}{Colors.RESET}, "
          f"{Colors.MAGENTA}Ошибки: {change_types['ERROR']}{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}Последние изменения по файлам:{Colors.RESET}")
    for file_path, file_changes in files_changed.items():
        # Берем самое последнее изменение
        last_change = sorted(file_changes, key=lambda x: x.get('timestamp', ''), reverse=True)[0]
        change_type = last_change.get('type', '').upper()
        function_name = last_change.get('function', 'unknown')
        description = last_change.get('description', 'Нет описания')
        timestamp = format_timestamp(last_change.get('timestamp', 'N/A'))
        
        type_color = Colors.CYAN if change_type == 'EDIT' else \
                    Colors.GREEN if change_type == 'ADD' else \
                    Colors.RED if change_type == 'DELETE' else Colors.MAGENTA
        
        short_file = os.path.basename(file_path)
        print(f"  {type_color}{change_type}{Colors.RESET} {short_file}::{function_name} - {timestamp}")
        print(f"    {description}")

def get_recent_log_files(log_dir: str = 'logs', days: int = 7) -> List[str]:
    """Возвращает список лог-файлов за последние N дней."""
    if not os.path.exists(log_dir):
        return []
    
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    log_files = []
    
    for file_path in glob.glob(f"{log_dir}/*.log"):
        try:
            file_stat = os.stat(file_path)
            file_time = datetime.fromtimestamp(file_stat.st_mtime)
            if file_time >= cutoff:
                log_files.append(file_path)
        except:
            pass
    
    return sorted(log_files, key=lambda x: os.path.getmtime(x), reverse=True)

def show_recent_activities(log_files: List[str], limit: int = 10) -> None:
    """Показывает последние активности из лог-файлов."""
    if not log_files:
        print(f"{Colors.YELLOW}Лог-файлы не найдены{Colors.RESET}")
        return
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}===== Последние активности ====={Colors.RESET}")
    
    # Ключевые слова для поиска важных событий
    important_keywords = [
        'ERROR', 'FAIL', 'ПРЕДУПРЕЖДЕНИЕ', 'WARNING', 'API вызов', 
        'превышает', 'бюджет', 'стоимость:', 'отменено'
    ]
    activities = []
    
    for log_file in log_files[:3]:  # Берем только 3 самых свежих файла
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if any(keyword in line for keyword in important_keywords):
                        activities.append(line)
        except Exception as e:
            print(f"{Colors.RED}Ошибка при чтении лога {log_file}: {e}{Colors.RESET}")
    
    # Отображаем последние события
    if activities:
        for activity in activities[-limit:]:
            if 'ERROR' in activity or 'FAIL' in activity:
                print(f"{Colors.RED}{activity}{Colors.RESET}")
            elif 'WARNING' in activity or 'ПРЕДУПРЕЖДЕНИЕ' in activity:
                print(f"{Colors.YELLOW}{activity}{Colors.RESET}")
            elif 'API вызов' in activity:
                print(f"{Colors.BLUE}{activity}{Colors.RESET}")
            else:
                print(activity)
    else:
        print("Важных событий не обнаружено в последних логах.")

def main():
    """Основная функция программы."""
    parser = argparse.ArgumentParser(
        description="Анализ логов и статистики использования системы graphf-extractor"
    )
    parser.add_argument('--api', action='store_true', help="Показать статистику API-вызовов")
    parser.add_argument('--tests', action='store_true', help="Показать статистику тестов")
    parser.add_argument('--changes', action='store_true', help="Показать изменения в коде")
    parser.add_argument('--activities', action='store_true', help="Показать последние активности")
    parser.add_argument('--all', action='store_true', help="Показать всю статистику")
    parser.add_argument('--debug', action='store_true', help="Показать отладочную информацию")
    
    args = parser.parse_args()
    
    # Отладочный режим для диагностики проблем
    if args.debug:
        print(f"{Colors.YELLOW}== Отладочная информация =={Colors.RESET}")
        print(f"Директория logs существует: {os.path.exists('logs')}")
        if os.path.exists('logs'):
            print(f"Содержимое директории logs:")
            for item in os.listdir('logs'):
                item_path = os.path.join('logs', item)
                size = os.path.getsize(item_path) if os.path.isfile(item_path) else "директория"
                print(f"  - {item}: {size}")
    
    # Если не указаны конкретные отчеты, показываем все
    show_all = args.all or not (args.api or args.tests or args.changes or args.activities or args.debug)
    
    # Проверка существования директории для логов
    if not os.path.exists('logs'):
        print(f"{Colors.RED}Директория 'logs' не существует. Логирование не настроено или не использовалось.{Colors.RESET}")
        return
    
    print(f"{Colors.BOLD}{Colors.GREEN}===== Анализ логов системы graphf-extractor ====={Colors.RESET}")
    print(f"Время запуска: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    
    if args.api or show_all:
        analyze_api_usage()
    
    if args.tests or show_all:
        analyze_test_runs()
    
    if args.changes or show_all:
        analyze_code_changes()
    
    if args.activities or show_all:
        log_files = get_recent_log_files()
        show_recent_activities(log_files)
    
    print(f"\n{Colors.GREEN}Анализ логов завершен.{Colors.RESET}")

if __name__ == "__main__":
    main()
