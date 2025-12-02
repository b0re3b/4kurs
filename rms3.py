import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from scipy.fftpack import dct, idct
import requests
from io import BytesIO
import logging
from datetime import datetime
import time

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'compression_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ImageCompressor:
    """
    Клас для стиснення зображень за допомогою DCT та DWT методів.

    Attributes:
        original (np.ndarray): Оригінальне зображення у відтінках сірого
        height (int): Висота зображення
        width (int): Ширина зображення

    Methods:
        compress_dct(quality): Стиснення методом DCT (Discrete Cosine Transform)
        compress_dwt(quality): Стиснення методом DWT (Discrete Wavelet Transform)
        compare_compression(quality): Порівняння обох методів


    """

    def __init__(self, url):
        """
        Ініціалізація компресора зображень.

        Args:
            url (str): URL зображення для завантаження


        """
        logger.info("=" * 70)
        logger.info("Початок роботи ImageCompressor")
        logger.info(f"URL: {url}")

        start_time = time.time()

        try:
            logger.info("Завантаження зображення з інтернету...")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            logger.info(f"HTTP статус: {response.status_code}")
            logger.info(f"Розмір завантаженого файлу: {len(response.content) / 1024:.2f} KB")

            image = Image.open(BytesIO(response.content)).convert('L')

            self.original = np.array(image, dtype=float)
            self.height, self.width = self.original.shape

            load_time = time.time() - start_time
            logger.info(f"✓ Зображення завантажено успішно за {load_time:.2f} сек")
            logger.info(f"Розміри: {self.width}x{self.height} пікселів")
            logger.info(f"Кількість пікселів: {self.width * self.height:,}")
            logger.info(f"Діапазон значень: [{self.original.min():.1f}, {self.original.max():.1f}]")

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Помилка при завантаженні з URL: {e}")
            raise Exception(f"Помилка при завантаженні з URL: {e}")
        except Exception as e:
            logger.error(f"✗ Помилка при завантаженні зображення: {e}")
            raise Exception(f"Помилка при завантаженні зображення: {e}")

    def calculate_psnr(self, original, compressed):
        """
        Розрахунок PSNR (Peak Signal-to-Noise Ratio).

        PSNR вимірює якість стиснення. Вищі значення = краща якість.
        Типові значення: 30-50 dB (добре), >50 dB (відмінно)

        Args:
            original (np.ndarray): Оригінальне зображення
            compressed (np.ndarray): Стиснене зображення

        Returns:
            float: Значення PSNR в децибелах
        """
        mse = np.mean((original - compressed) ** 2)
        if mse == 0:
            logger.warning("MSE = 0: ідентичні зображення")
            return float('inf')
        max_pixel = 255.0
        psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
        logger.debug(f"MSE: {mse:.4f}, PSNR: {psnr:.2f} dB")
        return psnr

    def dct2(self, block):
        """
        2D DCT (Discrete Cosine Transform) перетворення.

        Перетворює просторову область в частотну для стиснення.

        Args:
            block (np.ndarray): Блок зображення 8x8

        Returns:
            np.ndarray: DCT коефіцієнти
        """
        return dct(dct(block.T, norm='ortho').T, norm='ortho')

    def idct2(self, block):
        """
        Зворотнє 2D DCT перетворення.

        Відновлює зображення з частотної області.

        Args:
            block (np.ndarray): DCT коефіцієнти

        Returns:
            np.ndarray: Відновлений блок зображення
        """
        return idct(idct(block.T, norm='ortho').T, norm='ortho')

    def compress_dct(self, quality=50):
        """
        Стиснення зображення методом DCT (як у JPEG).

        Процес:
        1. Розділення на блоки 8x8
        2. DCT перетворення кожного блоку
        3. Квантування коефіцієнтів
        4. Зворотнє перетворення

        Args:
            quality (int): Якість стиснення (1-100)
                          1 = максимальне стиснення, низька якість
                          100 = мінімальне стиснення, висока якість

        Returns:
            np.ndarray: Стиснене зображення
        """
        logger.info("-" * 70)
        logger.info("DCT СТИСНЕННЯ")
        logger.info(f"Параметр якості: {quality}%")

        start_time = time.time()
        block_size = 8

        # Додавання padding
        pad_h = (block_size - self.height % block_size) % block_size
        pad_w = (block_size - self.width % block_size) % block_size
        padded = np.pad(self.original, ((0, pad_h), (0, pad_w)), mode='edge')

        logger.info(f"Розмір з padding: {padded.shape}")
        logger.info(f"Кількість блоків 8x8: {(padded.shape[0] // 8) * (padded.shape[1] // 8)}")

        compressed = np.zeros_like(padded)

        # Матриця квантування (стандарт JPEG)
        quant_matrix = np.array([
            [16, 11, 10, 16, 24, 40, 51, 61],
            [12, 12, 14, 19, 26, 58, 60, 55],
            [14, 13, 16, 24, 40, 57, 69, 56],
            [14, 17, 22, 29, 51, 87, 80, 62],
            [18, 22, 37, 56, 68, 109, 103, 77],
            [24, 35, 55, 64, 81, 104, 113, 92],
            [49, 64, 78, 87, 103, 121, 120, 101],
            [72, 92, 95, 98, 112, 100, 103, 99]
        ])

        # Масштабування матриці квантування
        if quality < 50:
            scale = 50.0 / quality
        else:
            scale = 2.0 - quality / 50.0

        quant_matrix = np.floor(quant_matrix * scale + 0.5)
        quant_matrix[quant_matrix == 0] = 1

        logger.debug(f"Масштаб квантування: {scale:.3f}")
        logger.debug(f"Діапазон значень матриці квантування: [{quant_matrix.min()}, {quant_matrix.max()}]")

        # Обробка блоків
        total_blocks = (padded.shape[0] // block_size) * (padded.shape[1] // block_size)
        processed_blocks = 0

        for i in range(0, padded.shape[0], block_size):
            for j in range(0, padded.shape[1], block_size):
                block = padded[i:i + block_size, j:j + block_size]
                dct_block = self.dct2(block - 128)
                quantized = np.round(dct_block / quant_matrix)
                dequantized = quantized * quant_matrix
                reconstructed = self.idct2(dequantized) + 128
                compressed[i:i + block_size, j:j + block_size] = reconstructed

                processed_blocks += 1
                if processed_blocks % 1000 == 0:
                    logger.debug(f"Оброблено блоків: {processed_blocks}/{total_blocks}")

        compressed = compressed[:self.height, :self.width]
        compressed = np.clip(compressed, 0, 255)

        process_time = time.time() - start_time
        logger.info(f"✓ DCT стиснення завершено за {process_time:.2f} сек")
        logger.info(f"Швидкість: {total_blocks / process_time:.0f} блоків/сек")

        return compressed

    def haar_transform(self, data):
        """
        1D вейвлет перетворення Хаара.

        Розкладає сигнал на середні значення та різниці.

        Args:
            data (np.ndarray): Вхідний одновимірний масив

        Returns:
            np.ndarray: Коефіцієнти вейвлет-перетворення
        """
        data = data.copy()
        length = len(data)

        if length % 2 != 0:
            data = np.append(data, data[-1])
            length += 1

        output = np.zeros(length, dtype=float)
        avg = (data[::2] + data[1::2]) / np.sqrt(2)
        diff = (data[::2] - data[1::2]) / np.sqrt(2)

        output[:length // 2] = avg
        output[length // 2:] = diff
        return output

    def inverse_haar_transform(self, data):
        """
        Зворотнє 1D вейвлет перетворення Хаара.

        Args:
            data (np.ndarray): Коефіцієнти вейвлет-перетворення

        Returns:
            np.ndarray: Відновлений сигнал
        """
        length = len(data)
        output = np.zeros(length, dtype=float)
        half = length // 2

        for i in range(half):
            output[2 * i] = (data[i] + data[half + i]) / np.sqrt(2)
            output[2 * i + 1] = (data[i] - data[half + i]) / np.sqrt(2)
        return output

    def dwt2(self, image):
        """2D вейвлет перетворення (застосування до рядків та стовпців)."""
        rows = np.array([self.haar_transform(row) for row in image])
        cols = np.array([self.haar_transform(col) for col in rows.T]).T
        return cols

    def idwt2(self, coeffs):
        """Зворотнє 2D вейвлет перетворення."""
        cols = np.array([self.inverse_haar_transform(col) for col in coeffs.T]).T
        rows = np.array([self.inverse_haar_transform(row) for row in cols])
        return rows

    def compress_dwt(self, quality=50):
        """
        Стиснення зображення методом DWT (Discrete Wavelet Transform).

        Використовує вейвлет Хаара для багаторівневої декомпозиції.

        Процес:
        1. Багаторівнева вейвлет-декомпозиція
        2. Порогова фільтрація коефіцієнтів
        3. Зворотнє перетворення

        Args:
            quality (int): Відсоток коефіцієнтів для збереження (1-100)

        Returns:
            np.ndarray: Стиснене зображення
        """
        logger.info("-" * 70)
        logger.info("DWT СТИСНЕННЯ (Haar Wavelet)")
        logger.info(f"Якість (відсоток збережених коефіцієнтів): {quality}%")

        start_time = time.time()

        max_levels = int(np.log2(min(self.height, self.width)))
        levels = min(3, max_levels)

        logger.info(f"Максимальна кількість рівнів: {max_levels}")
        logger.info(f"Використовується рівнів: {levels}")

        target_size = 2 ** levels
        pad_h = (target_size - self.height % target_size) % target_size
        pad_w = (target_size - self.width % target_size) % target_size

        image = np.pad(self.original, ((0, pad_h), (0, pad_w)), mode='edge')
        logger.info(f"Розмір з padding: {image.shape}")

        # Пряме перетворення
        coeffs = image.copy()
        for level in range(levels):
            h = image.shape[0] // (2 ** level)
            w = image.shape[1] // (2 ** level)

            if h >= 2 and w >= 2:
                block = coeffs[:h, :w]
                coeffs[:h, :w] = self.dwt2(block)
                logger.debug(f"Рівень {level + 1}: розмір блоку {h}x{w}")

        # Порогова фільтрація
        keep_percent = quality
        threshold = np.percentile(np.abs(coeffs), 100 - keep_percent)
        logger.info(f"Поріг фільтрації: {threshold:.2f}")

        coeffs_before = np.count_nonzero(coeffs)
        coeffs_thresholded = coeffs.copy()
        coeffs_thresholded[np.abs(coeffs) < threshold] = 0
        coeffs_after = np.count_nonzero(coeffs_thresholded)

        logger.info(f"Коефіцієнтів до фільтрації: {coeffs_before:,}")
        logger.info(f"Коефіцієнтів після фільтрації: {coeffs_after:,}")
        logger.info(f"Відкинуто: {100 * (1 - coeffs_after / coeffs_before):.1f}%")

        # Зворотнє перетворення
        reconstructed = coeffs_thresholded.copy()
        for level in range(levels - 1, -1, -1):
            h = image.shape[0] // (2 ** level)
            w = image.shape[1] // (2 ** level)

            if h >= 2 and w >= 2:
                block = reconstructed[:h, :w]
                reconstructed[:h, :w] = self.idwt2(block)
                logger.debug(f"Відновлення рівня {level + 1}")

        reconstructed = reconstructed[:self.height, :self.width]
        reconstructed = np.clip(reconstructed, 0, 255)

        process_time = time.time() - start_time
        logger.info(f"✓ DWT стиснення завершено за {process_time:.2f} сек")

        return reconstructed

    def compare_compression(self, quality=50):
        """
        Порівняння методів стиснення DCT та DWT.

        Виконує стиснення обома методами, розраховує метрики якості
        та створює візуалізацію результатів.

        Args:
            quality (int): Рівень якості стиснення (1-100)

        Returns:
            tuple: (dct_compressed, dwt_compressed, dct_psnr, dwt_psnr)
        """
        logger.info("=" * 70)
        logger.info(f"ПОРІВНЯННЯ МЕТОДІВ СТИСНЕННЯ")
        logger.info(f"Якість: {quality}%")
        logger.info("=" * 70)

        total_start = time.time()

        # DCT стиснення
        dct_compressed = self.compress_dct(quality)
        dct_psnr = self.calculate_psnr(self.original, dct_compressed)
        logger.info(f"DCT PSNR: {dct_psnr:.2f} dB")

        # DWT стиснення
        dwt_compressed = self.compress_dwt(quality)
        dwt_psnr = self.calculate_psnr(self.original, dwt_compressed)
        logger.info(f"DWT PSNR: {dwt_psnr:.2f} dB")

        # Аналіз помилок
        dct_error = np.abs(self.original - dct_compressed)
        dwt_error = np.abs(self.original - dwt_compressed)

        logger.info("-" * 70)
        logger.info("СТАТИСТИКА ПОМИЛОК:")
        logger.info(f"DCT - Макс: {dct_error.max():.2f}, Середня: {dct_error.mean():.2f}, Std: {dct_error.std():.2f}")
        logger.info(f"DWT - Макс: {dwt_error.max():.2f}, Середня: {dwt_error.mean():.2f}, Std: {dwt_error.std():.2f}")

        # Визначення переможця
        winner = "DCT" if dct_psnr > dwt_psnr else "DWT"
        diff = abs(dct_psnr - dwt_psnr)
        logger.info("-" * 70)
        logger.info(f"🏆 КРАЩИЙ МЕТОД: {winner} (перевага: {diff:.2f} dB)")
        logger.info("-" * 70)

        # Візуалізація
        logger.info("Створення візуалізації...")
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # Рядок 1: Оригінал та стиснені зображення
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.imshow(self.original, cmap='gray', vmin=0, vmax=255)
        ax1.set_title('Оригінал', fontsize=12, fontweight='bold')
        ax1.axis('off')

        ax2 = fig.add_subplot(gs[0, 1])
        ax2.imshow(dct_compressed, cmap='gray', vmin=0, vmax=255)
        ax2.set_title(f'DCT\nPSNR: {dct_psnr:.2f} dB', fontsize=12, fontweight='bold')
        ax2.axis('off')

        ax3 = fig.add_subplot(gs[0, 2])
        ax3.imshow(dwt_compressed, cmap='gray', vmin=0, vmax=255)
        ax3.set_title(f'DWT (Haar)\nPSNR: {dwt_psnr:.2f} dB', fontsize=12, fontweight='bold')
        ax3.axis('off')

        # Рядок 2: Карти помилок
        ax4 = fig.add_subplot(gs[1, 0])
        ax4.axis('off')
        ax4.text(0.5, 0.5, 'Карти\nпомилок →', ha='center', va='center',
                 fontsize=14, fontweight='bold', transform=ax4.transAxes)

        ax5 = fig.add_subplot(gs[1, 1])
        im1 = ax5.imshow(dct_error, cmap='hot', vmin=0, vmax=50)
        ax5.set_title(f'DCT помилка\nMax: {dct_error.max():.1f}', fontsize=11)
        ax5.axis('off')
        plt.colorbar(im1, ax=ax5, fraction=0.046, pad=0.04)

        ax6 = fig.add_subplot(gs[1, 2])
        im2 = ax6.imshow(dwt_error, cmap='hot', vmin=0, vmax=50)
        ax6.set_title(f'DWT помилка\nMax: {dwt_error.max():.1f}', fontsize=11)
        ax6.axis('off')
        plt.colorbar(im2, ax=ax6, fraction=0.046, pad=0.04)

        # Рядок 3: Гістограми та порівняння
        ax7 = fig.add_subplot(gs[2, 0])
        ax7.hist(dct_error.flatten(), bins=50, color='#FF6B6B', alpha=0.7, edgecolor='black')
        ax7.set_xlabel('Абсолютна помилка (пікселі)', fontsize=10)
        ax7.set_ylabel('Частота', fontsize=10)
        ax7.set_title('Розподіл помилок DCT', fontsize=11, fontweight='bold')
        ax7.grid(True, alpha=0.3)

        ax8 = fig.add_subplot(gs[2, 1])
        ax8.hist(dwt_error.flatten(), bins=50, color='#4ECDC4', alpha=0.7, edgecolor='black')
        ax8.set_xlabel('Абсолютна помилка (пікселі)', fontsize=10)
        ax8.set_ylabel('Частота', fontsize=10)
        ax8.set_title('Розподіл помилок DWT', fontsize=11, fontweight='bold')
        ax8.grid(True, alpha=0.3)

        ax9 = fig.add_subplot(gs[2, 2])
        methods = ['DCT', 'DWT']
        psnr_values = [dct_psnr, dwt_psnr]
        colors = ['#FF6B6B', '#4ECDC4']
        bars = ax9.bar(methods, psnr_values, color=colors, alpha=0.8, edgecolor='black', linewidth=2)
        ax9.set_ylabel('PSNR (dB)', fontsize=11, fontweight='bold')
        ax9.set_title('Порівняння якості', fontsize=11, fontweight='bold')
        ax9.grid(True, alpha=0.3, axis='y')

        for bar, value in zip(bars, psnr_values):
            height = bar.get_height()
            ax9.text(bar.get_x() + bar.get_width() / 2., height,
                     f'{value:.2f} dB',
                     ha='center', va='bottom', fontsize=10, fontweight='bold')

        better_idx = 0 if dct_psnr > dwt_psnr else 1
        bars[better_idx].set_linewidth(3)
        bars[better_idx].set_edgecolor('gold')

        fig.suptitle(f'Порівняння методів стиснення (якість: {quality}%)',
                     fontsize=16, fontweight='bold', y=0.995)

        filename = f'compression_comparison_q{quality}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        logger.info(f"✓ Графік збережено: {filename}")
        plt.show()

        total_time = time.time() - total_start
        logger.info(f"Загальний час порівняння: {total_time:.2f} сек")
        logger.info("=" * 70)

        return dct_compressed, dwt_compressed, dct_psnr, dwt_psnr


if __name__ == "__main__":
    """
    Приклад використання ImageCompressor.

    Завантажує тестове зображення та порівнює методи стиснення
    з різними рівнями якості.
    """
    logger.info("╔" + "═" * 68 + "╗")
    logger.info("║" + " " * 20 + "IMAGE COMPRESSOR v1.0" + " " * 27 + "║")
    logger.info("║" + " " * 15 + "DCT vs DWT Compression Comparison" + " " * 20 + "║")
    logger.info("╚" + "═" * 68 + "╝")

    try:
        # URL тестового зображення
        url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/800px-Cat03.jpg'

        logger.info(f"\nІніціалізація компресора...")
        compressor = ImageCompressor(url)

        # Порівняння з різними рівнями якості
        quality_levels = [10, 30, 50, 70, 90]
        logger.info(f"\nРівні якості для тестування: {quality_levels}")

        results = []
        for quality in quality_levels:
            dct_img, dwt_img, dct_psnr, dwt_psnr = compressor.compare_compression(quality)
            results.append({
                'quality': quality,
                'dct_psnr': dct_psnr,
                'dwt_psnr': dwt_psnr,
                'winner': 'DCT' if dct_psnr > dwt_psnr else 'DWT'
            })

        # Підсумкова таблиця
        logger.info("\n" + "=" * 70)
        logger.info("ПІДСУМКОВА ТАБЛИЦЯ РЕЗУЛЬТАТІВ")
        logger.info("=" * 70)
        logger.info(f"{'Якість':<10} {'DCT PSNR':<15} {'DWT PSNR':<15} {'Переможець':<15}")
        logger.info("-" * 70)
        for r in results:
            logger.info(f"{r['quality']:<10} {r['dct_psnr']:<15.2f} {r['dwt_psnr']:<15.2f} {r['winner']:<15}")
        logger.info("=" * 70)

        logger.info("\n✓ Всі обчислення завершені успішно!")
        logger.info(f"✓ Результати збережені як PNG файли")
        logger.info(f"✓ Лог-файл збережено")

    except Exception as e:
        logger.error(f"✗ Критична помилка: {e}", exc_info=True)
        logger.info("\nПідказка: Переконайтеся, що:")
        logger.info("  • URL веде до зображення")
        logger.info("  • Є підключення до інтернету")
        logger.info("  • Встановлені всі необхідні бібліотеки")
        logger.info("    pip install numpy matplotlib pillow scipy requests")