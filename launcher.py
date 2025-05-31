#!/usr/bin/env python3
"""
OEEG Plot Launcher
Универсальный лаунчер для приложения OEEG Plot
"""

import os
import sys
import importlib.util
from pathlib import Path


def find_main_module():
    """Находит и возвращает главный модуль приложения"""

    # Список возможных имен главного файла в порядке приоритета
    possible_mains = [
        'main.py',
        'app.py',
        'OEEG_plot.py',
        'oeeg_plot.py',
        'gui.py',
        'interface.py'
    ]

    current_dir = Path(__file__).parent

    # Ищем главный файл
    for main_file in possible_mains:
        main_path = current_dir / main_file
        if main_path.exists():
            print(f"Найден главный модуль: {main_file}")
            return main_path

    # Если не нашли стандартные имена, ищем любой .py файл с функцией main()
    for py_file in current_dir.glob("*.py"):
        if py_file.name == "launcher.py":  # Пропускаем сам лаунчер
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'def main(' in content or 'if __name__ == "__main__"' in content:
                    print(f"Найден возможный главный модуль: {py_file.name}")
                    return py_file
        except Exception:
            continue

    return None


def load_and_run_module(module_path):
    """Загружает и запускает модуль"""
    try:
        # Загружаем модуль
        spec = importlib.util.spec_from_file_location("main_module", module_path)
        module = importlib.util.module_from_spec(spec)

        # Добавляем путь к модулю в sys.path для корректного импорта зависимостей
        module_dir = str(module_path.parent)
        if module_dir not in sys.path:
            sys.path.insert(0, module_dir)

        # Выполняем модуль
        spec.loader.exec_module(module)

        # Если есть функция main(), запускаем её
        if hasattr(module, 'main'):
            print("Запуск функции main()...")
            module.main()
        else:
            print("Модуль загружен и выполнен")

    except Exception as e:
        print(f"Ошибка при запуске модуля: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def main():
    """Главная функция лаунчера"""
    print("=== OEEG Plot Launcher ===")
    print("Поиск главного модуля приложения...")

    # Находим главный модуль
    main_module_path = find_main_module()

    if not main_module_path:
        print("Ошибка: Не удалось найти главный модуль приложения!")
        print("Убедитесь, что в директории есть один из файлов:")
        print("- main.py")
        print("- app.py")
        print("- OEEG_plot.py")
        print("- oeeg_plot.py")
        print("- или любой .py файл с функцией main() или блоком if __name__ == '__main__'")
        input("Нажмите Enter для выхода...")
        sys.exit(1)

    print(f"Запуск {main_module_path.name}...")
    print("-" * 40)

    # Запускаем найденный модуль
    success = load_and_run_module(main_module_path)

    if not success:
        print("-" * 40)
        print("Приложение завершилось с ошибкой")
        input("Нажмите Enter для выхода...")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nПриложение прервано пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"Критическая ошибка лаунчера: {e}")
        import traceback

        traceback.print_exc()
        input("Нажмите Enter для выхода...")
        sys.exit(1)