"""
日志记录系统
提供结构化的异常和事件日志功能
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict
import json


@dataclass
class LogEvent:
    """日志事件"""
    timestamp: str
    level: str
    category: str
    message: str
    details: Optional[dict] = None


class AppLogger:
    """应用程序日志器"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        初始化日志器
        
        参数:
            log_dir: 日志目录（None 表示使用默认目录）
        """
        if log_dir is None:
            # 使用用户目录下的日志文件夹
            log_dir = Path.home() / ".xgen-waveform-viewer" / "logs"
        
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建日志文件名（包含日期）
        date_str = datetime.now().strftime("%Y%m%d")
        self._log_file = self._log_dir / f"xgen_waveform_{date_str}.log"
        
        # 配置 Python 标准日志器
        self._logger = logging.getLogger("xgen_waveform_viewer")
        self._logger.setLevel(logging.DEBUG)
        
        # 文件处理器
        file_handler = logging.FileHandler(self._log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        
        # 控制台处理器（仅警告及以上）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(console_formatter)
        
        # 避免重复添加处理器
        if not self._logger.handlers:
            self._logger.addHandler(file_handler)
            self._logger.addHandler(console_handler)
        
        # 事件日志（用于 UI 显示）
        self._event_log: list[LogEvent] = []
        self._max_events = 1000
    
    def debug(self, message: str, category: str = "general", details: Optional[dict] = None):
        """记录调试信息"""
        self._logger.debug(message)
        self._add_event("DEBUG", category, message, details)
    
    def info(self, message: str, category: str = "general", details: Optional[dict] = None):
        """记录信息"""
        self._logger.info(message)
        self._add_event("INFO", category, message, details)
    
    def warning(self, message: str, category: str = "general", details: Optional[dict] = None):
        """记录警告"""
        self._logger.warning(message)
        self._add_event("WARNING", category, message, details)
    
    def error(self, message: str, category: str = "general", details: Optional[dict] = None, exc_info: bool = False):
        """记录错误"""
        self._logger.error(message, exc_info=exc_info)
        self._add_event("ERROR", category, message, details)
    
    def critical(self, message: str, category: str = "general", details: Optional[dict] = None, exc_info: bool = False):
        """记录严重错误"""
        self._logger.critical(message, exc_info=exc_info)
        self._add_event("CRITICAL", category, message, details)
    
    def log_serial_event(self, event_type: str, details: Optional[dict] = None):
        """记录串口事件"""
        message = f"Serial event: {event_type}"
        self.info(message, category="serial", details=details)
    
    def log_frame_event(self, event_type: str, seq: Optional[int] = None, details: Optional[dict] = None):
        """记录帧事件"""
        message = f"Frame event: {event_type}"
        if seq is not None:
            message += f" (seq={seq})"
        
        if details is None:
            details = {}
        if seq is not None:
            details["seq"] = seq
        
        self.debug(message, category="frame", details=details)
    
    def log_crc_error(self, seq: Optional[int] = None, expected: Optional[int] = None, received: Optional[int] = None):
        """记录 CRC 错误"""
        details = {}
        if seq is not None:
            details["seq"] = seq
        if expected is not None:
            details["expected_crc"] = expected
        if received is not None:
            details["received_crc"] = received
        
        self.warning("CRC validation failed", category="crc_error", details=details)
    
    def log_seq_gap(self, expected: int, received: int, gap: int):
        """记录序列号间隙"""
        details = {
            "expected_seq": expected,
            "received_seq": received,
            "gap_size": gap
        }
        self.warning(f"Sequence gap detected: expected {expected}, got {received}", 
                    category="seq_gap", details=details)
    
    def log_resync(self, reason: str = "unknown"):
        """记录重同步事件"""
        self.warning(f"Frame resynchronization: {reason}", category="resync")
    
    def log_recording_event(self, event_type: str, details: Optional[dict] = None):
        """记录录制事件"""
        message = f"Recording event: {event_type}"
        self.info(message, category="recording", details=details)
    
    def log_performance_warning(self, message: str, details: Optional[dict] = None):
        """记录性能警告"""
        self.warning(message, category="performance", details=details)
    
    def _add_event(self, level: str, category: str, message: str, details: Optional[dict]):
        """添加事件到事件日志"""
        event = LogEvent(
            timestamp=datetime.now().isoformat(),
            level=level,
            category=category,
            message=message,
            details=details
        )
        
        self._event_log.append(event)
        
        # 限制事件日志大小
        if len(self._event_log) > self._max_events:
            self._event_log = self._event_log[-self._max_events:]
    
    def get_events(
        self,
        level: Optional[str] = None,
        category: Optional[str] = None,
        limit: Optional[int] = None
    ) -> list[LogEvent]:
        """
        获取事件日志
        
        参数:
            level: 过滤级别
            category: 过滤类别
            limit: 限制数量
        
        返回:
            事件列表
        """
        events = self._event_log
        
        if level is not None:
            events = [e for e in events if e.level == level]
        
        if category is not None:
            events = [e for e in events if e.category == category]
        
        if limit is not None:
            events = events[-limit:]
        
        return events
    
    def get_error_count(self) -> int:
        """获取错误数量"""
        return len([e for e in self._event_log if e.level in ("ERROR", "CRITICAL")])
    
    def get_warning_count(self) -> int:
        """获取警告数量"""
        return len([e for e in self._event_log if e.level == "WARNING"])
    
    def clear_events(self):
        """清空事件日志"""
        self._event_log.clear()
    
    def export_events_json(self, filepath: Path):
        """导出事件日志为 JSON 文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in self._event_log], f, indent=2, ensure_ascii=False)
    
    def get_log_file_path(self) -> Path:
        """获取日志文件路径"""
        return self._log_file
    
    def cleanup_old_logs(self, days: int = 7):
        """清理旧日志文件"""
        cutoff = datetime.now().timestamp() - (days * 86400)
        
        for log_file in self._log_dir.glob("xgen_waveform_*.log"):
            if log_file.stat().st_mtime < cutoff:
                try:
                    log_file.unlink()
                    self.info(f"Deleted old log file: {log_file.name}")
                except Exception as e:
                    self.error(f"Failed to delete log file {log_file.name}: {e}")


# 全局日志器实例
_global_logger: Optional[AppLogger] = None


def get_logger() -> AppLogger:
    """获取全局日志器实例"""
    global _global_logger
    if _global_logger is None:
        _global_logger = AppLogger()
    return _global_logger


def init_logger(log_dir: Optional[Path] = None) -> AppLogger:
    """初始化全局日志器"""
    global _global_logger
    _global_logger = AppLogger(log_dir)
    return _global_logger
