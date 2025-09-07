#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для сборки EpsToTxt2 в исполняемый файл для Windows
Использует PyInstaller для создания standalone приложения
"""

import os
import sys
import shutil
from pathlib import Path

def create_spec_file():
    """Создание .spec файла для PyInstaller"""
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['gui_main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pylibdmtx.pylibdmtx',
        'numpy',
        'PIL',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EpsToTxt2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon='icon.ico'
)
'''
    
    with open('EpsToTxt2.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content.strip())

def create_version_info():
    """Создание файла информации о версии"""
    version_info = '''
# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=(2, 0, 0, 0),
    prodvers=(2, 0, 0, 0),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x4,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Peltik'),
        StringStruct(u'FileDescription', u'EpsToTxt2 - Обработка DataMatrix кодов'),
        StringStruct(u'FileVersion', u'2.0.0.0'),
        StringStruct(u'InternalName', u'EpsToTxt2'),
        StringStruct(u'LegalCopyright', u'© 2025 Peltik'),
        StringStruct(u'OriginalFilename', u'EpsToTxt2.exe'),
        StringStruct(u'ProductName', u'EpsToTxt2'),
        StringStruct(u'ProductVersion', u'2.0.0.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_info.strip())

def create_icon():
    """Создание простой иконки (заглушка)"""
    # В реальном проекте здесь должна быть настоящая иконка
    # Пока создаем пустой файл как заглушку
    if not os.path.exists('icon.ico'):
        # Создаем минимальную иконку 16x16 пикселей
        from PIL import Image, ImageDraw
        
        # Создаем изображение 32x32 для иконки
        img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Рисуем простую иконку - синий квадрат с белым текстом
        draw.rectangle([2, 2, 30, 30], fill=(74, 144, 226, 255))
        draw.text((8, 12), "ET", fill=(255, 255, 255, 255))
        
        img.save('icon.ico', format='ICO')
        print("✅ Создана иконка icon.ico")

def build_executable():
    """Основная функция сборки"""
    print("🚀 Начинаем сборку EpsToTxt2 в исполняемый файл...")
    
    # Проверяем наличие необходимых файлов
    required_files = ['gui_main.py', 'main.py']
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Ошибка: файл {file} не найден!")
            return False
    
    # Создаем необходимые файлы для сборки
    print("📝 Создаем файлы конфигурации...")
    create_spec_file()
    create_version_info()
    create_icon()
    
    # Проверяем наличие PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller найден: версия {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller не установлен!")
        print("Установите его командой: pip install pyinstaller")
        return False
    
    # Запускаем сборку
    print("🔨 Запускаем PyInstaller...")
    
    # Очищаем предыдущие сборки
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')
    
    # Команда сборки
    import subprocess
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',                    # Один файл
        '--windowed',                   # Без консоли
        '--name=EpsToTxt2',            # Имя файла
        '--icon=icon.ico',             # Иконка
        '--version-file=version_info.txt',  # Информация о версии
        '--add-data=README.md;.',      # Добавляем README
        '--add-data=OPTIMIZATIONS.md;.',  # Добавляем документацию
        '--hidden-import=pylibdmtx.pylibdmtx',
        '--hidden-import=numpy',
        '--hidden-import=PIL',
        'gui_main.py'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Сборка завершена успешно!")
        
        # Проверяем результат
        exe_path = Path('dist') / 'EpsToTxt2.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📦 Создан файл: {exe_path}")
            print(f"📏 Размер: {size_mb:.1f} MB")
            
            # Создаем папки In и Out рядом с exe
            dist_path = Path('dist')
            (dist_path / 'In').mkdir(exist_ok=True)
            (dist_path / 'Out').mkdir(exist_ok=True)
            
            # Копируем документацию
            if os.path.exists('README.md'):
                shutil.copy2('README.md', dist_path / 'README.md')
            if os.path.exists('OPTIMIZATIONS.md'):
                shutil.copy2('OPTIMIZATIONS.md', dist_path / 'OPTIMIZATIONS.md')
            
            print("📁 Созданы папки In и Out")
            print("📋 Скопирована документация")
            print(f"🎉 Готовое приложение находится в папке: {dist_path.absolute()}")
            
            return True
        else:
            print("❌ Исполняемый файл не создан!")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка сборки: {e}")
        print(f"Вывод: {e.stdout}")
        print(f"Ошибки: {e.stderr}")
        return False

def clean_build_files():
    """Очистка временных файлов сборки"""
    files_to_remove = [
        'EpsToTxt2.spec',
        'version_info.txt',
        'icon.ico'
    ]
    
    dirs_to_remove = [
        'build',
        '__pycache__'
    ]
    
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑 Удален: {file}")
    
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"🗑 Удалена папка: {dir_name}")

if __name__ == "__main__":
    print("=" * 60)
    print("EpsToTxt2 - Сборка исполняемого файла для Windows")
    print("=" * 60)
    
    success = build_executable()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ СБОРКА ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)
        print("\n📋 Инструкции по использованию:")
        print("1. Перейдите в папку dist/")
        print("2. Поместите ZIP архивы в папку In/")
        print("3. Запустите EpsToTxt2.exe")
        print("4. Результаты будут в папке Out/")
        
        # Спрашиваем об очистке
        response = input("\n🗑 Очистить временные файлы сборки? (y/n): ")
        if response.lower() in ['y', 'yes', 'д', 'да']:
            clean_build_files()
            print("✅ Временные файлы очищены")
    else:
        print("\n" + "=" * 60)
        print("❌ СБОРКА ЗАВЕРШИЛАСЬ С ОШИБКОЙ!")
        print("=" * 60)
        print("\n🔧 Проверьте:")
        print("1. Установлен ли PyInstaller: pip install pyinstaller")
        print("2. Все ли зависимости установлены: pip install -r requirements.txt")
        print("3. Нет ли ошибок в коде")
