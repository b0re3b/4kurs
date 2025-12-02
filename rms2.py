"""
Медіаплеєр з сучасним інтерфейсом
===================================

Опис:
    Простий та зручний медіаплеєр з підтримкою відео та аудіо файлів,
    а також потокового мультимедіа через URL.

Основні можливості:
    - Відтворення локальних медіафайлів (MP3, MP4, AVI, MKV тощо)
    - Підтримка потокового мультимедіа (HTTP, HTTPS, RTSP)
    - Сучасний темний інтерфейс
    - Контроль відтворення (пауза, стоп, перемотка)
    - Регулювання гучності
    - Повзунок прогресу відтворення

Вимоги:
    - Python 3.6+
    - PyQt5
    - PyQt5.QtMultimedia

Використання:
    python media_player.py

Автор: [Ваше ім'я]
Версія: 1.0
Дата: 2025
"""

import sys
import os
import logging
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSlider, QLabel,
                             QFileDialog, QStyle, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtGui import QIcon, QPalette, QColor, QFont


# Налаштування логування
def setup_logging():
    """
    Налаштовує систему логування для запису подій роботи програми.

    Створює лог-файли у директорії 'logs' з поточною датою та часом.
    Формат: media_player_YYYYMMDD_HHMMSS.log
    """
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"media_player_{timestamp}.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    logging.info("=" * 60)
    logging.info("Медіаплеєр запущено")
    logging.info("=" * 60)


class ModernButton(QPushButton):
    """
    Кастомна кнопка з сучасним дизайном.

    Наслідує QPushButton та додає стильні ефекти hover і pressed.
    """

    def __init__(self, *args, **kwargs):
        """Ініціалізація кнопки з кастомними стилями."""
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 20px;
                padding: 10px;
                color: white;
                min-width: 40px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)


