#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EpsToTxt2 GUI - Графический интерфейс для обработки DataMatrix кодов
Современный интерфейс на PyQt6 с темной темой и анимациями
"""

import sys
import os
import time
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QPushButton, QLabel, QTextEdit, QProgressBar, 
    QFileDialog, QMessageBox, QFrame, QScrollArea, QGroupBox,
    QSpinBox, QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMenuBar, QStatusBar, QSplitter, QLineEdit
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, 
    QEasingCurve, QRect, QSize, QSettings
)
from PyQt5.QtGui import (
    QFont, QIcon, QPalette, QColor, QPixmap, QPainter, 
    QLinearGradient, QFontDatabase
)
from PyQt5.QtWidgets import QAction

# Импортируем основную логику
from main import process_zip_archive, clear_cache

class ModernButton(QPushButton):
    """Современная кнопка с эффектами наведения"""
    
    def __init__(self, text="", icon=None, primary=False):
        super().__init__(text)
        self.primary = primary
        self.setMinimumHeight(40)
        self.setFont(QFont("Segoe UI", 10, QFont.Medium))
        self.setCursor(Qt.PointingHandCursor)
        
        if primary:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4A90E2, stop:1 #357ABD);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #5BA0F2, stop:1 #4A90E2);
                    transform: translateY(-1px);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #357ABD, stop:1 #2E6BA8);
                }
                QPushButton:disabled {
                    background: #CCCCCC;
                    color: #666666;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: #F8F9FA;
                    color: #495057;
                    border: 2px solid #E9ECEF;
                    border-radius: 8px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background: #E9ECEF;
                    border-color: #ADB5BD;
                }
                QPushButton:pressed {
                    background: #DEE2E6;
                }
                QPushButton:disabled {
                    background: #F8F9FA;
                    color: #ADB5BD;
                    border-color: #DEE2E6;
                }
            """)

class ModernProgressBar(QProgressBar):
    """Современный прогресс-бар с анимацией"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(8)
        self.setTextVisible(False)
        self.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #E9ECEF;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4A90E2, stop:1 #7B68EE);
                border-radius: 4px;
            }
        """)

