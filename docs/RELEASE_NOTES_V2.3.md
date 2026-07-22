# xgen-waveform-viewer V2.3 发布说明

发布日期：2024-12-22

## 概述

V2.3 版本专注于**性能优化**和**鲁棒性提升**，为高速数据采集和长时间运行提供了强大的支持。此版本引入了智能降采样算法、帧率限制、内存管理、完整的日志系统和实时统计面板。

## 核心特性

### 🚀 性能优化

#### 1. Min/Max 降采样算法
智能降采样技术，在不损失波形关键特征的前提下大幅提升渲染性能。

**主要功能：**
- 自动触发：当数据点超过阈值（默认 10,000 点）时自动启用
- 峰值保留：使用 min/max 分段算法保留波形的峰值和谷值
- 可配置：可调节降采样阈值和目标渲染点数
- 透明化：降采样过程对用户透明，无需手动干预

**性能提升：**
- 对于 >10,000 点的数据集，渲染速度提升 5-10 倍
- 消除了高密度波形的卡顿现象
- 保持视觉保真度，不会丢失重要的波形细节

**使用示例：**
```python
from performance import PerformanceOptimizer

# 创建性能优化器
optimizer = PerformanceOptimizer()

# 配置降采样阈值
optimizer.set_downsample_threshold(15000)  # 超过 15,000 点触发降采样

# 准备渲染数据（自动降采样）
time_render, data_render = optimizer.prepare_render_data(time, data)
```

#### 2. 帧率限制
可配置的显示刷新率控制，降低 CPU 使用率。

**主要功能：**
- FPS 范围：1-120 FPS（默认 30 FPS）
- 独立控制：显示刷新率与数据采集率独立
- 动态调整：可在运行时调整帧率限制

**性能提升：**
- CPU 使用率降低 30-50%
- 延长笔记本电脑电池续航
- 减少发热和风扇噪音

**配置方法：**
```python
# 设置帧率限制为 60 FPS
optimizer.set_fps_limit(60.0)

# 获取刷新间隔（毫秒）
interval_ms = optimizer.get_refresh_interval_ms()  # 返回 16 (≈60 FPS)
```

#### 3. 内存管理
自动内存优化，防止系统内存耗尽。

**主要功能：**
- 内存限制：默认 200 MB，可配置
- 自动调整：根据内存限制自动调整缓冲区大小
- 使用监控：实时估算内存使用量

**使用方法：**
```python
from performance import MemoryOptimizer

mem_optimizer = MemoryOptimizer()

# 设置内存限制为 100 MB
mem_optimizer.set_memory_limit_mb(100.0)

# 计算可容纳的最大样本数
max_samples = mem_optimizer.calculate_max_samples()

# 检查是否在限制内
if mem_optimizer.is_within_limit(requested_samples):
    # 分配缓冲区
    pass
```

### 🛡️ 鲁棒性提升

#### 1. 日志记录系统
全面的事件和错误日志功能。

**主要功能：**
- 分类日志：serial, frame, crc_error, seq_gap, resync, recording, performance
- 多级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
- 自动归档：日志文件按日期命名，自动清理旧文件（默认 7 天）
- JSON 导出：支持导出为 JSON 格式进行分析

**日志位置：**
```
Windows: C:\Users\<用户名>\.xgen-waveform-viewer\logs\
Linux/Mac: ~/.xgen-waveform-viewer/logs/
```

**日志文件命名：**
```
xgen_waveform_20241222.log
```

**使用示例：**
```python
from logger import get_logger

logger = get_logger()

# 记录信息
logger.info("Application started", category="app")

# 记录警告
logger.warning("High error rate detected", category="performance", 
              details={"error_rate": 5.2})

# 记录错误
logger.error("Failed to open file", category="recording", exc_info=True)

# 记录 CRC 错误
logger.log_crc_error(seq=1234, expected=0xABCD, received=0x1234)

# 记录序列号间隙
logger.log_seq_gap(expected=100, received=105, gap=5)

# 导出日志
logger.export_events_json(Path("log_export.json"))
```

#### 2. 统计面板
实时数据完整性可视化。

**主要功能：**
- 实时统计：总帧数、总样本数、CRC 错误、序列号间隙、重同步次数
- 错误率计算：自动计算各类错误的百分比
- 时间序列图表：
  - 帧率 (FPS)
  - 错误率 (%)
  - 采样率 (Hz)
- 历史记录：保留 60 秒的历史数据
- 颜色编码：错误指标以红色/橙色高亮显示

**统计指标：**
```
总帧数：接收的总帧数
总样本数：接收的总样本点数
CRC 错误：CRC 校验失败的帧数
序列号间隙：检测到的帧丢失次数
重同步次数：帧同步丢失并重新同步的次数
短帧数：检测到的不完整帧数
```

**错误率计算：**
```
CRC 错误率 = (CRC 错误数 / 总帧数) × 100%
间隙率 = (序列号间隙数 / 总帧数) × 100%
重同步率 = (重同步次数 / 总帧数) × 100%
```

#### 3. 增强的 CRC 错误恢复
改进的错误检测和恢复策略。

**改进点：**
- 详细日志：记录 CRC 校验失败的详细信息（期望值、实际值）
- 序列号追踪：记录帧序列号间隙的大小和位置
- 重同步原因：记录触发重同步的具体原因
- 短帧检测：检测并记录不完整的帧

**错误恢复流程：**
1. 检测到 CRC 错误
2. 记录错误详情到日志
3. 尝试跳过错误字节
4. 搜索下一个同步头
5. 重新建立帧同步
6. 继续正常接收

## 新增模块

### performance.py
性能优化引擎。

