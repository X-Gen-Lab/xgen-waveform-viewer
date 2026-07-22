# xgen-waveform-viewer V2.4 发布说明

**发布日期**: 2025-01-XX  
**版本**: 2.4.0

## 🎉 新增功能

### 📼 数据回放
V2.4 引入了完整的数据回放功能，让您可以重播之前录制的波形数据：

- **多格式支持**: 支持回放 BIN 和 CSV 格式的录制文件
- **变速播放**: 支持 0.1x ~ 10x 的播放速度调节
- **进度控制**: 可视化的播放进度条和时间显示
- **播放控制**: 支持播放、暂停、停止、恢复等完整控制
- **独立面板**: 回放控制面板可独立显示，不干扰主界面

#### 使用方法
1. 点击菜单 `File` → `Playback Recording...` 打开回放面板
2. 点击"打开文件..."选择录制文件
3. 调整播放速度（可选）
4. 点击"播放"开始回放
5. 使用暂停/停止控制回放过程

### 🎨 高级导出功能
新增多种专业的数据导出格式：

#### PNG/SVG 图片导出
- 导出当前可见波形为 PNG 位图（1920x1080）
- 导出为 SVG 矢量图，支持无损缩放
- 适用于报告、演示文稿和论文

#### MATLAB 格式支持 (.mat)
```python
# 导出的 .mat 文件包含：
- samples: 采样数据数组
- time: 时间数组
- sample_rate_hz: 采样率
- export_time: 导出时间戳
```
需要安装: `pip install scipy`

#### HDF5 高效存储 (.h5)
- 采用 gzip 压缩，大幅减少文件大小
- 支持大数据量高效存储
- 完整保存元数据和采样信息
- 科学计算领域的标准格式

需要安装: `pip install h5py`

#### HTML 统计报告
- 自动生成美观的 HTML 统计报告
- 包含波形预览图片
- 显示关键统计指标：平均值、RMS、峰峰值等
- 适合存档和分享

### 📊 波形比较工具
新增波形比较功能，可以对比两个波形的统计特性：

- 样本统计对比（均值、标准差、最大最小值）
- 差异计算（MSE、MAE、最大差异）
- 相关性分析

## 🔧 技术改进

### 新增依赖
- **PyQt6-SVG**: SVG 导出支持
- **scipy** (可选): MATLAB 格式导出
- **h5py** (可选): HDF5 格式支持

### 架构优化
- 新增 `playback.py`: 回放引擎核心模块
- 新增 `playback_panel.py`: 回放 UI 控制面板
- 新增 `exporter.py`: 统一的导出功能模块
- 主窗口集成回放和导出菜单

## 📝 使用示例

### 回放录制文件
```
1. 录制一段波形数据（Record）
2. 打开 File → Playback Recording...
3. 选择录制的 .bin 或 .csv 文件
4. 调整播放速度，点击播放
```

### 导出为 MATLAB 格式
```python
# 在 MATLAB 中加载：
data = load('waveform_20250122_143052.mat');
plot(data.time, data.samples);
xlabel('Time (s)');
ylabel('ADC Value');
title(sprintf('Sample Rate: %d Hz', data.sample_rate_hz));
```

### 导出为 HDF5
```python
# 在 Python 中加载：
import h5py
import numpy as np

with h5py.File('waveform_20250122_143052.h5', 'r') as f:
    samples = f['samples'][:]
    sample_rate = f.attrs['sample_rate_hz']
    time = np.arange(len(samples)) / sample_rate
```

### 生成统计报告
```
1. 在主界面查看需要的波形
2. File → Export As → Export Report (HTML)...
3. 选择保存位置
4. 自动生成 HTML 报告和波形图片
```

## 🚀 快捷键

新增快捷键：
- `Ctrl+P`: 打开回放面板

已有快捷键：
- `Ctrl+S`: 保存缓冲区
- `Ctrl+E`: 导出 CSV
- `Ctrl+Q`: 退出程序
- `Space`: 恢复自动滚动
- `C`: 连接/断开串口
- `R`: 开始/停止录制
- `F`: 显示全部缓冲区
- `Y`: 切换 Y 轴模式
- `+/-`: X 轴缩放

## 🔄 版本对比

| 功能 | V2.3 | V2.4 |
|------|------|------|
| 实时采集 | ✅ | ✅ |
| 数据录制 | ✅ | ✅ |
| 测量工具 | ✅ | ✅ |
| 触发功能 | ✅ | ✅ |
| 性能优化 | ✅ | ✅ |
| **数据回放** | ❌ | ✅ |
| **变速播放** | ❌ | ✅ |
| **PNG/SVG导出** | ❌ | ✅ |
| **MATLAB格式** | ❌ | ✅ |
| **HDF5格式** | ❌ | ✅ |
| **HTML报告** | ❌ | ✅ |
| **波形比较** | ❌ | ✅ |

## 📦 安装说明

### 基础安装
```bash
pip install xgen-waveform-viewer==2.4.0
```

### 完整功能安装（包含可选依赖）
```bash
pip install "xgen-waveform-viewer[full]==2.4.0"
```

或手动安装可选依赖：
```bash
pip install scipy h5py
```

## ⚠️ 已知限制

1. **回放性能**: 大文件（>100MB）回放时可能占用较多内存
2. **图片导出**: PNG/SVG 导出仅包含当前可见区域
3. **MATLAB/HDF5**: 需要额外安装 scipy 和 h5py

## 🔮 下一版本预告 (V3.0)

- 多通道支持
- 自定义帧格式配置
- TCP/UDP 数据源
- 固件配置界面

## 🐛 Bug 修复

V2.4.0:
- 修复回放大文件时的内存泄漏问题
- 修复 SVG 导出在某些主题下的渲染问题
- 优化导出进度显示

## 💬 反馈

如有问题或建议，请访问：
- GitHub Issues: https://github.com/X-Gen-Lab/xgen-waveform-viewer/issues
- 讨论区: https://github.com/X-Gen-Lab/xgen-waveform-viewer/discussions

---

感谢使用 xgen-waveform-viewer！
