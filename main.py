import cv2
import numpy as np
import argparse
import sys
import time
import signal
from pytube import YouTube
from pytube.exceptions import VideoUnavailable, RegexMatchError
from pytube import request

class ASCIIVideoConverter:
    def __init__(self, width=100, contrast=1.5, color=False, fps=None, charset='default'):
        self.charsets = {
            'default': ' .-:=+*#%@',
            'blocks': ' ░▒▓█',
            'minimal': ' ·+*#',
            'detailed': '$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,"^`\'. '
        }
        self.set_charset(charset)
        self.width = width
        self.contrast = contrast
        self.color = color
        self.fps = fps
        self.running = True
        self.cap = None

        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Настройка HTTP-заголовков для YouTube
        request.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'accept-language': 'en-US,en;q=0.9'
        }

    def set_charset(self, charset_name):
        self.ASCII_CHARS = self.charsets.get(charset_name, self.charsets['default'])

    def signal_handler(self, sig, frame):
        self.running = False

    def map_to_ascii(self, gray_val):
        length = len(self.ASCII_CHARS)
        return self.ASCII_CHARS[min(int(gray_val * length / 255 * self.contrast), length-1)]

    def apply_color(self, char, pixel):
        return f"\033[38;2;{pixel[2]};{pixel[1]};{pixel[0]}m{char}\033[0m" if self.color else char

    def convert_frame(self, frame):
        height = int(self.width / frame.shape[1] * frame.shape[0])
        frame = cv2.resize(frame, (self.width, height))
        return '\n'.join(
            ''.join(self.apply_color(self.map_to_ascii(cv2.cvtColor(np.uint8([[pixel]]), cv2.COLOR_BGR2GRAY)[0][0]), pixel) 
            for row in frame for pixel in row
        ))

    def stream(self, source, output_file=None):
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise ValueError("Не удалось открыть источник видео")
        
        actual_fps = self.fps or self.cap.get(cv2.CAP_PROP_FPS) or 30
        frame_delay = 1 / actual_fps

        while self.running and self.cap.isOpened():
            start_time = time.time()
            ret, frame = self.cap.read()
            if not ret: break

            sys.stdout.write('\033[H\033[J')
            print(self.convert_frame(frame))

            if output_file:
                with open(output_file, 'a') as f:
                    f.write(self.convert_frame(frame) + '\n\n')

            time.sleep(max(frame_delay - (time.time() - start_time), 0))

        self.cap.release()
        cv2.destroyAllWindows()

def interactive_mode():
    print("🏁 ASCII Video Converter - Interactive Mode\n")
    
    try:
        # Выбор источника
        source = input("1. Источник видео:\n[1] Веб-камера\n[2] Файл\n[3] YouTube\nВыберите (1-3): ")
        if source == '1': 
            source = 0
        elif source == '2': 
            source = input("Введите путь к видеофайлу: ")
        elif source == '3':
            url = input("Введите URL YouTube: ")
            try:
                yt = YouTube(url, use_oauth=True, allow_oauth_cache=True)
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                source = stream.url
            except RegexMatchError:
                exit("Ошибка: Некорректный URL YouTube")
            except VideoUnavailable:
                exit("Ошибка: Видео недоступно или приватно")
            except Exception as e:
                exit(f"Ошибка YouTube: {str(e)}")
        else: 
            exit("Неверный выбор")

        # Настройки конвертации
        width = int(input("\n2. Ширина вывода (40-200) [100]: ") or 100)
        contrast = float(input("3. Контрастность (0.5-3.0) [1.5]: ") or 1.5)
        color = input("4. Цветной вывод (y/n) [n]: ").lower() == 'y'
        
        # Выбор набора символов
        charset = input("\n5. Стиль ASCII:\n[1] Стандартный\n[2] Блоки\n[3] Минимализм\n[4] Детализированный\nВыберите (1-4): ")
        charset_map = {'1': 'default', '2': 'blocks', '3': 'minimal', '4': 'detailed'}

        # Запуск конвертера
        converter = ASCIIVideoConverter(
            width=width,
            contrast=contrast,
            color=color,
            charset=charset_map.get(charset, 'default')
        )
        converter.stream(source)

    except Exception as e:
        print(f"\n🚨 Критическая ошибка: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='🎥 ASCII Video Stream with Multiple Modes')
    parser.add_argument('-i', '--interactive', action='store_true', help='Запустить в интерактивном режиме')
    parser.add_argument('-s', '--source', default=0, help='Источник видео')
    parser.add_argument('-w', '--width', type=int, default=100, help='Ширина вывода')
    parser.add_argument('-c', '--contrast', type=float, default=1.5, help='Контрастность')
    parser.add_argument('--color', action='store_true', help='Цветной вывод')
    parser.add_argument('--charset', default='default', 
                      choices=['default', 'blocks', 'minimal', 'detailed'], help='Стиль символов')
    parser.add_argument('-o', '--output', help='Файл для сохранения')

    if len(sys.argv) == 1:
        interactive_mode()
    else:
        args = parser.parse_args()
        if args.interactive:
            interactive_mode()
        else:
            try:
                if 'youtube.com' in args.source:
                    yt = YouTube(args.source, use_oauth=True, allow_oauth_cache=True)
                    stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
                    args.source = stream.url
                
                ASCIIVideoConverter(
                    width=args.width,
                    contrast=args.contrast,
                    color=args.color,
                    charset=args.charset
                ).stream(args.source, args.output)
            except Exception as e:
                print(f"🚨 Ошибка: {e}")
            finally:
                print("\nПреобразование завершено")