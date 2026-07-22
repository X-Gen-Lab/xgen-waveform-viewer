"""
多通道数据模型与管理 - V3.0

支持多通道 ADC 数据的采集、显示和管理：
- 通道配置（颜色、标签、可见性）
- 通道分组显示
- 通道独立 Y 轴设置
- 多通道数据缓冲区管理
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor


@dataclass
class ChannelConfig:
    """单通道配置"""
    channel_id: int
    label: str = ""
    color: str = "#00ff00"  # 默认绿色
    visible: bool = True
    y_offset: float = 0.0  # Y 轴偏移（用于通道分组显示）
    y_scale: float = 1.0   # Y 轴缩放
    group: str = "default"  # 通道分组
    
    def __post_init__(self):
        if not self.label:
            self.label = f"CH{self.channel_id}"


@dataclass
class ChannelData:
    """单通道数据缓冲区"""
    channel_id: int
    samples: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.uint16))
    timestamps: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    sequence_numbers: List[int] = field(default_factory=list)
    
    def append(self, data: np.ndarray, seq: int, timestamp: float):
        """追加数据到缓冲区"""
        self.samples = np.append(self.samples, data)
        # 为每个采样点生成时间戳
        dt = 1.0 / 10000.0  # 假设 10kHz 采样率，实际应从配置读取
        new_timestamps = np.arange(len(data)) * dt + timestamp
        self.timestamps = np.append(self.timestamps, new_timestamps)
        self.sequence_numbers.append(seq)
    
    def clear(self):
        """清空缓冲区"""
        self.samples = np.array([], dtype=np.uint16)
        self.timestamps = np.array([], dtype=np.float64)
        self.sequence_numbers.clear()
    
    def trim_to_size(self, max_samples: int):
        """限制缓冲区大小"""
        if len(self.samples) > max_samples:
            self.samples = self.samples[-max_samples:]
            self.timestamps = self.timestamps[-max_samples:]
            # 保留对应的序列号
            total_trimmed = len(self.samples) - max_samples
            while self.sequence_numbers and total_trimmed > 0:
                self.sequence_numbers.pop(0)
                total_trimmed -= 1


class MultiChannelManager(QObject):
    """多通道管理器"""
    
    # 信号：通道配置变更
    channel_config_changed = pyqtSignal(int)  # channel_id
    # 信号：通道数据更新
    channel_data_updated = pyqtSignal(int)  # channel_id
    # 信号：通道列表变更
    channels_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._channels: Dict[int, ChannelConfig] = {}
        self._data: Dict[int, ChannelData] = {}
        self._max_samples_per_channel = 1_000_000  # 默认每通道 1M 采样点
        self._default_colors = [
            "#00ff00",  # 绿色
            "#ffff00",  # 黄色
            "#ff00ff",  # 品红
            "#00ffff",  # 青色
            "#ff8800",  # 橙色
            "#8800ff",  # 紫色
            "#ff0088",  # 粉红
            "#88ff00",  # 黄绿
        ]
    
    def add_channel(self, channel_id: int, label: str = "", color: str = "") -> ChannelConfig:
        """添加通道"""
        if not color:
            # 自动分配颜色
            color = self._default_colors[channel_id % len(self._default_colors)]
        
        config = ChannelConfig(
            channel_id=channel_id,
            label=label or f"CH{channel_id}",
            color=color
        )
        self._channels[channel_id] = config
        self._data[channel_id] = ChannelData(channel_id)
        
        self.channels_changed.emit()
        return config
    
    def remove_channel(self, channel_id: int):
        """移除通道"""
        if channel_id in self._channels:
            del self._channels[channel_id]
            del self._data[channel_id]
            self.channels_changed.emit()
    
    def get_channel_config(self, channel_id: int) -> Optional[ChannelConfig]:
        """获取通道配置"""
        return self._channels.get(channel_id)
    
    def update_channel_config(self, channel_id: int, **kwargs):
        """更新通道配置"""
        if channel_id in self._channels:
            config = self._channels[channel_id]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            self.channel_config_changed.emit(channel_id)
    
    def get_channel_data(self, channel_id: int) -> Optional[ChannelData]:
        """获取通道数据"""
        return self._data.get(channel_id)
    
    def append_data(self, channel_id: int, samples: np.ndarray, seq: int, timestamp: float):
        """追加数据到指定通道"""
        if channel_id not in self._data:
            self.add_channel(channel_id)
        
        data = self._data[channel_id]
        data.append(samples, seq, timestamp)
        
        # 限制缓冲区大小
        data.trim_to_size(self._max_samples_per_channel)
        
        self.channel_data_updated.emit(channel_id)
    
    def clear_all_data(self):
        """清空所有通道数据"""
        for data in self._data.values():
            data.clear()
        for channel_id in self._channels:
            self.channel_data_updated.emit(channel_id)
    
    def clear_channel_data(self, channel_id: int):
        """清空指定通道数据"""
        if channel_id in self._data:
            self._data[channel_id].clear()
            self.channel_data_updated.emit(channel_id)
    
    def get_all_channels(self) -> List[ChannelConfig]:
        """获取所有通道配置"""
        return list(self._channels.values())
    
    def get_visible_channels(self) -> List[ChannelConfig]:
        """获取所有可见通道"""
        return [ch for ch in self._channels.values() if ch.visible]
    
    def get_channels_by_group(self, group: str) -> List[ChannelConfig]:
        """按分组获取通道"""
        return [ch for ch in self._channels.values() if ch.group == group]
    
    def set_max_samples_per_channel(self, max_samples: int):
        """设置每通道最大采样点数"""
        self._max_samples_per_channel = max_samples
        # 立即应用到现有数据
        for data in self._data.values():
            data.trim_to_size(max_samples)
    
    def get_channel_count(self) -> int:
        """获取通道总数"""
        return len(self._channels)
    
    def save_config(self) -> dict:
        """保存通道配置为字典"""
        return {
            str(ch_id): {
                "label": config.label,
                "color": config.color,
                "visible": config.visible,
                "y_offset": config.y_offset,
                "y_scale": config.y_scale,
                "group": config.group,
            }
            for ch_id, config in self._channels.items()
        }
    
    def load_config(self, config_dict: dict):
        """从字典加载通道配置"""
        for ch_id_str, ch_config in config_dict.items():
            channel_id = int(ch_id_str)
            if channel_id not in self._channels:
                self.add_channel(channel_id)
            self.update_channel_config(channel_id, **ch_config)
