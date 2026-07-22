# xgen-waveform-viewer V2.2 Release Notes

**Release Date:** 2024-12-21  
**Version:** 2.2.0

## 🎯 Overview

V2.2 "Data Analysis Tools" 带来了专业级的数据分析功能，使 xgen-waveform-viewer 从简单的波形查看工具升级为强大的信号分析平台。本版本新增测量工具、触发功能和录制增强三大模块，显著提升了数据采集和分析的能力。

---

## ✨ New Features

### 📏 测量工具 (Measurement Tools)

#### 1. 可拖动标尺 (Draggable Ruler)
- **功能**：在波形上放置两条可拖动的垂直线，实时测量时间间隔和幅值差
- **快捷键**：`M` - 显示/隐藏标尺
- **显示内容**：
  - Δt: 时间间隔 (ms)
  - f: 频率 (Hz)
  - ΔV: 幅值差

#### 2. 自动峰值检测 (Peak Detection)
- **功能**：自动识别并标注波形的正负峰值点
- **快捷键**：`P` - 执行峰值检测
- **可配置参数**：
  - 阈值 (相对于数据范围的比例)
  - 最小峰值间距
- **可视化**：
  - 正峰：红色向上三角形 ▲
  - 负峰：绿色向下三角形 ▼

#### 3. 统计值计算 (Statistical Measurements)
实时计算并显示选定区域的统计特性：
- **Mean**: 平均值
- **RMS**: 均方根值
- **Min/Max**: 最小/最大值
- **Vpp**: 峰峰值 (Peak-to-Peak)
- **Frequency**: 频率（基于峰值间隔）
- **Period**: 周期

#### 4. 测量结果面板
- 集中显示所有测量结果
- 实时更新（标尺移动时）
- 一键清除所有标记

---

### ⚡ 触发功能 (Trigger System)

#### 1. 触发模式 (Trigger Modes)
- **Disabled**: 禁用触发
- **Auto**: 自动连续触发
- **Normal**: 满足条件时触发
- **Single**: 单次触发模式（触发一次后停止）

#### 2. 触发类型 (Trigger Types)
- **Rising Edge** (上升沿): 信号从低到高穿越阈值
- **Falling Edge** (下降沿): 信号从高到低穿越阈值
- **Both Edges** (双边沿): 任意方向穿越阈值
- **Level High** (高电平): 信号高于阈值
- **Level Low** (低电平): 信号低于阈值

#### 3. 触发参数
- **Threshold**: 触发阈值 (ADC 值, 0-4095)
- **Hysteresis**: 滞回值，防止抖动触发
- **Pre-trigger**: 触发前保留的采样点数

#### 4. 单次触发工作流
1. 配置触发条件（类型、阈值）
2. 点击 "Arm Single Trigger" 或按 `T` 键
3. 等待触发条件满足
4. 触发后自动停止，可查看触发点信息

#### 5. 触发指示
- 状态栏实时显示触发状态
- 触发事件包含：触发时间、触发值、触发类型
- 触发点可视化标记（可选）

---

### 🎬 录制增强 (Recording Enhancements)

#### 1. 暂停/恢复录制 (Pause/Resume)
- **功能**：录制过程中可随时暂停和恢复
- **快捷键**：`Ctrl+P` - 暂停/恢复录制
- **用途**：
  - 跳过无关数据段
  - 临时停止录制查看实时波形
  - 节省存储空间
- **统计**：自动记录暂停次数和总暂停时长

#### 2. 自动分段录制 (Auto-Segmentation)
自动将长时间录制分割为多个文件，防止单文件过大：

**按时间分段**：
- 配置参数：`record/auto_segment_duration` (秒)
- 示例：设置为 300 秒（5 分钟），每 5 分钟创建新文件

**按大小分段**：
- 配置参数：`record/auto_segment_size` (MB)
- 示例：设置为 100 MB，文件达到 100 MB 时创建新文件

**分段文件命名**：
```
adc_record_20241221_143025.bin         # 原始文件
adc_record_20241221_143025_part001.bin # 第 1 个分段
adc_record_20241221_143025_part002.bin # 第 2 个分段
```

#### 3. 实时录制预览 (Live Recording Preview)
状态栏实时显示录制信息：
- **时长**: 录制已持续时间 (秒/分/小时)
- **文件大小**: 当前文件大小 (KB/MB/GB)
- **帧数**: 已录制帧数和采样点数
- **分段索引**: 当前所在分段（分段录制时）
- **暂停状态**: [PAUSED] 指示

