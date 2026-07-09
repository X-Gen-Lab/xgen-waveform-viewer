"""
xgen-waveform-viewer - 入口
用法:
    python main.py
    python main.py --port COM3
    python main.py --port /dev/ttyUSB0 --baud 460800
"""

import sys
import argparse
import warnings

# pyqtgraph ViewBox + numpy 2.x: 内部整数比较触发无害的 overflow 警告，直接过滤
warnings.filterwarnings("ignore", message="overflow encountered in cast", category=RuntimeWarning)

import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow
from .config import UART_BAUDRATE
from .version import APP_NAME, APP_TITLE, __version__


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument("--port", type=str, default="", help="串口端口 (如 COM3 或 /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=UART_BAUDRATE, help=f"波特率 (默认 {UART_BAUDRATE})")
    return parser.parse_args()


def main():
    args = parse_args()

    # pyqtgraph 全局设置
    pg.setConfigOptions(antialias=False, background="k", foreground="w")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)

    window = MainWindow()
    window.resize(1100, 650)
    window.show()

    # 如果命令行指定了端口，自动连接
    if args.port:
        window._port_combo.setCurrentText(args.port)
        window._baud_combo.setCurrentText(str(args.baud))
        window._connect()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
