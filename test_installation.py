#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест установки всех компонентов EpsToTxt2
Проверяет наличие всех необходимых зависимостей
"""

import sys
import os

def test_python_version():
    """Проверка версии Python"""
    print("🐍 Проверка версии Python...")
    version = sys.version_info
    print(f"   Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("   ❌ Требуется Python 3.7 или выше!")
        return False
    else:
        print("   ✅ Версия Python подходит")
        return True

def test_basic_imports():
    """Проверка основных библиотек"""
    print("\n📚 Проверка основных библиотек...")
    
    tests = [
        ("numpy", "NumPy"),
        ("PIL", "Pillow (PIL)"),
        ("pylibdmtx.pylibdmtx", "pylibdmtx"),
    ]
    
    success = True
    for module, name in tests:
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError as e:
            print(f"   ❌ {name} - {e}")
            success = False
    
    return success

def test_gui_imports():
    """Проверка GUI библиотек"""
    print("\n🖥️ Проверка GUI библиотек...")
    
    # Сначала пробуем PyQt5
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QFont
        print("   ✅ PyQt5")
        return True, "PyQt5"
    except ImportError:
        print("   ❌ PyQt5 не найден")
    
    # Потом пробуем PyQt6
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont
        print("   ✅ PyQt6")
        return True, "PyQt6"
    except ImportError:
        print("   ❌ PyQt6 не найден")
    
    print("   ❌ Ни PyQt5, ни PyQt6 не установлены!")
    return False, None

def test_main_module():
    """Проверка основного модуля"""
    print("\n🔧 Проверка основного модуля...")
    
    try:
        from main import parse_eps_to_matrix, decode_datamatrix, clear_cache
        print("   ✅ main.py импортируется корректно")
        return True
    except ImportError as e:
        print(f"   ❌ Ошибка импорта main.py: {e}")
        return False

def test_gui_module():
    """Проверка GUI модуля"""
    print("\n🎨 Проверка GUI модуля...")
    
    try:
        # Проверяем только импорт, не запускаем GUI
        import gui_main
        print("   ✅ gui_main.py импортируется корректно")
        return True
    except ImportError as e:
        print(f"   ❌ Ошибка импорта gui_main.py: {e}")
        return False

def test_directories():
    """Проверка структуры папок"""
    print("\n📁 Проверка структуры папок...")
    
    required_dirs = ["In", "Out"]
    success = True
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"   ✅ Папка {dir_name}/ существует")
        else:
            print(f"   ⚠️ Папка {dir_name}/ не найдена, создаю...")
            try:
                os.makedirs(dir_name, exist_ok=True)
                print(f"   ✅ Папка {dir_name}/ создана")
            except Exception as e:
                print(f"   ❌ Не удалось создать папку {dir_name}/: {e}")
                success = False
    
    return success

def test_optional_tools():
    """Проверка дополнительных инструментов"""
    print("\n🛠️ Проверка дополнительных инструментов...")
    
    try:
        import PyInstaller
        print(f"   ✅ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("   ⚠️ PyInstaller не установлен (нужен для сборки exe)")
    
    return True

def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("🧪 ТЕСТ УСТАНОВКИ EpsToTxt2")
    print("=" * 60)
    
    all_tests = [
        test_python_version(),
        test_basic_imports(),
        test_main_module(),
        test_directories(),
    ]
    
    gui_success, gui_lib = test_gui_imports()
    all_tests.append(gui_success)
    
    if gui_success:
        all_tests.append(test_gui_module())
    
    test_optional_tools()
    
    print("\n" + "=" * 60)
    if all(all_tests):
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("=" * 60)
        print("\n✅ Готово к использованию:")
        print("   • Консольная версия: python main.py")
        if gui_success:
            print("   • GUI версия: python gui_main.py")
            print(f"   • Используется: {gui_lib}")
        print("   • Сборка exe: python build_exe.py")
    else:
        print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ!")
        print("=" * 60)
        print("\n🔧 Для исправления:")
        print("   pip install -r requirements.txt")
        if not gui_success:
            print("   pip install PyQt5")
        print("\n📖 Подробнее в файле TROUBLESHOOTING.md")
    
    print("\n📋 Информация о системе:")
    print(f"   • Python: {sys.version}")
    print(f"   • Платформа: {sys.platform}")
    print(f"   • Рабочая папка: {os.getcwd()}")

if __name__ == "__main__":
    main()