示例：
```
REC [BIN]: 125.3s | 45.2MB | 3127 frames
REC [BIN]: 67.8s | 22.1MB | 1695 frames [PAUSED]
REC [BIN]: 328.9s | 112.7MB | 8219 frames (Seg 1)
```

#### 4. 录制统计增强
新增统计字段（保存到 `.meta.json`）：
- `paused`: 是否暂停过
- `pause_count`: 暂停次数
- `total_pause_duration`: 总暂停时长
- `file_size_bytes`: 文件大小
- `segment_index`: 分段索引

---

## 🎨 User Interface Changes

### 1. 侧边工具面板
新增可折叠的右侧工具面板，包含两个标签页：
- **📏 Measurement**: 测量工具控制和结果显示
- **⚡ Trigger**: 触发功能配置和状态

面板特性：
- 可调整宽度（分割器）
- 默认宽度 300-400 像素
- 不影响原有波形显示区域

### 2. 测量控制按钮
- **Ruler**: 显示/隐藏标尺（可选中状态）
- **Find Peaks**: 执行峰值检测
- **Clear**: 清除所有测量标记

### 3. 录制控制增强
工具栏新增按钮：
- **Pause/Resume**: 暂停/恢复录制按钮
  - 录制时启用
  - 暂停时文本显示 "Resume"
  - 恢复时文本显示 "Pause"

---

## ⌨️ New Keyboard Shortcuts

| 快捷键 | 功能 | 说明 |
|--------|------|------|
| `M` | Toggle Ruler | 显示/隐藏测量标尺 |
| `P` | Detect Peaks | 执行峰值检测 |
| `T` | Arm Trigger | 准备单次触发（需启用触发功能） |
| `Ctrl+P` | Pause/Resume | 暂停/恢复录制（录制时可用） |

---

## 🔧 Technical Details

### 新增模块

#### 1. `measurement_tools.py`
核心类：
- `Ruler`: 可拖动标尺，实时测量时间和幅值
- `PeakMarker`: 峰值标记器，可视化峰值点
- `MeasurementPanel`: 测量结果显示面板
- `MeasurementEngine`: 测量计算引擎（静态方法）
- `MeasurementResult`: 测量结果数据类

关键算法：
- `detect_peaks()`: 基于局部极值的峰值检测算法
- `calculate_statistics()`: 统计值计算（Mean, RMS, Min, Max, Vpp）
- `calculate_frequency()`: 基于峰值间隔的频率计算

#### 2. `trigger.py`
核心类：
- `TriggerDetector`: 触发检测器，实时监测触发条件
- `TriggerPanel`: 触发控制面板 UI
- `TriggerConfig`: 触发配置数据类
- `TriggerEvent`: 触发事件数据类

枚举类：
- `TriggerMode`: 触发模式（Disabled, Auto, Normal, Single）
- `TriggerType`: 触发类型（上升沿、下降沿、双边沿、电平）

触发检测流程：
1. 逐采样点处理 (`process_sample()`)
2. 检查触发条件（边沿/电平 + 阈值 + 滞回）
3. 满足条件时发射 `trigger_fired` 信号
4. 单次模式下记录触发状态

#### 3. `recorder.py` 增强
新增功能：
- `pause()`: 暂停录制，刷新缓冲区
- `resume()`: 恢复录制
- `is_paused()`: 查询暂停状态
- `get_preview()`: 获取实时录制预览信息
- `_should_create_segment()`: 检查是否需要分段
- `_create_new_segment()`: 创建新分段文件

新增内部信号：
- `_PAUSE`: 暂停命令（队列消息）
- `_RESUME`: 恢复命令（队列消息）

### API Changes

#### 1. `FrameRecorder` 构造函数
```python
FrameRecorder(
    path: str | Path,
    record_format: RecordFormat,
    sample_rate_hz: int = ADC_SAMPLE_RATE_HZ,
    queue_size: int = 8192,
    auto_segment_duration: float = 0.0,  # 新增：按时间分段(秒)
    auto_segment_size: int = 0,          # 新增：按大小分段(MB)
)
```

#### 2. `RecorderStats` 新增字段
```python
paused: bool = False                     # 是否暂停
pause_count: int = 0                     # 暂停次数
total_pause_duration: float = 0.0        # 总暂停时长
file_size_bytes: int = 0                 # 文件大小
segment_index: int = 0                   # 分段索引
```

