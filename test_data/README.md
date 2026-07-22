# 测试数据说明

本目录包含用于回放功能测试的各种波形数据文件。

## 数据格式

### BIN 格式 (二进制格式)

**文件结构：**

```
[文件头 24 bytes]
magic         : 4 bytes  - 魔数 'XGEN' (0x5847454E)
version       : 4 bytes  - 版本号 (uint32, 当前为 1)
frame_count   : 4 bytes  - 总帧数 (uint32)
sample_rate   : 4 bytes  - 采样率 Hz (uint32)
segment_idx   : 4 bytes  - 段索引 (uint32)
timestamp     : 8 bytes  - 时间戳毫秒 (int64)

[数据帧] (重复 frame_count 次)
seq           : 4 bytes  - 帧序号 (uint32)
count         : 2 bytes  - 本帧采样点数 (uint16, 最大 4096)
samples       : count * 2 bytes - ADC 数据 (uint16 array)
```

**特点：**
- 紧凑的二进制存储，占用空间小
- 每帧最多支持 4096 个采样点
- 支持快速随机访问
- 包含完整的元数据信息

**示例代码（Python 读取）：**
```python
import struct
import numpy as np

with open('sine_100hz.bin', 'rb') as f:
    # 读取文件头
    header = f.read(24)
    magic, version, frame_count, sample_rate, segment_idx, timestamp = \
        struct.unpack('<4sIIIIq', header)
    
    print(f"采样率: {sample_rate} Hz")
    print(f"总帧数: {frame_count}")
    
    # 读取数据帧
    all_samples = []
    for _ in range(frame_count):
        seq, count = struct.unpack('<IH', f.read(6))
        samples = np.frombuffer(f.read(count * 2), dtype=np.uint16)
        all_samples.extend(samples)
    
    print(f"总采样点: {len(all_samples)}")
```

### CSV 格式 (文本格式)

**文件结构：**

```
# sample_rate=10000Hz
# timestamp=2024-01-01 12:00:00
# total_samples=20000
# seq,index,adc_value
0,0,2048
0,1,2100
0,2,2150
...
1,0,2200
1,1,2250
...
```

**字段说明：**
- `seq`: 帧序号 (从 0 开始递增)
- `index`: 帧内采样点索引 (每帧从 0 开始)
- `adc_value`: ADC 采样值 (0-4095，对应 12-bit ADC)

**特点：**
- 人类可读，便于调试和分析
- 可用 Excel、文本编辑器直接打开
- 占用空间较大（约为 BIN 格式的 6 倍）
- 支持任意文本处理工具

**示例代码（Python 读取）：**
```python
import pandas as pd

# 读取 CSV 文件
df = pd.read_csv('sine_100hz.csv', comment='#', names=['seq', 'index', 'adc_value'])

# 提取采样率（从注释中）
with open('sine_100hz.csv', 'r') as f:
    for line in f:
        if line.startswith('# sample_rate='):
            sample_rate = int(line.split('=')[1].replace('Hz', ''))
            break

print(f"采样率: {sample_rate} Hz")
print(f"总采样点: {len(df)}")

# 获取所有 ADC 值
samples = df['adc_value'].values
```

## 测试文件列表

### 1. 纯正弦波 (100Hz)
- **文件名**: `sine_100hz.bin` / `sine_100hz.csv`
- **信号类型**: 单频正弦波
- **频率**: 100 Hz
- **幅值**: ±1000 ADC 单位
- **中心值**: 2048 (12-bit ADC 中点)
- **噪声**: 5 ADC 单位 RMS
- **用途**: 基本正弦波形测试，频率分析验证

### 2. 多频率叠加 (50Hz + 150Hz + 300Hz)
- **文件名**: `multi_frequency.bin` / `multi_frequency.csv`
- **信号类型**: 多频率复合信号
- **频率成分**:
  - 50 Hz (幅值 500)
  - 150 Hz (幅值 300)
  - 300 Hz (幅值 200)
- **噪声**: 10 ADC 单位 RMS
- **用途**: 频谱分析测试，多频检测验证

### 3. 方波信号 (50Hz)
- **文件名**: `square_50hz.bin` / `square_50hz.csv`
- **信号类型**: 方波
- **频率**: 50 Hz
- **幅值**: ±1000 ADC 单位
- **占空比**: 50%
- **噪声**: 10 ADC 单位 RMS
- **用途**: 边沿检测测试，脉冲响应分析

### 4. 锯齿波信号 (50Hz)
- **文件名**: `sawtooth_50hz.bin` / `sawtooth_50hz.csv`
- **信号类型**: 锯齿波
- **频率**: 50 Hz
- **幅值**: ±1500 ADC 单位
- **斜率**: 线性上升，瞬间下降
- **噪声**: 10 ADC 单位 RMS
- **用途**: 线性度测试，斜率分析

### 5. 随机噪声
- **文件名**: `noise.bin` / `noise.csv`
- **信号类型**: 高斯白噪声
- **均值**: 2048
- **标准差**: 500 ADC 单位
- **范围**: 0-4095 (裁剪)
- **用途**: 噪声分析，统计特性验证