class MediaPlayer(QMainWindow):
    """
    Головний клас медіаплеєра.

    Attributes:
        player (QMediaPlayer): Об'єкт медіаплеєра PyQt5
        video_widget (QVideoWidget): Віджет для відображення відео
        is_dragging (bool): Флаг перетягування повзунка
        control_timer (QTimer): Таймер для автоприховування контролів
    """

    def __init__(self):
        """Ініціалізація головного вікна медіаплеєра."""
        super().__init__()
        logging.info("Ініціалізація медіаплеєра")

        self.setWindowTitle("Медіаплеєр")
        self.setGeometry(100, 100, 1000, 700)

        # Темна тема
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
        """)

        # Ініціалізація медіаплеєра
        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        logging.info("QMediaPlayer ініціалізовано")

        # Створення інтерфейсу
        self.create_ui()

        # Підключення сигналів
        self.player.stateChanged.connect(self.media_state_changed)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.error.connect(self.handle_error)
        logging.info("Сигнали підключено")

        # Флаги для відстеження стану
        self.is_dragging = False

        # Таймер для автоприховування контролів
        self.control_timer = QTimer()
        self.control_timer.timeout.connect(self.hide_controls)
        self.control_timer.setInterval(3000)

    def create_ui(self):
        """
        Створює користувацький інтерфейс програми.

        Включає:
        - Відео віджет
        - Контейнер з контролями
        - Кнопки управління
        - Повзунки (прогрес, гучність)
        - Мітки часу та гучності
        """
        logging.info("Створення інтерфейсу користувача")

        # Центральний віджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Головний layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        central_widget.setLayout(layout)

        # Відео віджет
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("""
            QVideoWidget {
                background-color: #000000;
            }
        """)
        self.player.setVideoOutput(self.video_widget)
        layout.addWidget(self.video_widget)

        # Контейнер для контролів з градієнтом
        self.control_container = QFrame()
        self.control_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 0, 0, 0),
                    stop:0.5 rgba(0, 0, 0, 150),
                    stop:1 rgba(0, 0, 0, 200)
                );
                border: none;
            }
        """)

        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(20, 20, 20, 20)
        control_layout.setSpacing(15)
        self.control_container.setLayout(control_layout)

        # Заголовок файлу
        self.title_label = QLabel("Відкрийте медіафайл для відтворення")
        self.title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                background: transparent;
            }
        """)
        control_layout.addWidget(self.title_label)

        # Повзунок позиції (кастомний дизайн)
        position_layout = QHBoxLayout()
        position_layout.setSpacing(10)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_position)
        self.position_slider.sliderPressed.connect(self.slider_pressed)
        self.position_slider.sliderReleased.connect(self.slider_released)
        self.position_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(255, 255, 255, 0.2);
                height: 4px;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #4a9eff;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #4a9eff;
            }
        """)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                background: transparent;
                min-width: 100px;
            }
        """)

        position_layout.addWidget(self.position_slider)
        position_layout.addWidget(self.time_label)
        control_layout.addLayout(position_layout)

        # Кнопки управління
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Ліва частина - файли
        left_buttons = QHBoxLayout()
        left_buttons.setSpacing(5)

        self.open_btn = ModernButton()
        self.open_btn.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.open_btn.setToolTip("Відкрити файл")
        self.open_btn.clicked.connect(self.open_file)

        self.url_btn = ModernButton("URL")
        self.url_btn.setStyleSheet(self.url_btn.styleSheet() + """
            QPushButton {
                font-weight: bold;
                font-size: 12px;
            }
        """)
        self.url_btn.setToolTip("Відкрити потокове медіа")
        self.url_btn.clicked.connect(self.open_url)

        left_buttons.addWidget(self.open_btn)
        left_buttons.addWidget(self.url_btn)

        # Центральна частина - відтворення
        center_buttons = QHBoxLayout()
        center_buttons.setSpacing(5)

        self.backward_btn = ModernButton()
        self.backward_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekBackward))
        self.backward_btn.setToolTip("Назад 10 сек")
        self.backward_btn.clicked.connect(self.backward)

        self.play_btn = ModernButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_btn.setToolTip("Відтворити")
        self.play_btn.clicked.connect(self.play_pause)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(74, 158, 255, 0.8);
                border: none;
                border-radius: 25px;
                padding: 10px;
                color: white;
                min-width: 50px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: rgba(74, 158, 255, 1);
            }
            QPushButton:pressed {
                background-color: rgba(60, 140, 230, 1);
            }
        """)

        self.stop_btn = ModernButton()
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_btn.setToolTip("Стоп")
        self.stop_btn.clicked.connect(self.stop)

        self.forward_btn = ModernButton()
        self.forward_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekForward))
        self.forward_btn.setToolTip("Вперед 10 сек")
        self.forward_btn.clicked.connect(self.forward)

        center_buttons.addWidget(self.backward_btn)
        center_buttons.addWidget(self.play_btn)
        center_buttons.addWidget(self.stop_btn)
        center_buttons.addWidget(self.forward_btn)

        # Права частина - гучність
        right_buttons = QHBoxLayout()
        right_buttons.setSpacing(10)

        volume_icon = QLabel("🔊")
        volume_icon.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                background: transparent;
            }
        """)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(120)
        self.volume_slider.setToolTip("Гучність")
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(255, 255, 255, 0.2);
                height: 4px;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: white;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """)

        self.volume_label = QLabel("50%")
        self.volume_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                background: transparent;
                min-width: 35px;
            }
        """)

        right_buttons.addWidget(volume_icon)
        right_buttons.addWidget(self.volume_slider)
        right_buttons.addWidget(self.volume_label)

        # Додавання всіх груп кнопок
        button_layout.addLayout(left_buttons)
        button_layout.addStretch()
        button_layout.addLayout(center_buttons)
        button_layout.addStretch()
        button_layout.addLayout(right_buttons)

        control_layout.addLayout(button_layout)
        layout.addWidget(self.control_container)

        # Встановлення початкової гучності
        self.set_volume(50)
        logging.info("Інтерфейс створено успішно")

    def open_file(self):
        """
        Відкриває діалог вибору локального медіафайлу.

        Підтримувані формати:
        - Аудіо: MP3, WAV, OGG, M4A, AAC
        - Відео: MP4, AVI, MKV, FLV, MOV, WMV, WEBM
        """
        logging.info("Відкриття діалогу вибору файлу")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Відкрити медіафайл",
            "",
            "Медіафайли (*.mp3 *.mp4 *.avi *.mkv *.flv *.mov *.wmv *.wav *.ogg *.webm *.m4a *.aac);;Всі файли (*.*)"
        )

        if file_path:
            logging.info(f"Вибрано файл: {file_path}")
            if not os.path.exists(file_path):
                logging.error(f"Файл не знайдено: {file_path}")
                QMessageBox.warning(self, "Помилка", "Файл не знайдено!")
                return
            self.load_media(file_path)
            # Оновити заголовок
            file_name = os.path.basename(file_path)
            self.title_label.setText(file_name)
            logging.info(f"Завантажено файл: {file_name}")
        else:
            logging.info("Вибір файлу скасовано")

    def open_url(self):
        """
        Відкриває діалог введення URL для потокового медіа.

        Підтримувані протоколи: HTTP, HTTPS, RTSP, MMS
        """
        from PyQt5.QtWidgets import QInputDialog

        logging.info("Відкриття діалогу введення URL")

        url, ok = QInputDialog.getText(
            self,
            "Відкрити потокове медіа",
            "Введіть URL (наприклад, http://example.com/stream.mp3):"
        )

        if ok and url:
            logging.info(f"Введено URL: {url}")
            self.load_media(url)
            self.title_label.setText("Потокове медіа")
        else:
            logging.info("Введення URL скасовано")

    def load_media(self, path):
        """
        Завантажує медіафайл або потік.

        Args:
            path (str): Шлях до локального файлу або URL

        Raises:
            Exception: При помилці завантаження медіа
        """
        try:
            logging.info(f"Завантаження медіа: {path}")

            if path.startswith(('http://', 'https://', 'rtsp://', 'mms://')):
                url = QUrl(path)
                logging.info(f"Розпізнано як URL: {path}")
            else:
                url = QUrl.fromLocalFile(path)
                logging.info(f"Розпізнано як локальний файл: {path}")

            media = QMediaContent(url)
            self.player.setMedia(media)
            self.player.play()
            logging.info("Медіа завантажено та розпочато відтворення")

        except Exception as e:
            logging.error(f"Помилка завантаження медіа: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити медіа:\n{str(e)}")

    def play_pause(self):
        """
        Перемикає між відтворенням та паузою.
        """
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            logging.info("Відтворення призупинено")
        else:
            self.player.play()
            logging.info("Відтворення відновлено")

    def stop(self):
        """
        Зупиняє відтворення та скидає позицію до початку.
        """
        self.player.stop()
        self.position_slider.setValue(0)
        self.time_label.setText("00:00 / 00:00")
        logging.info("Відтворення зупинено")

    def forward(self):
        """
        Перемотує вперед на 10 секунд.
        """
        position = self.player.position()
        duration = self.player.duration()
        new_position = min(position + 10000, duration)
        self.player.setPosition(new_position)
        logging.info(f"Перемотка вперед: {position}ms -> {new_position}ms")

    def backward(self):
        """
        Перемотує назад на 10 секунд.
        """
        position = self.player.position()
        new_position = max(0, position - 10000)
        self.player.setPosition(new_position)
        logging.info(f"Перемотка назад: {position}ms -> {new_position}ms")

    def slider_pressed(self):
        """
        Обробляє натискання на повзунок позиції.
        """
        self.is_dragging = True
        logging.debug("Початок перетягування повзунка")

    def slider_released(self):
        """
        Обробляє відпускання повзунка позиції.
        """
        self.is_dragging = False
        logging.debug("Завершення перетягування повзунка")

    def set_position(self, position):
        """
        Встановлює позицію відтворення.

        Args:
            position (int): Позиція в мілісекундах
        """
        self.player.setPosition(position)
        logging.debug(f"Встановлено позицію: {position}ms")

    def set_volume(self, volume):
        """
        Встановлює рівень гучності.

        Args:
            volume (int): Рівень гучності (0-100)
        """
        self.player.setVolume(volume)
        self.volume_label.setText(f"{volume}%")
        logging.info(f"Гучність змінено на: {volume}%")

    def media_state_changed(self, state):
        """
        Обробляє зміну стану медіаплеєра.

        Args:
            state (QMediaPlayer.State): Новий стан плеєра
        """
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.play_btn.setToolTip("Пауза")
            logging.info("Стан: Відтворення")
        elif state == QMediaPlayer.PausedState:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.play_btn.setToolTip("Відтворити")
            logging.info("Стан: Пауза")
        elif state == QMediaPlayer.StoppedState:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.play_btn.setToolTip("Відтворити")
            logging.info("Стан: Зупинено")

    def position_changed(self, position):
        """
        Обробляє зміну позиції відтворення.

        Args:
            position (int): Поточна позиція в мілісекундах
        """
        if not self.is_dragging:
            self.position_slider.setValue(position)

        # Оновлення часу
        duration = self.player.duration()
        if duration > 0:
            current_str = self.format_time(position)
            total_str = self.format_time(duration)
            self.time_label.setText(f"{current_str} / {total_str}")

    def duration_changed(self, duration):
        """
        Обробляє зміну тривалості медіа.

        Args:
            duration (int): Тривалість в мілісекундах
        """
        self.position_slider.setRange(0, duration)
        logging.info(f"Тривалість медіа: {self.format_time(duration)}")

    def handle_error(self):
        """
        Обробляє помилки відтворення медіа.
        """
        error = self.player.errorString()
        if error:
            logging.error(f"Помилка відтворення: {error}")
            QMessageBox.critical(self, "Помилка відтворення", error)

    def format_time(self, milliseconds):
        """
        Форматує час з мілісекунд у рядок.

        Args:
            milliseconds (int): Час в мілісекундах

        Returns:
            str: Відформатований час (MM:SS або HH:MM:SS)
        """
        if milliseconds < 0:
            return "00:00"

        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        hours = minutes // 60
        minutes = minutes % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def hide_controls(self):
        """
        Приховує контрольну панель (заготовка для майбутнього функціоналу).
        """
        # Функціонал автоприховування можна додати пізніше
        pass

    def closeEvent(self, event):
        """
        Обробляє закриття вікна програми.

        Args:
            event (QCloseEvent): Подія закриття
        """
        logging.info("Закриття медіаплеєра")
        self.player.stop()
        logging.info("Плеєр зупинено")
        logging.info("=" * 60)
        logging.info("Медіаплеєр завершив роботу")
        logging.info("=" * 60)
        event.accept()


if __name__ == "__main__":
    # Налаштування логування
    setup_logging()

    try:
        # Створення застосунку
        app = QApplication(sys.argv)
        logging.info("QApplication створено")

        # Створення та відображення медіаплеєра
        player = MediaPlayer()
        player.show()
        logging.info("Головне вікно відображено")

        # Запуск циклу подій
        sys.exit(app.exec_())

    except Exception as e:
        logging.critical(f"Критична помилка: {str(e)}", exc_info=True)
        sys.exit(1)