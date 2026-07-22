"""
用户配置管理
持久化保存用户偏好设置
"""

import json
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QSettings


class AppSettings:
    """应用程序设置管理器"""

    def __init__(self, org_name: str = "X-GEN-LAB", app_name: str = "xgen-waveform-viewer"):
        self._settings = QSettings(org_name, app_name)
        self._defaults = self._get_defaults()

    @staticmethod
    def _get_defaults() -> dict[str, Any]:
        """默认配置"""
        return {
            # 串口设置
            "serial/last_port": "",
            "serial/baudrate": 460800,
            "serial/databits": 8,
            "serial/stopbits": 1.0,
            "serial/parity": "None",
            "serial/auto_reconnect": False,
            "serial/reconnect_delay": 3.0,
            
            # 显示设置
            "display/theme": "dark",  # dark, light
            "display/x_window": 2.0,
            "display/buffer_limit": 10.0,  # Mpts
            "display/y_auto": True,
            "display/y_min": 0.0,
            "display/y_max": 1200.0,
            
            # 录制设置
            "record/format": "bin",  # bin, csv
            "record/save_dir": "",
            
            # 窗口设置
            "window/geometry": None,
            "window/width": 1100,
            "window/height": 650,
            
            # 快捷键启用
            "shortcuts/enabled": True,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """获取设置值"""
        if default is None:
            default = self._defaults.get(key)
        value = self._settings.value(key, default)
        
        # 类型转换
        if key in self._defaults:
            default_type = type(self._defaults[key])
            if default_type == bool:
                return str(value).lower() in ("true", "1", "yes")
            elif default_type in (int, float):
                try:
                    return default_type(value)
                except (ValueError, TypeError):
                    return default
        
        return value

    def set(self, key: str, value: Any) -> None:
        """设置值"""
        self._settings.setValue(key, value)

    def sync(self) -> None:
        """同步到磁盘"""
        self._settings.sync()

    def reset(self) -> None:
        """重置所有设置"""
        self._settings.clear()

    def export_to_file(self, path: str | Path) -> None:
        """导出配置到 JSON 文件"""
        path = Path(path)
        config = {}
        for key in self._defaults.keys():
            config[key] = self.get(key)
        
        path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    def import_from_file(self, path: str | Path) -> None:
        """从 JSON 文件导入配置"""
        path = Path(path)
        if not path.exists():
            return
        
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
            for key, value in config.items():
                self.set(key, value)
            self.sync()
        except Exception:
            pass  # 忽略导入错误
