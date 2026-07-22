"""
主题管理
支持暗色/亮色主题切换
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
import pyqtgraph as pg


class Theme:
    """主题管理器"""

    DARK = "dark"
    LIGHT = "light"

    @staticmethod
    def apply_theme(theme: str) -> None:
        """应用主题到应用程序"""
        if theme == Theme.LIGHT:
            Theme._apply_light_theme()
        else:
            Theme._apply_dark_theme()

    @staticmethod
    def _apply_dark_theme() -> None:
        """应用暗色主题"""
        app = QApplication.instance()
        if app is None:
            return

        # Qt 调色板
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
        # 禁用状态
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))
        
        app.setPalette(palette)

        # pyqtgraph 全局配置
        pg.setConfigOptions(
            antialias=False,
            background=(3, 7, 10),
            foreground=(220, 220, 220)
        )

        # 样式表
        app.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QToolTip {
                background-color: #2d2d2d;
                color: #dcdcdc;
                border: 1px solid #555;
                padding: 3px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #2d2d2d;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 3px 5px;
                color: #dcdcdc;
            }
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
                border: 1px solid #42a5f5;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px 12px;
                color: #dcdcdc;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #42a5f5;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
            }
            QPushButton:disabled {
                background-color: #252525;
                color: #7f7f7f;
                border: 1px solid #3a3a3a;
            }
            QStatusBar {
                background-color: #252525;
                color: #aaa;
            }
            QLabel {
                color: #dcdcdc;
            }
        """)

    @staticmethod
    def _apply_light_theme() -> None:
        """应用亮色主题"""
        app = QApplication.instance()
        if app is None:
            return

        # Qt 调色板
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
        # 禁用状态
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(120, 120, 120))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(120, 120, 120))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(120, 120, 120))
        
        app.setPalette(palette)

        # pyqtgraph 全局配置
        pg.setConfigOptions(
            antialias=False,
            background=(255, 255, 255),
            foreground=(0, 0, 0)
        )

        # 样式表
        app.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QToolTip {
                background-color: #ffffdc;
                color: #000;
                border: 1px solid #999;
                padding: 3px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #fff;
                border: 1px solid #999;
                border-radius: 3px;
                padding: 3px 5px;
                color: #000;
            }
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
                border: 1px solid #42a5f5;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #999;
                border-radius: 4px;
                padding: 5px 12px;
                color: #000;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
                border: 1px solid #42a5f5;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #999;
                border: 1px solid #ccc;
            }
            QStatusBar {
                background-color: #e8e8e8;
                color: #555;
            }
            QLabel {
                color: #000;
            }
        """)

    @staticmethod
    def get_waveform_colors(theme: str) -> dict:
        """获取波形颜色配置"""
        if theme == Theme.LIGHT:
            return {
                "curve": (0, 150, 136),  # 青绿色
                "cursor_v": (255, 152, 0, 180),  # 橙色
                "cursor_h": (255, 152, 0, 150),
                "grid_alpha": 0.3,
                "text": (0, 0, 0),
                "axis": (100, 100, 100),
            }
        else:
            return {
                "curve": (0, 255, 160),  # 青绿色
                "cursor_v": (255, 212, 96, 150),  # 金色
                "cursor_h": (255, 212, 96, 120),
                "grid_alpha": 0.22,
                "text": (225, 235, 238),
                "axis": (150, 165, 170),
            }
