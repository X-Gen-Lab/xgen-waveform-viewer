"""
生成测试数据用于回放功能测试

生成多种测试波形:
1. 纯正弦波 (100Hz)
2. 多频率叠加 (50Hz + 150Hz + 300Hz)
3. 方波信号
4. 锯齿波信号
5. 随机噪声

每种波形导出为 BIN 和 CSV 两种格式
"""

import struct
import numpy as np
from pathlib import Path
from datetime import datetime


# 常量定义（与 config.py 保持一致）
BIN_MAGIC = b'XGEN'
BIN_VERSION = 1
MAX_FRAME_SAMPLES = 4096


def write_bin_file(filepath: str, samples: np.ndarray, sample_rate_hz: int):
    """
    写入 BIN 格式文件
    
    BIN 文件格式:
    - 文件头 (24 bytes):
      - magic: 4 bytes (b'XGEN')
      - version: 4 bytes (uint32)
      - frame_count: 4 bytes (uint32)
      - sample_rate: 4 bytes (uint32)
      - segment_idx: 4 bytes (uint32)
      - timestamp: 8 bytes (int64)
    
    - 数据帧 (重复):
      - seq: 4 bytes (uint32) - 帧序号
      - count: 2 bytes (uint16) - 本帧采样点数
      - samples: count * 2 bytes (uint16 array) - ADC 数据
    """
    # 将数据分帧（每帧最多 512 个采样点）
    frame_size = 512
    frames = []
    
    for i in range(0, len(samples), frame_size):
        frame_samples = samples[i:i+frame_size]
        frames.append(frame_samples)
    
    # 写入文件
    with open(filepath, 'wb') as f:
        # 写入文件头
        timestamp = int(datetime.now().timestamp() * 1000)  # 毫秒时间戳
        header = struct.pack(
            '<4sIIIIq',
            BIN_MAGIC,           # magic
            BIN_VERSION,         # version
            len(frames),         # frame_count
            sample_rate_hz,      # sample_rate
            0,                   # segment_idx
            timestamp            # timestamp
        )
        f.write(header)
        
        # 写入数据帧
        for seq, frame_samples in enumerate(frames):
            # 帧头
            frame_header = struct.pack('<IH', seq, len(frame_samples))
            f.write(frame_header)
            
            # 采样数据
            frame_data = frame_samples.astype(np.uint16).tobytes()
            f.write(frame_data)
    
    print(f"✓ 已生成 BIN 文件: {filepath}")
    print(f"  总采样点: {len(samples):,}")
    print(f"  总帧数: {len(frames)}")
    print(f"  采样率: {sample_rate_hz} Hz")
    print(f"  时长: {len(samples) / sample_rate_hz:.2f} 秒")
    print(f"  文件大小: {Path(filepath).stat().st_size / 1024:.1f} KB")