**类和方法：**
```python
class PerformanceOptimizer:
    def set_fps_limit(fps: float)
    def get_fps_limit() -> float
    def get_refresh_interval_ms() -> int
    def set_enable_downsampling(enabled: bool)
    def is_downsampling_enabled() -> bool
    def set_downsample_threshold(threshold: int)
    def should_downsample(data_length: int) -> bool
    def calculate_downsample_factor(data_length: int) -> int
    def downsample_minmax(time, data, factor) -> DownsampleResult
    def prepare_render_data(time, data) -> tuple[ndarray, ndarray]

class MemoryOptimizer:
    def set_memory_limit_mb(limit_mb: float)
    def get_memory_limit_mb() -> float
    def set_auto_limit_enabled(enabled: bool)
    def calculate_max_samples() -> int
    def estimate_memory_usage(n_samples: int) -> int
    def is_within_limit(n_samples: int) -> bool
    def suggest_buffer_size(requested_samples: int) -> int
```

### logger.py
日志记录基础设施。

**类和方法：**
```python
class AppLogger:
    def debug(message, category, details)
    def info(message, category, details)
    def warning(message, category, details)
    def error(message, category, details, exc_info)
    def critical(message, category, details, exc_info)
    def log_serial_event(event_type, details)
    def log_frame_event(event_type, seq, details)
    def log_crc_error(seq, expected, received)
    def log_seq_gap(expected, received, gap)
    def log_resync(reason)
    def log_recording_event(event_type, details)
    def log_performance_warning(message, details)
    def get_events(level, category, limit) -> list[LogEvent]
    def export_events_json(filepath)
    def cleanup_old_logs(days)

# 全局函数
def get_logger() -> AppLogger
def init_logger(log_dir) -> AppLogger
```

### statistics_panel.py
统计信息可视化 UI。

**类和方法：**
```python
class StatisticsPanel(QWidget):
    def update_statistics(fps, sample_rate, frame_count, crc_errors, 
                         seq_gaps, resyncs, short_frames)
    def update_sample_count(total_samples)
    def reset_statistics()
    def apply_theme_colors(colors)
```

## 配置选项

新增配置键（settings.py）：

```python
# 性能优化
"performance/fps_limit": 30.0              # 帧率限制 (FPS)
"performance/downsample_enabled": True     # 启用降采样
"performance/downsample_threshold": 10000  # 降采样阈值（点数）
"performance/memory_limit_mb": 200.0       # 内存限制 (MB)

# 日志
"logging/retention_days": 7                # 日志保留天数
```

## 性能基准测试

### 渲染性能
```
数据集大小：100,000 点
无降采样：~200 ms/帧 (5 FPS)
有降采样：~20 ms/帧 (50 FPS)
性能提升：10x
```

### CPU 使用率
```
30 FPS 限制：CPU 使用率 ~15%
60 FPS 限制：CPU 使用率 ~25%
无限制：CPU 使用率 ~45%
降低：50%+
```

### 内存使用
```
10M 样本无限制：~20 MB
10M 样本限制 200 MB：~20 MB
100M 样本无限制：~200 MB
100M 样本限制 200 MB：~195 MB（自动限制）
```

## 使用建议

### 高速数据采集（>10 kHz）
```python
# 启用所有性能优化
optimizer.set_fps_limit(30.0)
optimizer.set_enable_downsampling(True)
optimizer.set_downsample_threshold(10000)
mem_optimizer.set_memory_limit_mb(200.0)
```

### 长时间运行
```python
# 定期清理日志
logger.cleanup_old_logs(days=7)

# 监控内存使用
if not mem_optimizer.is_within_limit(buffer_samples):
    # 减小缓冲区或停止录制
    pass
```

### 调试问题
```python
# 启用详细日志
logger.set_level(logging.DEBUG)

# 查看错误事件
errors = logger.get_events(level="ERROR")
warnings = logger.get_events(level="WARNING")

# 查看特定类别
crc_errors = logger.get_events(category="crc_error")
seq_gaps = logger.get_events(category="seq_gap")

# 导出分析
logger.export_events_json(Path("debug_log.json"))
```

## API 变更

### WaveformWidget
```python
# 新增方法
widget.set_performance_optimizer(optimizer)
widget.enable_downsampling(True)
is_enabled = widget.is_downsampling_enabled()
```

### SerialReader
```python
# 增强的日志记录
# 所有关键事件现在都会自动记录到日志系统
```

## 向后兼容性

V2.3 完全向后兼容 V2.2 和 V2.1。所有现有配置和数据格式保持不变。

## 已知限制

1. 降采样仅在数据点超过阈值时触发
2. 日志文件需要手动清理或设置自动清理
3. 统计面板历史记录限制为 60 秒
4. 内存限制仅作为建议，不强制执行

## 故障排除

### 渲染性能问题
- 启用降采样：`optimizer.set_enable_downsampling(True)`
- 降低 FPS 限制：`optimizer.set_fps_limit(20.0)`
- 减小缓冲区大小

### 内存问题
- 设置内存限制：`mem_optimizer.set_memory_limit_mb(100.0)`
- 减小缓冲区：`widget.set_max_buffer_samples(5_000_000)`
- 定期保存并清除缓冲区

### 高错误率
1. 检查统计面板查看错误模式
2. 查看日志文件获取详细信息
3. 导出日志进行分析：`logger.export_events_json(...)`
4. 检查硬件连接和波特率设置

## 下一步

查看 [ROADMAP.md](../ROADMAP.md) 了解 V2.4 和未来版本的计划功能。

## 反馈

如有问题或建议，请在 GitHub Issues 中提出：
https://github.com/X-Gen-Lab/xgen-waveform-viewer/issues

---

感谢使用 xgen-waveform-viewer！