### 6. 脉冲串信号
- **文件名**: `pulse_train.bin` / `pulse_train.csv`
- **信号类型**: 周期性脉冲
- **脉冲间隔**: 1000 采样点 (100ms @ 10kHz)
- **脉冲宽度**: 50 采样点 (5ms)
- **脉冲幅值**: 1500 ADC 单位
- **基准值**: 2048
- **噪声**: 10 ADC 单位 RMS
- **用途**: 触发功能测试，脉冲检测

### 7. 长时间正弦波 (60Hz, 10秒)
- **文件名**: `long_sine_60hz.bin`
- **信号类型**: 单频正弦波
- **频率**: 60 Hz
- **时长**: 10 秒
- **总采样点**: 100,000
- **噪声**: 5 ADC 单位 RMS
- **用途**: 性能测试，长时间回放验证

## 采样参数

所有测试文件使用统一的采样参数：
- **采样率**: 10,000 Hz (10 kHz)
- **ADC 分辨率**: 12-bit (0-4095)
- **数据类型**: uint16
- **短时长文件**: 2 秒 (20,000 采样点)
- **长时长文件**: 10 秒 (100,000 采样点)

## 使用方法

### 在 xgen-waveform-viewer 中使用

1. 启动程序: `python -m xgen_waveform_viewer`
2. 切换到 **"回放"** 标签页
3. 点击 **"选择文件"** 按钮
4. 选择本目录下的任意 `.bin` 或 `.csv` 文件
5. 点击 **"播放"** 按钮开始回放

### 回放控制

- **播放/暂停**: 点击播放按钮
- **停止**: 点击停止按钮
- **变速**: 调整速度滑块 (0.1x ~ 10x)
- **进度**: 拖动进度条快速定位

### 编程方式使用

```python
from xgen_waveform_viewer.playback import PlaybackReader
import numpy as np

# 创建回放读取器
reader = PlaybackReader()

# 加载文件
info = reader.load_file('test_data/sine_100hz.bin')

print(f"采样率: {info.sample_rate_hz} Hz")
print(f"时长: {info.duration_s:.2f} 秒")
print(f"总采样点: {info.total_samples:,}")

# 设置回放速度 (可选)
reader.set_speed(2.0)  # 2倍速

# 连接信号
reader.frame_ready.connect(lambda samples, seq: print(f"帧 {seq}: {len(samples)} 个采样点"))
reader.progress_updated.connect(lambda progress: print(f"进度: {progress:.1f}%"))
reader.playback_finished.connect(lambda: print("回放完成"))

# 开始回放
reader.start()

# 暂停/恢复
# reader.pause()
# reader.resume()

# 停止回放
# reader.stop()
```

## 文件大小对比

| 文件名 | BIN 大小 | CSV 大小 | 压缩比 |
|--------|----------|----------|--------|
| sine_100hz | 39.3 KB | 244.8 KB | 6.2x |
| multi_frequency | 39.3 KB | 244.8 KB | 6.2x |
| square_50hz | 39.3 KB | 244.8 KB | 6.2x |
| sawtooth_50hz | 39.3 KB | 241.8 KB | 6.2x |
| noise | 39.3 KB | 244.4 KB | 6.2x |
| pulse_train | 39.3 KB | 244.8 KB | 6.2x |
| long_sine_60hz | 196.5 KB | ~1.2 MB* | 6.1x |

\* CSV 文件未生成，估算值

**建议**:
- 存储和传输使用 BIN 格式（占用空间小）
- 调试和分析使用 CSV 格式（可读性好）

## 重新生成测试数据

如需重新生成测试数据：

```bash
cd examples
python generate_test_data.py
```

生成的文件将保存到 `test_data/` 目录。

## 数据验证

### 验证 BIN 文件完整性

```python
import struct

def verify_bin_file(filepath):
    with open(filepath, 'rb') as f:
        # 读取文件头
        header = f.read(24)
        magic, version, frame_count, sample_rate, _, _ = \
            struct.unpack('<4sIIIIq', header)
        
        if magic != b'XGEN':
            print("❌ 魔数错误")
            return False
        
        if version != 1:
            print("❌ 版本不支持")
            return False
        
        # 验证帧数据
        actual_frames = 0
        total_samples = 0
        
        while True:
            frame_header = f.read(6)
            if len(frame_header) < 6:
                break
            
            seq, count = struct.unpack('<IH', frame_header)
            
            if count > 4096:
                print(f"❌ 帧 {seq} 采样点数异常: {count}")
                return False
            
            f.seek(count * 2, 1)  # 跳过数据
            actual_frames += 1
            total_samples += count
        
        if actual_frames != frame_count:
            print(f"⚠️  实际帧数 ({actual_frames}) 与声明不一致 ({frame_count})")
        
        print(f"✅ 验证通过")
        print(f"   采样率: {sample_rate} Hz")
        print(f"   总帧数: {actual_frames}")
        print(f"   总采样点: {total_samples:,}")
        print(f"   时长: {total_samples / sample_rate:.2f} 秒")
        
        return True

# 验证所有 BIN 文件
import glob
for bin_file in glob.glob('*.bin'):
    print(f"\n验证文件: {bin_file}")
    verify_bin_file(bin_file)
```

## 技术支持

如有问题或建议，请访问项目主页提交 Issue。