def write_csv_file(filepath: str, samples: np.ndarray, sample_rate_hz: int):
    """
    写入 CSV 格式文件
    
    CSV 文件格式:
    - 文件头 (注释行):
      # sample_rate=XXXHz
      # timestamp=YYYY-MM-DD HH:MM:SS
      # total_samples=NNNN
    
    - 数据行:
      seq,index,adc_value
      0,0,2048
      0,1,2100
      ...
    """
    # 将数据分帧（每帧最多 512 个采样点）
    frame_size = 512
    
    lines = []
    
    # 写入文件头
    lines.append(f"# sample_rate={sample_rate_hz}Hz")
    lines.append(f"# timestamp={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"# total_samples={len(samples)}")
    lines.append("# seq,index,adc_value")
    
    # 写入数据行
    seq = 0
    for i in range(0, len(samples), frame_size):
        frame_samples = samples[i:i+frame_size]
        for idx, value in enumerate(frame_samples):
            lines.append(f"{seq},{idx},{int(value)}")
        seq += 1
    
    # 保存文件
    Path(filepath).write_text('\n'.join(lines), encoding='utf-8')
    
    print(f"✓ 已生成 CSV 文件: {filepath}")
    print(f"  总采样点: {len(samples):,}")
    print(f"  总帧数: {seq}")
    print(f"  采样率: {sample_rate_hz} Hz")
    print(f"  时长: {len(samples) / sample_rate_hz:.2f} 秒")
    print(f"  文件大小: {Path(filepath).stat().st_size / 1024:.1f} KB")


def generate_sine_wave(sample_rate: int = 10000, duration: float = 2.0, frequency: float = 100.0):
    """生成纯正弦波"""
    num_samples = int(sample_rate * duration)
    t = np.arange(num_samples) / sample_rate
    
    # ADC 中心值 2048 (12-bit ADC: 0-4095)
    # 幅值 1000
    samples = 2048 + 1000 * np.sin(2 * np.pi * frequency * t)
    
    # 添加小噪声使其更真实
    samples += np.random.randn(num_samples) * 5
    
    # 限制范围并转换为 uint16
    samples = np.clip(samples, 0, 4095).astype(np.uint16)
    
    return samples


def generate_multi_frequency(sample_rate: int = 10000, duration: float = 2.0):
    """生成多频率叠加波形"""
    num_samples = int(sample_rate * duration)
    t = np.arange(num_samples) / sample_rate
    
    # 叠加多个频率分量
    samples = 2048.0
    samples += 500 * np.sin(2 * np.pi * 50 * t)    # 50Hz
    samples += 300 * np.sin(2 * np.pi * 150 * t)   # 150Hz
    samples += 200 * np.sin(2 * np.pi * 300 * t)   # 300Hz
    
    # 添加噪声
    samples += np.random.randn(num_samples) * 10
    
    # 限制范围并转换为 uint16
    samples = np.clip(samples, 0, 4095).astype(np.uint16)
    
    return samples


def generate_square_wave(sample_rate: int = 10000, duration: float = 2.0, frequency: float = 50.0):
    """生成方波信号"""
    num_samples = int(sample_rate * duration)
    t = np.arange(num_samples) / sample_rate
    
    # 使用正弦波的符号函数生成方波
    square = np.sign(np.sin(2 * np.pi * frequency * t))
    samples = 2048 + 1000 * square
    
    # 添加噪声
    samples += np.random.randn(num_samples) * 10
    
    # 限制范围并转换为 uint16
    samples = np.clip(samples, 0, 4095).astype(np.uint16)
    
    return samples


def generate_sawtooth_wave(sample_rate: int = 10000, duration: float = 2.0, frequency: float = 50.0):
    """生成锯齿波信号"""
    num_samples = int(sample_rate * duration)
    t = np.arange(num_samples) / sample_rate
    
    # 生成锯齿波 (0 到 1 的线性增长)
    phase = (t * frequency) % 1.0
    samples = 2048 + 1500 * (2 * phase - 1)
    
    # 添加噪声
    samples += np.random.randn(num_samples) * 10
    
    # 限制范围并转换为 uint16
    samples = np.clip(samples, 0, 4095).astype(np.uint16)
    
    return samples


def generate_noise(sample_rate: int = 10000, duration: float = 2.0):
    """生成随机噪声"""
    num_samples = int(sample_rate * duration)
    
    # 高斯噪声，均值 2048，标准差 500
    samples = 2048 + np.random.randn(num_samples) * 500
    
    # 限制范围并转换为 uint16
    samples = np.clip(samples, 0, 4095).astype(np.uint16)
    
    return samples


def generate_pulse_train(sample_rate: int = 10000, duration: float = 2.0):
    """生成脉冲串信号"""
    num_samples = int(sample_rate * duration)
    samples = np.ones(num_samples) * 2048  # 基准值
    
    # 每 1000 个采样点添加一个脉冲
    pulse_interval = 1000
    pulse_width = 50
    pulse_amplitude = 1500
    
    for i in range(0, num_samples, pulse_interval):
        end = min(i + pulse_width, num_samples)
        samples[i:end] = 2048 + pulse_amplitude
    
    # 添加噪声
    samples += np.random.randn(num_samples) * 10
    
    # 限制范围并转换为 uint16
    samples = np.clip(samples, 0, 4095).astype(np.uint16)
    
    return samples


def main():
    """生成所有测试数据"""
    print("\n" + "="*60)
    print("生成回放测试数据")
    print("="*60 + "\n")
    
    # 创建输出目录
    output_dir = Path("test_data")
    output_dir.mkdir(exist_ok=True)
    
    # 测试参数
    sample_rate = 10000  # 10kHz
    duration = 2.0       # 2秒
    
    # 1. 纯正弦波 (100Hz)
    print("\n[1] 生成纯正弦波 (100Hz)...")
    samples = generate_sine_wave(sample_rate, duration, frequency=100.0)
    write_bin_file(str(output_dir / "sine_100hz.bin"), samples, sample_rate)
    write_csv_file(str(output_dir / "sine_100hz.csv"), samples, sample_rate)
    
    # 2. 多频率叠加
    print("\n[2] 生成多频率叠加波形 (50Hz + 150Hz + 300Hz)...")
    samples = generate_multi_frequency(sample_rate, duration)
    write_bin_file(str(output_dir / "multi_frequency.bin"), samples, sample_rate)
    write_csv_file(str(output_dir / "multi_frequency.csv"), samples, sample_rate)
    
    # 3. 方波信号
    print("\n[3] 生成方波信号 (50Hz)...")
    samples = generate_square_wave(sample_rate, duration, frequency=50.0)
    write_bin_file(str(output_dir / "square_50hz.bin"), samples, sample_rate)
    write_csv_file(str(output_dir / "square_50hz.csv"), samples, sample_rate)
    
    # 4. 锯齿波信号
    print("\n[4] 生成锯齿波信号 (50Hz)...")
    samples = generate_sawtooth_wave(sample_rate, duration, frequency=50.0)
    write_bin_file(str(output_dir / "sawtooth_50hz.bin"), samples, sample_rate)
    write_csv_file(str(output_dir / "sawtooth_50hz.csv"), samples, sample_rate)
    
    # 5. 随机噪声
    print("\n[5] 生成随机噪声...")
    samples = generate_noise(sample_rate, duration)
    write_bin_file(str(output_dir / "noise.bin"), samples, sample_rate)
    write_csv_file(str(output_dir / "noise.csv"), samples, sample_rate)
    
    # 6. 脉冲串
    print("\n[6] 生成脉冲串信号...")
    samples = generate_pulse_train(sample_rate, duration)
    write_bin_file(str(output_dir / "pulse_train.bin"), samples, sample_rate)
    write_csv_file(str(output_dir / "pulse_train.csv"), samples, sample_rate)
    
    # 7. 长时间数据 (10秒，用于测试性能)
    print("\n[7] 生成长时间数据 (10秒)...")
    samples = generate_sine_wave(sample_rate, duration=10.0, frequency=60.0)
    write_bin_file(str(output_dir / "long_sine_60hz.bin"), samples, sample_rate)
    # CSV 格式较大，可选生成
    # write_csv_file(str(output_dir / "long_sine_60hz.csv"), samples, sample_rate)
    
    print("\n" + "="*60)
    print(f"所有测试数据已生成到目录: {output_dir.absolute()}")
    print("="*60 + "\n")
    
    # 输出使用说明
    print("使用方法:")
    print("1. 打开 xgen-waveform-viewer")
    print("2. 点击 '回放' 标签页")
    print("3. 点击 '选择文件' 按钮")
    print(f"4. 选择 {output_dir.absolute()} 目录下的任意 .bin 或 .csv 文件")
    print("5. 点击 '播放' 按钮开始回放")
    print()


if __name__ == "__main__":
    main()
