# Устранение неполадок EpsToTxt2

## 🔧 Исправление проблем с PyQt

### Проблема: "DLL load failed while importing QtCore"

Эта ошибка возникает при использовании PyQt6 на некоторых системах Windows.

#### Решение:
1. **Удалите PyQt6:**
   ```bash
   pip uninstall PyQt6 -y
   ```

2. **Установите PyQt5:**
   ```bash
   pip install PyQt5
   ```

3. **Проверьте установку:**
   ```bash
   python -c "from PyQt5.QtWidgets import QApplication; print('PyQt5 работает!')"
   ```

### Альтернативные решения:

#### Вариант 1: Переустановка PyQt6
```bash
pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip -y
pip install PyQt6
```

#### Вариант 2: Использование conda
```bash
conda install pyqt
```

## 🐛 Другие распространенные проблемы

### Проблема: "ModuleNotFoundError: No module named 'pylibdmtx'"
```bash
pip install pylibdmtx
```

### Проблема: Ошибки с NumPy
```bash
pip install --upgrade numpy
```

### Проблема: Ошибки с PIL/Pillow
```bash
pip uninstall PIL Pillow -y
pip install Pillow
```

## ✅ Проверка работоспособности

### Консольная версия:
```bash
python main.py
```
Должно показать: "В папке 'In' не найдено ZIP файлов"

### GUI версия:
```bash
python gui_main.py
```
Должно открыться окно приложения

## 📦 Сборка исполняемого файла

### Требования:
```bash
pip install pyinstaller
pip install -r requirements.txt
```

### Сборка:
```bash
python build_exe.py
```

### Если сборка не работает:
1. Очистите кэш PyInstaller:
   ```bash
   pyinstaller --clean gui_main.py
   ```

2. Переустановите PyInstaller:
   ```bash
   pip uninstall pyinstaller -y
   pip install pyinstaller
   ```

## 🔍 Диагностика

### Проверка зависимостей:
```bash
pip list | findstr -i "pyqt numpy pillow pylibdmtx"
```

### Проверка Python версии:
```bash
python --version
```
Требуется Python 3.7 или выше.

## 💡 Рекомендации

1. **Используйте виртуальное окружение:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Обновите pip:**
   ```bash
   python -m pip install --upgrade pip
   ```

3. **Для старых систем Windows используйте PyQt5 вместо PyQt6**

---

Если проблемы продолжаются, проверьте:
- Версию Windows (рекомендуется Windows 10/11)
- Наличие Visual C++ Redistributable
- Права администратора при установке пакетов