#### 3. 新增便捷属性
```python
@property
def duration_display(self) -> str:
    """格式化显示时长：1.5s, 2.3min, 1.2h"""

@property
def file_size_display(self) -> str:
    """格式化显示文件大小：123B, 45.2KB, 12.3MB"""
```

---

## 📦 Dependencies

无新增依赖，所有功能基于现有库实现：
- PyQt6 (UI 组件)
- pyqtgraph (绘图和标记)
- numpy (数值计算)

---

## ⚙️ Configuration

### 新增配置项

```python
# 测量工具
"measurement/ruler_enabled": bool        # 启动时是否显示标尺
"measurement/peak_threshold": float      # 峰值检测阈值 (0.0-1.0)
"measurement/peak_min_distance": int     # 峰值最小间距 (采样点)

# 触发功能
"trigger/enabled": bool                  # 启动时是否启用触发
"trigger/mode": str                      # 触发模式 (Disabled/Auto/Normal/Single)
"trigger/type": str                      # 触发类型 (Rising/Falling/Both/LevelHigh/LevelLow)
"trigger/threshold": float               # 触发阈值 (ADC 值)
"trigger/hysteresis": float              # 滞回值
"trigger/pre_trigger_samples": int       # 预触发采样点数

# 录制增强
"record/auto_segment_duration": float    # 自动分段时长 (秒, 0=禁用)
"record/auto_segment_size": int          # 自动分段大小 (MB, 0=禁用)
```

---

## 🐛 Bug Fixes

- 修复了长时间录制可能导致的内存泄漏问题
- 优化了峰值检测算法的边界情况处理
- 修复了标尺拖动时的性能问题

---

## 🚀 Performance Improvements

- 测量值更新频率优化到 100ms，避免过度刷新
- 峰值检测使用向量化操作，提升大数据集处理速度
- 录制预览使用非阻塞方式获取文件大小

---

## 📖 Usage Examples

### 示例 1：频率测量

1. 连接设备，开始采集正弦波信号
2. 按 `M` 键显示标尺
3. 拖动两条标尺线对齐相邻两个波峰
4. 查看测量面板显示的频率值

### 示例 2：峰值分析

1. 采集包含脉冲信号的数据
2. 按 `P` 键执行峰值检测
3. 查看波形上的峰值标记
4. 测量面板显示正负峰值数量和统计信息

### 示例 3：触发捕获瞬态信号

1. 打开 "⚡ Trigger" 标签页
2. 启用触发功能，选择 "Single" 模式
3. 设置触发类型为 "Rising Edge"，阈值为 2500
4. 点击 "Arm Single Trigger" 或按 `T` 键
5. 等待信号满足条件，自动触发并停止
6. 查看触发点信息和波形

### 示例 4：长时间录制与分段

1. 打开设置，配置自动分段参数：
   ```python
   record/auto_segment_duration = 300  # 每 5 分钟分段
   record/auto_segment_size = 100      # 或每 100 MB 分段
   ```
2. 开始录制
3. 录制过程中可暂停/恢复（`Ctrl+P`）
4. 查看状态栏实时预览录制信息
5. 停止录制后，检查生成的多个分段文件

---

## 📝 Notes

1. **测量工具**：
   - 标尺位置会随着波形滚动自动更新（自动滚动模式）
   - 峰值检测仅对当前可见数据生效
   - 测量结果精度取决于采样率

2. **触发功能**：
   - 触发检测是实时的，每个采样点都会检查
   - 单次触发后需要重新 Arm 才能再次触发
   - 滞回参数建议设置为信号噪声的 2-3 倍

3. **录制增强**：
   - 暂停录制时，数据队列会被刷新到磁盘
   - 分段录制的每个文件都包含独立的元数据
   - 自动分段不会中断数据完整性

---

## 🔮 What's Next

V2.2 完成了数据分析工具的基础建设。接下来的 V2.3 将聚焦于性能优化和稳定性提升：

### V2.3 - Performance & Stability (Q2 2025)
- 分段 min/max 降采样算法
- 高采样率（>10kHz）渲染优化
- 增强 CRC 错误恢复策略
- 大数据量内存优化

---

## 🙏 Acknowledgments

感谢所有提供反馈和建议的用户！

V2.2 的功能设计参考了专业示波器和信号分析仪的用户体验，致力于为嵌入式开发者提供高效、易用的波形分析工具。

---

**Full Changelog**: [V2.1...V2.2](https://github.com/X-Gen-Lab/xgen-waveform-viewer/compare/v2.1.0...v2.2.0)
