"""
性能优化模块
实现数据降采样、渲染优化和内存管理功能
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class DownsampleResult:
    """降采样结果"""
    time: np.ndarray
    min_values: np.ndarray
    max_values: np.ndarray
    mean_values: np.ndarray
    original_length: int
    downsampled_length: int
    downsample_factor: int


class PerformanceOptimizer:
    """性能优化器"""
    
    # 渲染阈值：超过此数量的点将触发降采样
    DOWNSAMPLE_THRESHOLD = 10000
    
    # 目标渲染点数
    TARGET_RENDER_POINTS = 5000
    
    def __init__(self):
        self._fps_limit = 30.0
        self._enable_downsampling = True
        self._downsample_threshold = self.DOWNSAMPLE_THRESHOLD
        self._target_points = self.TARGET_RENDER_POINTS
    
    def set_fps_limit(self, fps: float):
        """设置帧率限制"""
        self._fps_limit = max(1.0, min(float(fps), 120.0))
    
    def get_fps_limit(self) -> float:
        """获取帧率限制"""
        return self._fps_limit
    
    def get_refresh_interval_ms(self) -> int:
        """获取刷新间隔（毫秒）"""
        return int(1000.0 / self._fps_limit)
    
    def set_enable_downsampling(self, enabled: bool):
        """启用/禁用降采样"""
        self._enable_downsampling = bool(enabled)
    
    def is_downsampling_enabled(self) -> bool:
        """是否启用降采样"""
        return self._enable_downsampling
    
    def set_downsample_threshold(self, threshold: int):
        """设置降采样阈值"""
        self._downsample_threshold = max(1000, int(threshold))
    
    def get_downsample_threshold(self) -> int:
        """获取降采样阈值"""
        return self._downsample_threshold
    
    def should_downsample(self, data_length: int) -> bool:
        """判断是否需要降采样"""
        if not self._enable_downsampling:
            return False
        return data_length > self._downsample_threshold
    
    def calculate_downsample_factor(self, data_length: int) -> int:
        """计算降采样因子"""
        if data_length <= self._target_points:
            return 1
        factor = int(np.ceil(data_length / self._target_points))
        return max(1, factor)
    
    def downsample_minmax(
        self, 
        time: np.ndarray, 
        data: np.ndarray,
        factor: Optional[int] = None
    ) -> DownsampleResult:
        """
        使用 min/max 方法降采样
        
        对于每个降采样段，保留最小值、最大值和平均值
        这样可以保留波形的峰值特征
        
        参数:
            time: 时间数组
            data: 数据数组
            factor: 降采样因子（None 表示自动计算）
        
        返回:
            DownsampleResult 对象
        """
        original_length = len(data)
        
        if factor is None:
            factor = self.calculate_downsample_factor(original_length)
        
        if factor <= 1:
            # 不需要降采样
            return DownsampleResult(
                time=time.copy(),
                min_values=data.copy(),
                max_values=data.copy(),
                mean_values=data.copy(),
                original_length=original_length,
                downsampled_length=original_length,
                downsample_factor=1
            )
        
        # 计算完整段的数量
        n_segments = original_length // factor
        remainder = original_length % factor
        
        # 重塑数据为 (n_segments, factor) 以便进行向量化操作
        reshaped_data = data[:n_segments * factor].reshape(n_segments, factor)
        reshaped_time = time[:n_segments * factor].reshape(n_segments, factor)
        
        # 计算每段的统计值
        min_vals = np.min(reshaped_data, axis=1)
        max_vals = np.max(reshaped_data, axis=1)
        mean_vals = np.mean(reshaped_data, axis=1)
        time_vals = np.mean(reshaped_time, axis=1)
        
        # 处理余数部分
        if remainder > 0:
            tail_data = data[n_segments * factor:]
            tail_time = time[n_segments * factor:]
            
            min_vals = np.append(min_vals, np.min(tail_data))
            max_vals = np.append(max_vals, np.max(tail_data))
            mean_vals = np.append(mean_vals, np.mean(tail_data))
            time_vals = np.append(time_vals, np.mean(tail_time))
        
        return DownsampleResult(
            time=time_vals,
            min_values=min_vals,
            max_values=max_vals,
            mean_values=mean_vals,
            original_length=original_length,
            downsampled_length=len(time_vals),
            downsample_factor=factor
        )
    
    def prepare_render_data(
        self,
        time: np.ndarray,
        data: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        准备用于渲染的数据
        
        如果数据量大，使用 min/max 降采样生成渲染数据
        返回交错的 min/max 数据以保留波形细节
        
        返回:
            (time_array, data_array) 用于绘制
        """
        if not self.should_downsample(len(data)):
            return time, data
        
        result = self.downsample_minmax(time, data)
        
        # 为每个段创建 min 和 max 两个点
        # 这样可以确保波形的峰值被保留
        n = result.downsampled_length
        render_time = np.empty(n * 2, dtype=time.dtype)
        render_data = np.empty(n * 2, dtype=data.dtype)
        
        # 交错填充 min 和 max
        render_time[0::2] = result.time
        render_time[1::2] = result.time
        render_data[0::2] = result.min_values
        render_data[1::2] = result.max_values
        
        return render_time, render_data


class MemoryOptimizer:
    """内存优化器"""
    
    # 内存限制（字节）
    DEFAULT_MEMORY_LIMIT = 200 * 1024 * 1024  # 200 MB
    
    # 样本数据类型大小
    SAMPLE_SIZE_BYTES = 2  # uint16
    
    def __init__(self):
        self._memory_limit_bytes = self.DEFAULT_MEMORY_LIMIT
        self._auto_limit_enabled = True
    
    def set_memory_limit_mb(self, limit_mb: float):
        """设置内存限制（MB）"""
        self._memory_limit_bytes = int(limit_mb * 1024 * 1024)
    
    def get_memory_limit_mb(self) -> float:
        """获取内存限制（MB）"""
        return self._memory_limit_bytes / (1024 * 1024)
    
    def set_auto_limit_enabled(self, enabled: bool):
        """启用/禁用自动内存限制"""
        self._auto_limit_enabled = bool(enabled)
    
    def is_auto_limit_enabled(self) -> bool:
        """是否启用自动内存限制"""
        return self._auto_limit_enabled
    
    def calculate_max_samples(self) -> int:
        """计算可容纳的最大样本数"""
        return self._memory_limit_bytes // self.SAMPLE_SIZE_BYTES
    
    def estimate_memory_usage(self, n_samples: int) -> int:
        """估算内存使用（字节）"""
        return n_samples * self.SAMPLE_SIZE_BYTES
    
    def is_within_limit(self, n_samples: int) -> bool:
        """检查样本数是否在内存限制内"""
        if not self._auto_limit_enabled:
            return True
        return self.estimate_memory_usage(n_samples) <= self._memory_limit_bytes
    
    def suggest_buffer_size(self, requested_samples: int) -> int:
        """建议合适的缓冲区大小"""
        if not self._auto_limit_enabled:
            return requested_samples
        
        max_samples = self.calculate_max_samples()
        return min(requested_samples, max_samples)
    
    @staticmethod
    def format_bytes(size_bytes: int) -> str:
        """格式化字节数为可读字符串"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