class ProcessingThread(QThread):
    """Поток для обработки файлов без блокировки GUI"""
    
    progress_updated = pyqtSignal(int)  # Прогресс архивов
    file_progress_updated = pyqtSignal(int, int, int)  # Прогресс файлов (current, total, archive_index)
    file_processed = pyqtSignal(str, bool, str)
    archive_started = pyqtSignal(str, int)  # Название архива и количество файлов
    archive_completed = pyqtSignal(str, dict)
    processing_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, zip_files, input_dir, output_dir, max_workers=None):
        super().__init__()
        self.zip_files = zip_files
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.is_cancelled = False
        
    def run(self):
        """Основной метод обработки"""
        try:
            total_stats = {
                'archives_processed': 0,
                'total_files': 0,
                'total_successful': 0,
                'total_failed': 0,
                'total_time': 0,
                'start_time': time.time()
            }
            
            for i, zip_file in enumerate(self.zip_files):
                if self.is_cancelled:
                    break
                    
                zip_path = os.path.join(self.input_dir, zip_file)
                
                # Сначала получаем информацию об архиве для прогресса файлов
                try:
                    import zipfile
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        eps_files = [f for f in zf.namelist() if f.lower().endswith('.eps')]
                        file_count = len(eps_files)
                        self.archive_started.emit(zip_file, file_count)
                        
                        # Сбрасываем прогресс файлов для нового архива
                        self.file_progress_updated.emit(0, file_count, i)
                        
                except Exception:
                    file_count = 0
                    self.archive_started.emit(zip_file, 0)
                
                # Обрабатываем архив с отслеживанием прогресса файлов
                stats = self.process_zip_with_progress(zip_path, self.output_dir, i, file_count)
                
                # Обновляем статистику
                total_stats['archives_processed'] += 1
                total_stats['total_files'] += stats['total_files']
                total_stats['total_successful'] += stats['successful']
                total_stats['total_failed'] += stats['failed']
                total_stats['total_time'] += stats['processing_time']
                
                # Сигналы о прогрессе архивов
                progress = int((i + 1) / len(self.zip_files) * 100)
                self.progress_updated.emit(progress)
                self.archive_completed.emit(zip_file, stats)
                
                # Очищаем кэш каждые 5 архивов
                if (i + 1) % 5 == 0:
                    clear_cache()
            
            total_stats['end_time'] = time.time()
            total_stats['total_processing_time'] = total_stats['end_time'] - total_stats['start_time']
            
            # Финальная очистка
            clear_cache()
            
            self.processing_finished.emit(total_stats)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def process_zip_with_progress(self, zip_path, output_dir, archive_index, total_files):
        """Обработка архива с отслеживанием прогресса файлов"""
        # Используем модифицированную версию process_zip_archive
        import zipfile
        import os
        
        archive_name = os.path.splitext(os.path.basename(zip_path))[0]
        results = []
        stats = {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'start_time': time.time()
        }
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                eps_files = [f for f in zip_file.namelist() if f.lower().endswith('.eps')]
                stats['total_files'] = len(eps_files)
                
                if not eps_files:
                    return stats
                
                # Определяем количество потоков
                max_workers = self.max_workers
                if max_workers is None:
                    max_workers = min(len(eps_files), os.cpu_count() or 1)
                
                # Подготавливаем аргументы для многопоточной обработки
                file_args = [(zip_path, eps_file) for eps_file in eps_files]
                
                # Обрабатываем файлы параллельно с отслеживанием прогресса
                from concurrent.futures import ThreadPoolExecutor
                from main import _process_single_eps_file
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Отправляем все задачи
                    future_to_file = {executor.submit(_process_single_eps_file, args): i 
                                    for i, args in enumerate(file_args)}
                    
                    completed = 0
                    for future in future_to_file:
                        if self.is_cancelled:
                            break
                            
                        try:
                            eps_file, code, success, error_msg = future.result()
                            
                            if success:
                                results.append(f"{eps_file}: {code}")
                                stats['successful'] += 1
                            else:
                                results.append(f"{eps_file}: {error_msg}")
                                stats['failed'] += 1
                            
                            # Обновляем прогресс файлов
                            completed += 1
                            self.file_progress_updated.emit(completed, len(eps_files), archive_index)
                            
                        except Exception as e:
                            stats['failed'] += 1
                            completed += 1
                            self.file_progress_updated.emit(completed, len(eps_files), archive_index)
        
        except Exception as e:
            stats['failed'] += 1
        
        stats['end_time'] = time.time()
        stats['processing_time'] = stats['end_time'] - stats['start_time']
        
        # Сохраняем результаты
        output_file = os.path.join(output_dir, f"{archive_name}_results.txt")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for result in results:
                    if ": " in result and not result.startswith("Ошибка"):
                        code = result.split(": ", 1)[1]
                        f.write(code + "\n")
        except Exception:
            pass
        
        return stats
    
    def cancel(self):
        """Отменить обработку"""
        self.is_cancelled = True

class EpsToTxtMainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings('EpsToTxt2', 'Settings')
        self.processing_thread = None
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        self.setWindowTitle("EpsToTxt2 - Обработка DataMatrix кодов")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной макет
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        self.create_header(main_layout)
        
        # Основное содержимое
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(content_splitter)
        
        # Левая панель - настройки
        self.create_settings_panel(content_splitter)
        
        # Правая панель - результаты
        self.create_results_panel(content_splitter)
        
        # Нижняя панель - прогресс и статус
        self.create_status_panel(main_layout)
        
        # Меню и статус бар
        self.create_menu_bar()
        self.create_status_bar()
        
        # Применяем стили
        self.apply_styles()
        
    def create_header(self, layout):
        """Создание заголовка приложения"""
        header_frame = QFrame()
        header_frame.setMaximumHeight(80)
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 12px;
                margin: 0px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        # Иконка и заголовок
        title_label = QLabel("EpsToTxt2")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title_label.setStyleSheet("color: white; background: transparent;")
        
        subtitle_label = QLabel("Обработка DataMatrix кодов из системы Честный Знак")
        subtitle_label.setFont(QFont("Segoe UI", 12))
        subtitle_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        
        title_layout = QVBoxLayout()
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        title_layout.setSpacing(0)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
    def create_settings_panel(self, splitter):
        """Создание панели настроек"""
        settings_widget = QWidget()
        settings_widget.setMaximumWidth(400)
        settings_layout = QVBoxLayout(settings_widget)
        
        # Группа выбора файлов
        file_group = QGroupBox("Выбор файлов")
        file_group.setFont(QFont("Segoe UI", 11, QFont.Medium))
        file_layout = QVBoxLayout(file_group)
        
        # Входная папка
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Входная папка:"))
        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("Выберите папку с ZIP файлами")
        self.input_path_edit.setText(str(Path.cwd() / "In"))
        input_layout.addWidget(self.input_path_edit)
        
        self.browse_input_btn = ModernButton("Обзор...")
        self.browse_input_btn.clicked.connect(self.browse_input_folder)
        input_layout.addWidget(self.browse_input_btn)
        
        file_layout.addLayout(input_layout)
        
        # Выходная папка
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Выходная папка:"))
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Выберите папку для результатов")
        self.output_path_edit.setText(str(Path.cwd() / "Out"))
        output_layout.addWidget(self.output_path_edit)
        
        self.browse_output_btn = ModernButton("Обзор...")
        self.browse_output_btn.clicked.connect(self.browse_output_folder)
        output_layout.addWidget(self.browse_output_btn)
        
        file_layout.addLayout(output_layout)
        
        settings_layout.addWidget(file_group)
        
        # Группа настроек обработки
        processing_group = QGroupBox("Настройки обработки")
        processing_group.setFont(QFont("Segoe UI", 11, QFont.Medium))
        processing_layout = QGridLayout(processing_group)
        
        # Количество потоков
        processing_layout.addWidget(QLabel("Количество потоков:"), 0, 0)
        self.threads_spinbox = QSpinBox()
        self.threads_spinbox.setMinimum(1)
        self.threads_spinbox.setMaximum(os.cpu_count() or 1)
        self.threads_spinbox.setValue(os.cpu_count() or 1)
        processing_layout.addWidget(self.threads_spinbox, 0, 1)
        
        # Автоочистка кэша
        self.auto_clear_cache = QCheckBox("Автоматическая очистка кэша")
        self.auto_clear_cache.setChecked(True)
        processing_layout.addWidget(self.auto_clear_cache, 1, 0, 1, 2)
        
        settings_layout.addWidget(processing_group)
        
        # Кнопки управления
        buttons_layout = QVBoxLayout()
        
        self.start_btn = ModernButton("🚀 Начать обработку", primary=True)
        self.start_btn.clicked.connect(self.start_processing)
        buttons_layout.addWidget(self.start_btn)
        
        self.stop_btn = ModernButton("⏹ Остановить обработку")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        buttons_layout.addWidget(self.stop_btn)
        
        self.clear_cache_btn = ModernButton("🗑 Очистить кэш")
        self.clear_cache_btn.clicked.connect(self.clear_cache_manually)
        buttons_layout.addWidget(self.clear_cache_btn)
        
        settings_layout.addLayout(buttons_layout)
        settings_layout.addStretch()
        
        splitter.addWidget(settings_widget)
        
    def create_results_panel(self, splitter):
        """Создание панели результатов"""
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        # Табы для разных видов информации
        self.tabs = QTabWidget()
        
        # Таб логов
        self.log_text = QTextEdit()
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setReadOnly(True)
        self.tabs.addTab(self.log_text, "📋 Логи обработки")
        
        # Таб статистики
        self.stats_table = QTableWidget()
        self.setup_stats_table()
        self.tabs.addTab(self.stats_table, "📊 Статистика")
        
        # Таб настроек
        settings_tab = QWidget()
        self.tabs.addTab(settings_tab, "⚙️ Дополнительные настройки")
        
        results_layout.addWidget(self.tabs)
        splitter.addWidget(results_widget)
        
    def setup_stats_table(self):
        """Настройка таблицы статистики"""
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Параметр", "Значение"])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.stats_table.setAlternatingRowColors(True)
        
        # Добавляем начальные строки
        stats_items = [
            ("Обработано архивов", "0"),
            ("Всего файлов", "0"),
            ("Успешно декодировано", "0"),
            ("Ошибок", "0"),
            ("Время обработки", "0 сек"),
            ("Среднее время на файл", "0 сек"),
            ("Процент успеха", "0%"),
            ("Использовано потоков", str(os.cpu_count() or 1))
        ]
        
        self.stats_table.setRowCount(len(stats_items))
        for i, (param, value) in enumerate(stats_items):
            self.stats_table.setItem(i, 0, QTableWidgetItem(param))
            self.stats_table.setItem(i, 1, QTableWidgetItem(value))
        
    def create_status_panel(self, layout):
        """Создание панели статуса и прогресса"""
        status_frame = QFrame()
        status_frame.setMaximumHeight(140)
        status_layout = QVBoxLayout(status_frame)
        
        # Прогресс архивов
        archives_layout = QHBoxLayout()
        archives_layout.addWidget(QLabel("📦 Архивы:"))
        
        self.progress_bar = ModernProgressBar()
        self.progress_bar.setValue(0)
        archives_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("0 из 0")
        self.progress_label.setMinimumWidth(80)
        self.progress_label.setStyleSheet("font-weight: bold; color: #4A90E2;")
        archives_layout.addWidget(self.progress_label)
        
        status_layout.addLayout(archives_layout)
        
        # Прогресс файлов в текущем архиве
        files_layout = QHBoxLayout()
        files_layout.addWidget(QLabel("📄 Файлы:"))
        
        self.file_progress_bar = ModernProgressBar()
        self.file_progress_bar.setValue(0)
        # Устанавливаем другой цвет для прогресса файлов
        self.file_progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #E9ECEF;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7B68EE, stop:1 #9370DB);
                border-radius: 4px;
            }
        """)
        files_layout.addWidget(self.file_progress_bar)
        
        self.file_progress_label = QLabel("0 из 0")
        self.file_progress_label.setMinimumWidth(80)
        self.file_progress_label.setStyleSheet("font-weight: bold; color: #7B68EE;")
        files_layout.addWidget(self.file_progress_label)
        
        status_layout.addLayout(files_layout)
        
        # Текущий статус
        self.status_label = QLabel("Готов к обработке")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #495057; padding: 5px;")
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(status_frame)
        
    def create_menu_bar(self):
        """Создание меню"""
        menubar = self.menuBar()
        
        # Файл
        file_menu = menubar.addMenu("Файл")
        
        open_action = QAction("Открыть папку входных файлов", self)
        open_action.triggered.connect(self.browse_input_folder)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Инструменты
        tools_menu = menubar.addMenu("Инструменты")
        
        clear_cache_action = QAction("Очистить кэш", self)
        clear_cache_action.triggered.connect(self.clear_cache_manually)
        tools_menu.addAction(clear_cache_action)
        
        # Справка
        help_menu = menubar.addMenu("Справка")
        
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_status_bar(self):
        """Создание строки состояния"""
        self.statusBar().showMessage("Готов к работе")
        
    def apply_styles(self):
        """Применение глобальных стилей"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8F9FA;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #E9ECEF;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #F8F9FA;
            }
            QLineEdit {
                border: 2px solid #E9ECEF;
                border-radius: 6px;
                padding: 8px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border-color: #4A90E2;
            }
            QSpinBox {
                border: 2px solid #E9ECEF;
                border-radius: 6px;
                padding: 5px;
                font-size: 10pt;
            }
            QTabWidget::pane {
                border: 2px solid #E9ECEF;
                border-radius: 8px;
                background: white;
            }
            QTabBar::tab {
                background: #F8F9FA;
                border: 2px solid #E9ECEF;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: white;
                border-color: #4A90E2;
            }
            QTextEdit {
                border: none;
                background: white;
                font-family: 'Consolas', monospace;
            }
            QTableWidget {
                border: none;
                background: white;
                gridline-color: #E9ECEF;
                selection-background-color: #4A90E2;
            }
            QHeaderView::section {
                background: #F8F9FA;
                border: 1px solid #E9ECEF;
                padding: 8px;
                font-weight: bold;
            }
        """)
    
    def browse_input_folder(self):
        """Выбор входной папки"""
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку с ZIP файлами", 
            self.input_path_edit.text()
        )
        if folder:
            self.input_path_edit.setText(folder)
    
    def browse_output_folder(self):
        """Выбор выходной папки"""
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку для результатов", 
            self.output_path_edit.text()
        )
        if folder:
            self.output_path_edit.setText(folder)
    
    def start_processing(self):
        """Начать обработку файлов"""
        input_dir = self.input_path_edit.text()
        output_dir = self.output_path_edit.text()
        
        if not os.path.exists(input_dir):
            QMessageBox.warning(self, "Ошибка", "Входная папка не существует!")
            return
        
        # Создаем выходную папку если не существует
        os.makedirs(output_dir, exist_ok=True)
        
        # Находим ZIP файлы
        zip_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.zip')]
        
        if not zip_files:
            QMessageBox.information(self, "Информация", "В выбранной папке нет ZIP файлов!")
            return
        
        # Настраиваем интерфейс для обработки
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.file_progress_bar.setValue(0)
        self.progress_label.setText(f"0 из {len(zip_files)}")
        self.file_progress_label.setText("0 из 0")
        self.log_text.clear()
        
        # Сохраняем общее количество архивов для отображения
        self.total_archives = len(zip_files)
        self.current_archive = 0
        
        # Добавляем информацию в лог
        self.add_log(f"🚀 Начинаем обработку {len(zip_files)} архивов")
        self.add_log(f"📁 Входная папка: {input_dir}")
        self.add_log(f"📁 Выходная папка: {output_dir}")
        self.add_log(f"🔧 Потоков: {self.threads_spinbox.value()}")
        self.add_log("-" * 60)
        
        # Запускаем поток обработки
        self.processing_thread = ProcessingThread(
            zip_files, input_dir, output_dir, self.threads_spinbox.value()
        )
        
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.file_progress_updated.connect(self.update_file_progress)
        self.processing_thread.archive_started.connect(self.archive_started)
        self.processing_thread.archive_completed.connect(self.archive_completed)
        self.processing_thread.processing_finished.connect(self.processing_finished)
        self.processing_thread.error_occurred.connect(self.processing_error)
        
        self.processing_thread.start()
        
        self.status_label.setText("Обработка файлов...")
        self.statusBar().showMessage("Обработка в процессе...")
    
    def stop_processing(self):
        """Остановить обработку"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.cancel()
            self.processing_thread.wait(5000)  # Ждем 5 секунд
            
            self.add_log("⏹ Обработка остановлена пользователем")
            self.status_label.setText("Обработка остановлена")
            self.statusBar().showMessage("Обработка остановлена")
            
            # Сбрасываем прогресс-бары
            self.progress_label.setText("Остановлено")
            self.file_progress_label.setText("Остановлено")
            
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def clear_cache_manually(self):
        """Очистить кэш вручную"""
        clear_cache()
        self.add_log("🗑 Кэш очищен")
        QMessageBox.information(self, "Информация", "Кэш успешно очищен!")
    
    def update_progress(self, value):
        """Обновление прогресса архивов"""
        self.progress_bar.setValue(value)
        # Вычисляем текущий архив из процентов
        current = int(value * self.total_archives / 100)
        self.progress_label.setText(f"{current} из {self.total_archives}")
    
    def update_file_progress(self, current, total, archive_index):
        """Обновление прогресса файлов в текущем архиве"""
        if total > 0:
            percentage = int(current * 100 / total)
            self.file_progress_bar.setValue(percentage)
        else:
            self.file_progress_bar.setValue(0)
        
        self.file_progress_label.setText(f"{current} из {total}")
    
    def archive_started(self, archive_name, file_count):
        """Начало обработки нового архива"""
        self.add_log(f"📦 Начинаем архив: {archive_name} ({file_count} файлов)")
        self.file_progress_bar.setValue(0)
        self.file_progress_label.setText(f"0 из {file_count}")
        self.status_label.setText(f"Обрабатывается: {archive_name}")
    
    def archive_completed(self, archive_name, stats):
        """Завершение обработки архива"""
        success_rate = (stats['successful'] / max(stats['total_files'], 1)) * 100
        self.add_log(f"✅ {archive_name}: {stats['successful']}/{stats['total_files']} "
                    f"({success_rate:.1f}%) за {stats['processing_time']:.2f}с")
    
    def processing_finished(self, total_stats):
        """Завершение всей обработки"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        # Завершаем прогресс-бары
        self.progress_bar.setValue(100)
        self.file_progress_bar.setValue(100)
        self.progress_label.setText(f"{total_stats['archives_processed']} из {self.total_archives}")
        self.file_progress_label.setText("Завершено")
        
        # Обновляем статистику
        self.update_stats_table(total_stats)
        
        # Добавляем итоговую информацию в лог
        self.add_log("=" * 60)
        self.add_log("🎉 ОБРАБОТКА ЗАВЕРШЕНА!")
        self.add_log(f"📊 Обработано архивов: {total_stats['archives_processed']}")
        self.add_log(f"📄 Всего файлов: {total_stats['total_files']}")
        self.add_log(f"✅ Успешно: {total_stats['total_successful']}")
        self.add_log(f"❌ Ошибок: {total_stats['total_failed']}")
        self.add_log(f"⏱ Время: {total_stats['total_processing_time']:.2f} сек")
        
        success_rate = (total_stats['total_successful'] / max(total_stats['total_files'], 1)) * 100
        self.add_log(f"📈 Успешность: {success_rate:.1f}%")
        
        self.status_label.setText("Обработка завершена")
        self.statusBar().showMessage("Готов к работе")
        
        # Показываем уведомление
        QMessageBox.information(self, "Готово!", 
                               f"Обработка завершена!\n\n"
                               f"Архивов: {total_stats['archives_processed']}\n"
                               f"Файлов: {total_stats['total_files']}\n"
                               f"Успешно: {total_stats['total_successful']}\n"
                               f"Время: {total_stats['total_processing_time']:.1f} сек")
    
    def processing_error(self, error_message):
        """Обработка ошибки"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.add_log(f"❌ ОШИБКА: {error_message}")
        self.status_label.setText("Ошибка обработки")
        self.statusBar().showMessage("Произошла ошибка")
        
        QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n\n{error_message}")
    
    def add_log(self, message):
        """Добавление сообщения в лог"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)
        
        # Автопрокрутка к концу
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_stats_table(self, stats):
        """Обновление таблицы статистики"""
        avg_time = stats['total_time'] / max(stats['total_files'], 1)
        success_rate = (stats['total_successful'] / max(stats['total_files'], 1)) * 100
        
        stats_data = [
            ("Обработано архивов", str(stats['archives_processed'])),
            ("Всего файлов", str(stats['total_files'])),
            ("Успешно декодировано", str(stats['total_successful'])),
            ("Ошибок", str(stats['total_failed'])),
            ("Время обработки", f"{stats['total_processing_time']:.2f} сек"),
            ("Среднее время на файл", f"{avg_time:.2f} сек"),
            ("Процент успеха", f"{success_rate:.1f}%"),
            ("Использовано потоков", str(self.threads_spinbox.value()))
        ]
        
        for i, (param, value) in enumerate(stats_data):
            self.stats_table.setItem(i, 1, QTableWidgetItem(value))
    
    def show_about(self):
        """Показать диалог 'О программе'"""
        about_text = """
        <h2>EpsToTxt2</h2>
        <p><b>Версия:</b> 2.0 GUI</p>
        <p><b>Автор:</b> Peltik</p>
        <p><b>Описание:</b> Программа для обработки DataMatrix кодов из системы "Честный Знак"</p>
        
        <h3>Особенности:</h3>
        <ul>
        <li>🚀 Многопоточная обработка</li>
        <li>💾 Кэширование результатов</li>
        <li>📊 Детальная статистика</li>
        <li>🎨 Современный интерфейс</li>
        <li>⚡ Оптимизированные алгоритмы</li>
        </ul>
        
        <p><small>Программа использует PyQt6, NumPy, PIL и pylibdmtx</small></p>
        """
        
        QMessageBox.about(self, "О программе EpsToTxt2", about_text)
    
    def load_settings(self):
        """Загрузка настроек"""
        input_path = self.settings.value("input_path", str(Path.cwd() / "In"))
        output_path = self.settings.value("output_path", str(Path.cwd() / "Out"))
        threads = self.settings.value("threads", os.cpu_count() or 1, type=int)
        auto_clear = self.settings.value("auto_clear_cache", True, type=bool)
        
        self.input_path_edit.setText(input_path)
        self.output_path_edit.setText(output_path)
        self.threads_spinbox.setValue(threads)
        self.auto_clear_cache.setChecked(auto_clear)
    
    def save_settings(self):
        """Сохранение настроек"""
        self.settings.setValue("input_path", self.input_path_edit.text())
        self.settings.setValue("output_path", self.output_path_edit.text())
        self.settings.setValue("threads", self.threads_spinbox.value())
        self.settings.setValue("auto_clear_cache", self.auto_clear_cache.isChecked())
    
    def closeEvent(self, event):
        """Обработка закрытия приложения"""
        if self.processing_thread and self.processing_thread.isRunning():
            reply = QMessageBox.question(
                self, "Подтверждение", 
                "Обработка еще не завершена. Вы уверены, что хотите выйти?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.processing_thread.cancel()
                self.processing_thread.wait(3000)
                self.save_settings()
                event.accept()
            else:
                event.ignore()
        else:
            self.save_settings()
            event.accept()

def main():
    """Главная функция запуска GUI"""
    app = QApplication(sys.argv)
    
    # Настройка приложения
    app.setApplicationName("EpsToTxt2")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Peltik")
    
    # Применяем современную тему
    app.setStyle('Fusion')
    
    # Создаем и показываем главное окно
    window = EpsToTxtMainWindow()
    window.show()
    
    # Запускаем приложение
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
