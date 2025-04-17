#!/usr/bin/env python3
import os
import sys

print("===== Анализатор логов системы =====")
print(f"Текущая директория: {os.getcwd()}")
print("Содержимое директории logs:")
if os.path.exists("logs"):
    for item in os.listdir("logs"):
        print(f"  - {item}")
else:
    print("Директория logs не существует")
print("===== Анализ завершен =====")
