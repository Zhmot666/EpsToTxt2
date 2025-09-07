import re
import numpy as np
import zipfile
import os
import time
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import lru_cache
from PIL import Image
from pylibdmtx.pylibdmtx import decode

# Компилируем regex один раз для повышения производительности
_EPS_PATTERN = re.compile(r"([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) rf")

@lru_cache(maxsize=128)
def _get_content_hash(content):
    """Создает хеш для кэширования"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def parse_eps_to_matrix(eps_text):
    """Парсит EPS файл и создает матрицу DataMatrix кода (оптимизированная версия)"""
    # Используем findall для более быстрого извлечения всех совпадений сразу
    matches = _EPS_PATTERN.findall(eps_text)
    
    if not matches:
        return None

    # Преобразуем все координаты в numpy массивы сразу
    coords = np.array(matches, dtype=np.float32)
    if coords.size == 0:
        return None
    
    xs, ys, ws, hs = coords[:, 0], coords[:, 1], coords[:, 2], coords[:, 3]
    
    # Векторизованные вычисления
    module_size = np.mean(ws)
    x_min, x_max = np.min(xs), np.max(xs)
    y_min, y_max = np.min(ys), np.max(ys)

    cols = int(round((x_max - x_min) / module_size)) + 1
    rows = int(round((y_max - y_min) / module_size)) + 1

    # Векторизованное создание матрицы
    matrix = np.zeros((rows, cols), dtype=np.uint8)
    
    # Векторизованное вычисление индексов
    cols_idx = np.round((xs - x_min) / module_size).astype(np.int32)
    rows_idx = np.round((y_max - ys) / module_size).astype(np.int32)
    
    # Фильтруем валидные индексы
    valid_mask = (rows_idx >= 0) & (rows_idx < rows) & (cols_idx >= 0) & (cols_idx < cols)
    valid_rows = rows_idx[valid_mask]
    valid_cols = cols_idx[valid_mask]
    
    # Устанавливаем значения одним действием
    matrix[valid_rows, valid_cols] = 1

    return matrix

def matrix_to_image(matrix, pixel_size=10, quiet_zone=4):
    """Преобразует матрицу в изображение с quiet zone (оптимизированная версия)"""
    height, width = matrix.shape
    
    total_width = (width + 2 * quiet_zone) * pixel_size
    total_height = (height + 2 * quiet_zone) * pixel_size
    
    # Создаем полный массив изображения сразу
    img_array = np.full((total_height, total_width), 255, dtype=np.uint8)
    
    # Векторизованное создание изображения
    # Создаем увеличенную матрицу с помощью repeat
    enlarged_matrix = np.repeat(np.repeat(matrix, pixel_size, axis=0), pixel_size, axis=1)
    
    # Вычисляем смещения для quiet zone
    start_y = quiet_zone * pixel_size
    start_x = quiet_zone * pixel_size
    end_y = start_y + height * pixel_size
    end_x = start_x + width * pixel_size
    
    # Применяем матрицу к изображению (инвертируем: 1->0, 0->255)
    img_array[start_y:end_y, start_x:end_x] = np.where(enlarged_matrix == 1, 0, 255)
    
    # Создаем изображение из массива
    return Image.fromarray(img_array, mode='L')

# Кэш для результатов декодирования
_DECODE_CACHE = {}

def decode_datamatrix(eps_content):
    """Декодирует DataMatrix код из EPS содержимого (с кэшированием)"""
    # Проверяем кэш
    content_hash = _get_content_hash(eps_content)
    if content_hash in _DECODE_CACHE:
        return _DECODE_CACHE[content_hash]
    
    try:
        matrix = parse_eps_to_matrix(eps_content)
        if matrix is None:
            result = (None, "Не удалось создать матрицу")
            _DECODE_CACHE[content_hash] = result
            return result
        
        img = matrix_to_image(matrix, pixel_size=10)
        decoded = decode(img)
        
        if decoded:
            result = (decoded[0].data.decode('utf-8'), "Успешно")
        else:
            result = (None, "Код не распознан")
            
        # Кэшируем результат
        _DECODE_CACHE[content_hash] = result
        return result
        
    except Exception as e:
        result = (None, f"Ошибка: {str(e)}")
        _DECODE_CACHE[content_hash] = result
        return result

def _process_single_eps_file(args):
    """Обрабатывает один EPS файл (для многопоточности)"""
    zip_path, eps_file = args
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            with zip_file.open(eps_file) as f:
                eps_content = f.read().decode('utf-8')
        
        code, status = decode_datamatrix(eps_content)
        
        if code:
            return eps_file, code, True, None
        else:
            return eps_file, None, False, status
            
    except Exception as e:
        return eps_file, None, False, f"Ошибка чтения файла: {str(e)}"

def process_zip_archive(zip_path, output_dir, max_workers=None):
    """Обрабатывает один ZIP архив с EPS файлами (с многопоточностью)"""
    archive_name = os.path.splitext(os.path.basename(zip_path))[0]
    results = []
    stats = {
        'total_files': 0,
        'successful': 0,
        'failed': 0,
        'start_time': time.time()
    }
    
    print(f"Обработка архива: {archive_name}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            eps_files = [f for f in zip_file.namelist() if f.lower().endswith('.eps')]
            stats['total_files'] = len(eps_files)
            
            if not eps_files:
                print("  В архиве не найдено EPS файлов")
                return stats
            
            # Определяем количество потоков
            if max_workers is None:
                max_workers = min(len(eps_files), os.cpu_count() or 1)
            
            print(f"  Использую {max_workers} потоков для {len(eps_files)} файлов")
            
            # Подготавливаем аргументы для многопоточной обработки
            file_args = [(zip_path, eps_file) for eps_file in eps_files]
            
            # Обрабатываем файлы параллельно
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for eps_file, code, success, error_msg in executor.map(_process_single_eps_file, file_args):
                    if success:
                        results.append(f"{eps_file}: {code}")
                        stats['successful'] += 1
                        print(f"  ✓ {eps_file}: {code[:50]}...")
                    else:
                        results.append(f"{eps_file}: {error_msg}")
                        stats['failed'] += 1
                        print(f"  ✗ {eps_file}: {error_msg}")
    
    except Exception as e:
        error_msg = f"Ошибка открытия архива: {str(e)}"
        results.append(error_msg)
        stats['failed'] += 1
        print(f"  ✗ {error_msg}")
    
    stats['end_time'] = time.time()
    stats['processing_time'] = stats['end_time'] - stats['start_time']
    
    # Сохраняем только коды в файл
    output_file = os.path.join(output_dir, f"{archive_name}_results.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            # Извлекаем только код из строки "файл: код"
            if ": " in result and not result.startswith("Ошибка"):
                code = result.split(": ", 1)[1]
                f.write(code + "\n")
    
    print(f"  Результаты сохранены в: {output_file}")
    print(f"  Статистика: {stats['successful']}/{stats['total_files']} успешно, {stats['failed']} ошибок, {stats['processing_time']:.2f}с")
    return stats

def clear_cache():
    """Очищает кэш для освобождения памяти"""
    global _DECODE_CACHE
    _DECODE_CACHE.clear()
    _get_content_hash.cache_clear()

def main():
    """Основная функция для пакетной обработки (оптимизированная версия)"""
    input_dir = "In"
    output_dir = "Out"
    
    # Создаем папку Out если не существует
    os.makedirs(output_dir, exist_ok=True)
    
    # Находим все ZIP файлы в папке In
    zip_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.zip')]
    
    if not zip_files:
        print("В папке 'In' не найдено ZIP файлов")
        return
    
    print(f"Найдено ZIP файлов: {len(zip_files)}")
    print(f"Доступно ядер процессора: {os.cpu_count()}")
    print("=" * 60)
    
    # Общая статистика
    total_stats = {
        'archives_processed': 0,
        'total_files': 0,
        'total_successful': 0,
        'total_failed': 0,
        'total_time': 0,
        'start_time': time.time()
    }
    
    # Обрабатываем каждый архив
    for i, zip_file in enumerate(zip_files):
        zip_path = os.path.join(input_dir, zip_file)
        stats = process_zip_archive(zip_path, output_dir)
        
        total_stats['archives_processed'] += 1
        total_stats['total_files'] += stats['total_files']
        total_stats['total_successful'] += stats['successful']
        total_stats['total_failed'] += stats['failed']
        total_stats['total_time'] += stats['processing_time']
        
        # Очищаем кэш каждые 5 архивов для экономии памяти
        if (i + 1) % 5 == 0:
            clear_cache()
            print(f"  Кэш очищен после {i + 1} архивов")
        
        print("-" * 60)
    
    total_stats['end_time'] = time.time()
    total_stats['total_processing_time'] = total_stats['end_time'] - total_stats['start_time']
    
    # Статистика выводится только в консоль
    
    print("=" * 60)
    print("ОБРАБОТКА ЗАВЕРШЕНА")
    print(f"Время начала: {datetime.fromtimestamp(total_stats['start_time']).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Время окончания: {datetime.fromtimestamp(total_stats['end_time']).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Обработано архивов: {total_stats['archives_processed']}")
    print(f"Всего EPS файлов: {total_stats['total_files']}")
    print(f"Успешно декодировано: {total_stats['total_successful']}")
    print(f"Ошибок: {total_stats['total_failed']}")
    print(f"Общее время выполнения: {total_stats['total_processing_time']:.2f} секунд")
    print(f"Среднее время на файл: {total_stats['total_time']/max(total_stats['total_files'], 1):.2f} секунд")
    print(f"Процент успеха: {(total_stats['total_successful']/max(total_stats['total_files'], 1)*100):.1f}%")
    print(f"Результаты (только коды) сохранены в папке: {output_dir}")
    
    # Финальная очистка памяти
    clear_cache()

if __name__ == "__main__":
    main()