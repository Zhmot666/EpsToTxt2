import re
import numpy as np
import zipfile
import os
import time
from datetime import datetime
from PIL import Image
from pylibdmtx.pylibdmtx import decode

def parse_eps_to_matrix(eps_text):
    """Парсит EPS файл и создает матрицу DataMatrix кода"""
    pattern = re.compile(r"([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) rf")

    squares = []
    xs = []
    ys = []

    for match in pattern.finditer(eps_text):
        x = float(match.group(1))
        y = float(match.group(2))
        w = float(match.group(3))
        h = float(match.group(4))

        squares.append((x, y, w, h))
        xs.append(x)
        ys.append(y)

    if len(squares) == 0:
        return None

    module_size = np.mean([w for _, _, w, _ in squares])
    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)

    cols = int(round((x_max - x_min) / module_size)) + 1
    rows = int(round((y_max - y_min) / module_size)) + 1

    matrix = np.zeros((rows, cols), dtype=int)

    for (x, y, w, h) in squares:
        col = int(round((x - x_min) / module_size))
        row = int(round((y_max - y) / module_size))
        
        if 0 <= row < rows and 0 <= col < cols:
            matrix[row, col] = 1

    return matrix

def matrix_to_image(matrix, pixel_size=10, quiet_zone=4):
    """Преобразует матрицу в изображение с quiet zone"""
    height, width = matrix.shape
    
    total_width = (width + 2 * quiet_zone) * pixel_size
    total_height = (height + 2 * quiet_zone) * pixel_size
    
    img = Image.new('L', (total_width, total_height), color=255)
    pixels = img.load()

    for y in range(height):
        for x in range(width):
            color = 0 if matrix[y, x] == 1 else 255
            img_x = (x + quiet_zone) * pixel_size
            img_y = (y + quiet_zone) * pixel_size
            
            for py in range(pixel_size):
                for px in range(pixel_size):
                    pixels[img_x + px, img_y + py] = color
    return img

def decode_datamatrix(eps_content):
    """Декодирует DataMatrix код из EPS содержимого"""
    try:
        matrix = parse_eps_to_matrix(eps_content)
        if matrix is None:
            return None, "Не удалось создать матрицу"
        
        img = matrix_to_image(matrix, pixel_size=10)
        decoded = decode(img)
        
        if decoded:
            return decoded[0].data.decode('utf-8'), "Успешно"
        else:
            return None, "Код не распознан"
    except Exception as e:
        return None, f"Ошибка: {str(e)}"

def process_zip_archive(zip_path, output_dir):
    """Обрабатывает один ZIP архив с EPS файлами"""
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
            
            for eps_file in eps_files:
                print(f"  Обработка: {eps_file}")
                
                try:
                    with zip_file.open(eps_file) as f:
                        eps_content = f.read().decode('utf-8')
                    
                    code, status = decode_datamatrix(eps_content)
                    
                    if code:
                        results.append(f"{eps_file}: {code}")
                        stats['successful'] += 1
                        print(f"    ✓ {code[:50]}...")
                    else:
                        results.append(f"{eps_file}: {status}")
                        stats['failed'] += 1
                        print(f"    ✗ {status}")
                        
                except Exception as e:
                    error_msg = f"Ошибка чтения файла: {str(e)}"
                    results.append(f"{eps_file}: {error_msg}")
                    stats['failed'] += 1
                    print(f"    ✗ {error_msg}")
    
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

def main():
    """Основная функция для пакетной обработки"""
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
    for zip_file in zip_files:
        zip_path = os.path.join(input_dir, zip_file)
        stats = process_zip_archive(zip_path, output_dir)
        
        total_stats['archives_processed'] += 1
        total_stats['total_files'] += stats['total_files']
        total_stats['total_successful'] += stats['successful']
        total_stats['total_failed'] += stats['failed']
        total_stats['total_time'] += stats['processing_time']
        
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

if __name__ == "__main__":
    main()