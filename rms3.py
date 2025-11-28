import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from scipy.fftpack import dct, idct
import requests
from io import BytesIO


class ImageCompressor:
    def __init__(self, source):

        try:
            # Перевіряємо чи це URL
            if source.startswith('http://') or source.startswith('https://'):
                print(f"Завантаження зображення з URL: {source}")

                # Додаємо User-Agent заголовок для Wikimedia та інших сайтів
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(source, headers=headers, timeout=10)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content)).convert('L')
            else:
                print(f"Завантаження локального файлу: {source}")
                image = Image.open(source).convert('L')

            self.original = np.array(image, dtype=float)
            self.height, self.width = self.original.shape
            print(f"Розмір зображення: {self.width}x{self.height}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Помилка при завантаженні з URL: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл '{source}' не знайдено")
        except Exception as e:
            raise Exception(f"Помилка при завантаженні зображення: {e}")

    def calculate_psnr(self, original, compressed):
        """Розрахунок PSNR (Peak Signal-to-Noise Ratio)"""
        mse = np.mean((original - compressed) ** 2)
        if mse == 0:
            return float('inf')
        max_pixel = 255.0
        psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
        return psnr

    def dct2(self, block):
        """2D DCT перетворення"""
        return dct(dct(block.T, norm='ortho').T, norm='ortho')

    def idct2(self, block):
        """Зворотнє 2D DCT перетворення"""
        return idct(idct(block.T, norm='ortho').T, norm='ortho')

    def compress_dct(self, quality=50):
        """Стиснення за допомогою DCT (блоки 8x8)"""
        block_size = 8

        pad_h = (block_size - self.height % block_size) % block_size
        pad_w = (block_size - self.width % block_size) % block_size
        padded = np.pad(self.original, ((0, pad_h), (0, pad_w)), mode='edge')

        compressed = np.zeros_like(padded)

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

        if quality < 50:
            scale = 50.0 / quality
        else:
            scale = 2.0 - quality / 50.0

        quant_matrix = np.floor(quant_matrix * scale + 0.5)
        quant_matrix[quant_matrix == 0] = 1

        for i in range(0, padded.shape[0], block_size):
            for j in range(0, padded.shape[1], block_size):
                block = padded[i:i + block_size, j:j + block_size]

                dct_block = self.dct2(block - 128)

                quantized = np.round(dct_block / quant_matrix)

                dequantized = quantized * quant_matrix

                reconstructed = self.idct2(dequantized) + 128
                compressed[i:i + block_size, j:j + block_size] = reconstructed

        compressed = compressed[:self.height, :self.width]
        compressed = np.clip(compressed, 0, 255)
        return compressed

    def haar_transform(self, data):
        """Вейвлет перетворення Хаара (1D)"""
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
        """Зворотнє вейвлет перетворення Хаара (1D)"""
        length = len(data)
        output = np.zeros(length, dtype=float)
        half = length // 2

        for i in range(half):
            output[2 * i] = (data[i] + data[half + i]) / np.sqrt(2)
            output[2 * i + 1] = (data[i] - data[half + i]) / np.sqrt(2)
        return output

    def dwt2(self, image):
        """2D вейвлет перетворення"""
        rows = np.array([self.haar_transform(row) for row in image])
        cols = np.array([self.haar_transform(col) for col in rows.T]).T
        return cols

    def idwt2(self, coeffs):
        """Зворотнє 2D вейвлет перетворення"""
        cols = np.array([self.inverse_haar_transform(col) for col in coeffs.T]).T
        rows = np.array([self.inverse_haar_transform(row) for row in cols])
        return rows

    def compress_dwt(self, quality=50):
        """Стиснення за допомогою DWT (вейвлет Хаара)"""
        max_levels = int(np.log2(min(self.height, self.width)))
        levels = min(3, max_levels)

        target_size = 2 ** levels
        pad_h = (target_size - self.height % target_size) % target_size
        pad_w = (target_size - self.width % target_size) % target_size

        image = np.pad(self.original, ((0, pad_h), (0, pad_w)), mode='edge')

        coeffs = image.copy()
        for level in range(levels):
            h = image.shape[0] // (2 ** level)
            w = image.shape[1] // (2 ** level)

            if h >= 2 and w >= 2:
                block = coeffs[:h, :w]
                coeffs[:h, :w] = self.dwt2(block)

        keep_percent = quality
        threshold = np.percentile(np.abs(coeffs), 100 - keep_percent)
        coeffs_thresholded = coeffs.copy()
        coeffs_thresholded[np.abs(coeffs) < threshold] = 0

        reconstructed = coeffs_thresholded.copy()
        for level in range(levels - 1, -1, -1):
            h = image.shape[0] // (2 ** level)
            w = image.shape[1] // (2 ** level)

            if h >= 2 and w >= 2:
                block = reconstructed[:h, :w]
                reconstructed[:h, :w] = self.idwt2(block)

        reconstructed = reconstructed[:self.height, :self.width]
        reconstructed = np.clip(reconstructed, 0, 255)
        return reconstructed

    def compare_compression(self, quality=50):
        """Порівняння методів стиснення"""
        print(f"\nСтиснення з якістю: {quality}%")

        print("Обробка DCT...")
        dct_compressed = self.compress_dct(quality)
        dct_psnr = self.calculate_psnr(self.original, dct_compressed)

        print("Обробка DWT...")
        dwt_compressed = self.compress_dwt(quality)
        dwt_psnr = self.calculate_psnr(self.original, dwt_compressed)

        dct_error = np.abs(self.original - dct_compressed)
        dwt_error = np.abs(self.original - dwt_compressed)

        print(f"DCT PSNR: {dct_psnr:.2f} dB")
        print(f"DWT PSNR: {dwt_psnr:.2f} dB")

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

        # Додаємо значення на стовпчики
        for bar, value in zip(bars, psnr_values):
            height = bar.get_height()
            ax9.text(bar.get_x() + bar.get_width() / 2., height,
                     f'{value:.2f} dB',
                     ha='center', va='bottom', fontsize=10, fontweight='bold')

        # Виділяємо кращий результат
        better_idx = 0 if dct_psnr > dwt_psnr else 1
        bars[better_idx].set_linewidth(3)
        bars[better_idx].set_edgecolor('gold')

        fig.suptitle(f'Порівняння методів стиснення (якість: {quality}%)',
                     fontsize=16, fontweight='bold', y=0.995)

        plt.savefig(f'compression_comparison_q{quality}.png', dpi=150, bbox_inches='tight')
        plt.show()

        return dct_compressed, dwt_compressed, dct_psnr, dwt_psnr


if __name__ == "__main__":
    try:
        url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/800px-Cat03.jpg'
        compressor = ImageCompressor(url)

        # Порівняння з різними рівнями якості
        for quality in [10, 30, 50, 70, 90]:
            compressor.compare_compression(quality)

        print("\n Готово! Результати збережені як PNG файли.")

    except Exception as e:
        print(f" Помилка: {e}")
        print("\n Підказка: Переконайтеся, що URL веде до зображення")
        print("   або файл існує в поточній директорії")