#!/usr/bin/env python3
"""
Простой скрипт для просмотра и анализа логов.
"""
import os
import sys
import json
import glob
from datetime import datetime

def print_separator(title):
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50)

def main():
    print_separator("Анализ логов системы")
    print(f"Время запуска: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    
    # Проверяем наличие директории с логами
    if not os.path.exists('logs'):
        print("\nДиректория 'logs' не существует")
        return
    
    # Список файлов в директории logs
    print("\nСодержимое директории logs:")
    log_files = os.listdir('logs')
    for item in log_files:
        item_path = os.path.join('logs', item)
        if os.path.isfile(item_path):
            size = os.path.getsize(item_path)
            print(f"  - {item}: {size} байт")
        else:
            print(f"  - {item}: директория")
    
    # Анализ файла api_usage_stats.json, если он существует
    api_stats_file = 'logs/api_usage_stats.json'
    if os.path.exists(api_stats_file) and os.path.getsize(api_stats_file) > 0:
        print_separator("Статистика API-вызовов")
        try:
            with open(api_stats_file, 'r') as f:
                stats = json.load(f)
                print(f"Всего вызовов API: {stats.get('calls_count', 0)}")
                print(f"Общая оценка стоимости: ${stats.get('total_cost_estimate', 0):.4f}")
                print("\nВызовы по моделям:")
                for model, model_stats in stats.get('calls_by_model', {}).items():
                    print(f"  - {model}: {model_stats.get('count', 0)} вызовов, "
                         f"${model_stats.get('total_cost', 0):.4f}")
        except Exception as e:
            print(f"Ошибка при чтении файла статистики API: {e}")
    else:
        print("\nФайл статистики API-вызовов не найден или пуст")
    
    # Анализ файлов с логами
    log_file_paths = glob.glob('logs/*.log')
    if log_file_paths:
        print_separator("Содержимое лог-файлов")
        for log_path in log_file_paths[:2]:  # Показываем только первые 2 файла
            print(f"\nФайл: {os.path.basename(log_path)}")
            try:
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        for i, line in enumerate(lines[:10]):  # Показываем только первые 10 строк
                            print(f"{i+1}: {line.strip()}")
                        if len(lines) > 10:
                            print(f"... и еще {len(lines) - 10} строк")
                    else:
                        print("Файл пуст")
            except Exception as e:
                print(f"Ошибка при чтении лог-файла: {e}")
    else:
        print("\nЛог-файлы (*.log) не найдены")
    
    # Проверяем файл test_runs.jsonl
    test_runs_file = 'logs/test_runs.jsonl'
    if os.path.exists(test_runs_file) and os.path.getsize(test_runs_file) > 0:
        print_separator("Запуски тестов")
        try:
            test_runs = []
            with open(test_runs_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        test_runs.append(json.loads(line))
            
            print(f"Всего записей о запусках тестов: {len(test_runs)}")
            for i, run in enumerate(test_runs[:5]):  # Показываем только первые 5 запусков
                print(f"\n{i+1}. Тест: {run.get('test_name', 'неизвестно')}")
                print(f"   Статус: {run.get('status', 'неизвестно')}")
                print(f"   Время: {run.get('timestamp', 'неизвестно')}")
                
            if len(test_runs) > 5:
                print(f"\n... и еще {len(test_runs) - 5} записей")
        except Exception as e:
            print(f"Ошибка при чтении файла запусков тестов: {e}")
    else:
        print("\nФайл запусков тестов не найден или пуст")
    
    print_separator("Анализ завершен")

if __name__ == "__main__":
    main()
