#!/usr/bin/env python3
"""
OEEG Plot Streamlit Launcher
Специальный лаунчер для Streamlit приложения (совместимый с PyInstaller)
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path


def get_resource_path(relative_path):
    """Получает правильный путь к ресурсам для PyInstaller"""
    try:
        # PyInstaller создает временную папку и сохраняет путь в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Если не PyInstaller, используем обычный путь
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def find_main_module():
    """Находит главный модуль приложения"""
    if getattr(sys, 'frozen', False):
        # Запущено из PyInstaller - проверяем разные варианты
        exe_dir = Path(sys.executable).parent

        # Вариант 1: main.py в папке с exe (для COLLECT)
        main_path = exe_dir / 'main.py'
        if main_path.exists():
            print(f"Найден главный модуль: {main_path}")
            return main_path

        # Вариант 2: main.py во внутренней папке _internal (новые версии PyInstaller)
        internal_path = exe_dir / '_internal' / 'main.py'
        if internal_path.exists():
            print(f"Найден главный модуль: {internal_path}")
            return internal_path

        # Вариант 3: main.py в ресурсах _MEIPASS
        try:
            resource_path = Path(get_resource_path('main.py'))
            if resource_path.exists():
                print(f"Найден главный модуль в ресурсах: {resource_path}")
                return resource_path
        except:
            pass

        # Вариант 4: копируем из ресурсов в рабочую папку
        try:
            import shutil
            resource_path = Path(sys._MEIPASS) / 'main.py'
            if resource_path.exists():
                target_path = exe_dir / 'main.py'
                print(f"Копирование main.py из ресурсов в {target_path}")
                shutil.copy2(resource_path, target_path)
                return target_path
        except Exception as e:
            print(f"Ошибка при копировании: {e}")
    else:
        # Обычный запуск
        current_dir = Path(__file__).parent
        main_path = current_dir / 'main.py'

        if main_path.exists():
            print(f"Найден главный модуль: {main_path}")
            return main_path

    print("Ошибка: Файл main.py не найден!")
    return None


def check_streamlit_installation():
    """Проверяет установку Streamlit"""
    try:
        import streamlit
        print(f"Streamlit найден: версия {streamlit.__version__}")
        return True
    except ImportError:
        print("❌ ОШИБКА: Streamlit не установлен!")
        print("Установите Streamlit: pip install streamlit")
        return False


def wait_for_server(url, timeout=30):
    """Ждет запуска Streamlit сервера"""
    import urllib.request
    import urllib.error

    print("Ожидание запуска сервера...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = urllib.request.urlopen(url, timeout=2)
            if response.getcode() == 200:
                return True
        except (urllib.error.URLError, OSError, Exception):
            time.sleep(1)

    return False


def run_streamlit_app(main_path):
    """Запускает Streamlit приложение"""
    try:
        # Проверяем установку Streamlit
        if not check_streamlit_installation():
            return False

        # Настройка окружения
        project_dir = str(main_path.parent)
        env = os.environ.copy()

        # Добавляем пути в PYTHONPATH
        paths_to_add = [project_dir]

        # Если запущено из PyInstaller, добавляем путь к временной директории
        if getattr(sys, 'frozen', False):
            try:
                paths_to_add.append(sys._MEIPASS)
                # Добавляем также папку exe для COLLECT сборки
                exe_dir = str(Path(sys.executable).parent)
                paths_to_add.append(exe_dir)
            except:
                pass

        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = os.pathsep.join(paths_to_add) + os.pathsep + env['PYTHONPATH']
        else:
            env['PYTHONPATH'] = os.pathsep.join(paths_to_add)

        # Параметры для Streamlit
        port = 8501
        url = f"http://localhost:{port}"

        print(f"Запуск Streamlit приложения...")
        print(f"URL: {url}")
        print("Для остановки приложения нажмите Ctrl+C в этом окне")
        print("-" * 50)

        # Определяем способ запуска
        if getattr(sys, 'frozen', False):
            # Для PyInstaller - попробуем запустить через встроенный Python
            try:
                # Способ 1: используем встроенный streamlit
                import streamlit.web.cli as stcli
                sys.argv = [
                    "streamlit", "run", str(main_path),
                    "--server.port", str(port),
                    "--server.headless", "true",
                    "--browser.gatherUsageStats", "false",
                    "--server.fileWatcherType", "none",
                    "--server.enableCORS", "false",
                    "--server.enableXsrfProtection", "false"
                ]

                print("Запуск через встроенный Streamlit...")

                # Открываем браузер в отдельном потоке
                def open_browser():
                    if wait_for_server(url, timeout=30):
                        print(f"✅ Сервер запущен! Открываем браузер...")
                        try:
                            webbrowser.open(url)
                        except Exception as e:
                            print(f"⚠️ Не удалось открыть браузер: {e}")
                            print(f"Откройте браузер вручную: {url}")
                    else:
                        print("⚠️ Не удалось дождаться запуска сервера")
                        print(f"Попробуйте открыть браузер вручную: {url}")

                browser_thread = threading.Thread(target=open_browser, daemon=True)
                browser_thread.start()

                # Запускаем Streamlit напрямую
                stcli.main()
                return True

            except Exception as e:
                print(f"Ошибка прямого запуска: {e}")
                print("Пробуем запуск через subprocess...")

            # Способ 2: через subprocess с системным Python
            python_executable = "python"
            try:
                result = subprocess.run([python_executable, "-c", "import streamlit; print('OK')"],
                                        capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    python_executable = "python3"
            except:
                python_executable = "python3"
        else:
            python_executable = sys.executable

        # Команда для запуска Streamlit через subprocess
        cmd = [
            python_executable, "-m", "streamlit", "run",
            str(main_path),
            "--server.port", str(port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--server.fileWatcherType", "none",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false"
        ]

        print(f"Выполняемая команда: {' '.join(cmd)}")
        print(f"Рабочая директория: {project_dir}")

        # Запускаем процесс
        process = subprocess.Popen(
            cmd,
            env=env,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # Функция для вывода логов Streamlit
        def print_output():
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[Streamlit] {line.rstrip()}")

        # Запускаем вывод логов в отдельном потоке
        output_thread = threading.Thread(target=print_output, daemon=True)
        output_thread.start()

        # Ждем запуска сервера и открываем браузер
        def open_browser():
            if wait_for_server(url, timeout=45):
                print(f"✅ Сервер запущен! Открываем браузер...")
                try:
                    webbrowser.open(url)
                except Exception as e:
                    print(f"⚠️ Не удалось открыть браузер: {e}")
                    print(f"Откройте браузер вручную: {url}")
            else:
                print("⚠️ Не удалось дождаться запуска сервера")
                print(f"Попробуйте открыть браузер вручную: {url}")

        # Запускаем открытие браузера в отдельном потоке
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()

        # Ждем завершения процесса
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n⚠️ Получен сигнал прерывания...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        return True

    except KeyboardInterrupt:
        print("\n⚠️ Приложение остановлено пользователем")
        if 'process' in locals():
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
        return True
    except FileNotFoundError as e:
        print(f"❌ ОШИБКА: Не найден исполняемый файл: {e}")
        print("Убедитесь, что Python и Streamlit установлены в системе")
        return False
    except Exception as e:
        print(f"❌ ОШИБКА при запуске Streamlit: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Главная функция лаунчера"""
    print("=== OEEG Plot Streamlit Launcher ===")

    # Определяем режим запуска
    if getattr(sys, 'frozen', False):
        print("Режим: Скомпилированное приложение (PyInstaller)")
    else:
        print("Режим: Обычный Python скрипт")

    print("Поиск главного модуля приложения...")

    # Находим главный модуль
    main_module_path = find_main_module()

    if not main_module_path:
        print("\n❌ ОШИБКА: Файл main.py не найден!")
        print("\nВозможные решения:")
        print("1. Убедитесь, что файл main.py находится в той же директории, что и исполняемый файл")
        print("2. При сборке с PyInstaller добавьте main.py в спецификацию:")
        print("   pyinstaller --add-data 'main.py;.' launcher.py")
        print("3. Или скопируйте main.py в директорию с исполняемым файлом")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

    print(f"Запуск Streamlit приложения...")
    print("-" * 40)

    # Запускаем Streamlit приложение
    success = run_streamlit_app(main_module_path)

    print("-" * 40)
    if not success:
        print("❌ Приложение завершилось с ошибкой")
    else:
        print("✅ Приложение завершилось")

    print("Для закрытия окна нажмите Enter...")
    input()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Приложение прервано пользователем")
        print("Для закрытия окна нажмите Enter...")
        input()
    except Exception as e:
        print(f"💥 КРИТИЧЕСКАЯ ОШИБКА ЛАУНЧЕРА: {e}")
        print("\nПолная информация об ошибке:")
        import traceback

        traceback.print_exc()
        print("\nДля закрытия окна нажмите Enter...")
        input()