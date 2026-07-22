"""
xgen-waveform-viewer V2.4 新功能示例

演示:
1. 数据回放功能
2. 多格式导出 (PNG, SVG, MATLAB, HDF5)
3. 波形比较工具
"""

import sys
from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import QApplication

# 导入回放和导出模块
from xgen_waveform_viewer.playback import PlaybackReader
from xgen_waveform_viewer.exporter import WaveformExporter, WaveformComparator


def example_1_load_and_analyze_recording():
    """示例 1: 加载并分析录制文件"""
    print("=== 示例 1: 加载并分析录制文件 ===\n")
    
    # 假设有一个录制文件
    recording_file = "path/to/your/recording.bin"
    
    if not Path(recording_file).exists():
        print(f"文件不存在: {recording_file}")
        print("请先使用主程序录制一些数据\n")
        return
    
    # 创建回放读取器
    reader = PlaybackReader()
    
    try:
        # 加载文件
        info = reader.load_file(recording_file)
        
        print(f"文件路径: {info.path}")
        print(f"格式: {info.format}")
        print(f"采样率: {info.sample_rate_hz} Hz")
        print(f"总帧数: {info.total_frames:,}")
        print(f"总采样点: {info.total_samples:,}")
        print(f"时长: {info.duration_s:.2f} 秒")
        print()
        
    except Exception as e:
        print(f"加载文件失败: {e}\n")


def example_2_export_to_matlab():
    """示例 2: 导出数据为 MATLAB 格式"""
    print("=== 示例 2: 导出为 MATLAB 格式 ===\n")
    
    # 生成示例数据
    sample_rate = 10000  # 10kHz
    duration = 1.0  # 1秒
    num_samples = int(sample_rate * duration)
    
    # 生成正弦波 + 噪声
    t = np.arange(num_samples) / sample_rate
    frequency = 100  # 100Hz
    samples = 2048 + 1000 * np.sin(2 * np.pi * frequency * t)
    samples += np.random.randn(num_samples) * 50  # 添加噪声
    samples = samples.astype(np.uint16)
    
    # 导出为 MATLAB 格式
    output_path = "example_waveform.mat"
    
    metadata = {
        'signal_type': 'sine_wave_with_noise',
        'frequency_hz': frequency,
        'noise_level': 50,
    }
    
    success = WaveformExporter.export_matlab(
        samples,
        output_path,
        sample_rate,
        metadata
    )
    
    if success:
        print(f"✓ 成功导出到: {output_path}")
        print(f"  采样点数: {len(samples):,}")
        print(f"  文件大小: {Path(output_path).stat().st_size / 1024:.1f} KB")
        print("\n在 MATLAB 中加载:")
        print(f"  data = load('{output_path}');")
        print("  plot(data.time, data.samples);")
        print()
    else:
        print("✗ 导出失败（需要安装 scipy）\n")


def example_3_export_to_hdf5():
    """示例 3: 导出数据为 HDF5 格式"""
    print("=== 示例 3: 导出为 HDF5 格式 ===\n")
    
    # 生成示例数据（更大的数据集）
    sample_rate = 100000  # 100kHz
    duration = 10.0  # 10秒
    num_samples = int(sample_rate * duration)
    
    # 生成复杂波形
    t = np.arange(num_samples) / sample_rate
    samples = 2048.0
    samples += 500 * np.sin(2 * np.pi * 50 * t)  # 50Hz 分量
    samples += 300 * np.sin(2 * np.pi * 150 * t)  # 150Hz 分量
    samples += 200 * np.sin(2 * np.pi * 300 * t)  # 300Hz 分量
    samples = samples.astype(np.uint16)
    
    # 导出为 HDF5（带压缩）
    output_path = "example_waveform.h5"
    
    metadata = {
        'signal_type': 'multi_frequency',
        'frequencies': '50, 150, 300 Hz',
    }
    
    success = WaveformExporter.export_hdf5(
        samples,
        output_path,
        sample_rate,
        metadata,
        compression=True
    )
    
    if success:
        file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        uncompressed_size_mb = len(samples) * 2 / (1024 * 1024)  # uint16 = 2 bytes
        compression_ratio = (1 - file_size_mb / uncompressed_size_mb) * 100
        
        print(f"✓ 成功导出到: {output_path}")
        print(f"  采样点数: {len(samples):,}")
        print(f"  未压缩大小: {uncompressed_size_mb:.1f} MB")
        print(f"  压缩后大小: {file_size_mb:.1f} MB")
        print(f"  压缩比: {compression_ratio:.1f}%")
        print("\n在 Python 中加载:")
        print(f"  import h5py")
        print(f"  with h5py.File('{output_path}', 'r') as f:")
        print(f"      samples = f['samples'][:]")
        print(f"      sample_rate = f.attrs['sample_rate_hz']")
        print()
    else:
        print("✗ 导出失败（需要安装 h5py）\n")


def example_4_load_and_export_hdf5():
    """示例 4: 从 HDF5 加载数据"""
    print("=== 示例 4: 从 HDF5 加载数据 ===\n")
    
    hdf5_file = "example_waveform.h5"
    
    if not Path(hdf5_file).exists():
        print(f"文件不存在: {hdf5_file}")
        print("请先运行示例 3 生成文件\n")
        return
    
    result = WaveformExporter.load_hdf5(hdf5_file)
    
    if result:
        samples, sample_rate, metadata = result
        
        print(f"✓ 成功加载: {hdf5_file}")
        print(f"  采样点数: {len(samples):,}")
        print(f"  采样率: {sample_rate} Hz")
        print(f"  时长: {len(samples) / sample_rate:.2f} 秒")
        print(f"  元数据: {metadata}")
        print()
        
        # 计算统计信息
        print("统计信息:")
        print(f"  平均值: {np.mean(samples):.2f}")
        print(f"  最大值: {np.max(samples)}")
        print(f"  最小值: {np.min(samples)}")
        print(f"  标准差: {np.std(samples):.2f}")
        print()
    else:
        print("✗ 加载失败\n")


def example_5_compare_waveforms():
    """示例 5: 波形比较"""
    print("=== 示例 5: 波形比较 ===\n")
    
    # 生成两个相似但不完全相同的波形
    sample_rate = 10000
    num_samples = 10000
    t = np.arange(num_samples) / sample_rate
    
    # 波形 1: 纯正弦波
    waveform1 = 2048 + 1000 * np.sin(2 * np.pi * 100 * t)
    waveform1 = waveform1.astype(np.uint16)
    
    # 波形 2: 正弦波 + 小噪声
    waveform2 = 2048 + 1000 * np.sin(2 * np.pi * 100 * t)
    waveform2 += np.random.randn(num_samples) * 30  # 添加噪声
    waveform2 = waveform2.astype(np.uint16)
    
    # 比较波形
    comparison = WaveformComparator.compare_waveforms(
        waveform1,
        waveform2,
        sample_rate
    )
    
    print("波形 1 统计:")
    for key, value in comparison['waveform1'].items():
        print(f"  {key}: {value:.2f}")
    
    print("\n波形 2 统计:")
    for key, value in comparison['waveform2'].items():
        print(f"  {key}: {value:.2f}")
    
    print("\n差异分析:")
    for key, value in comparison['difference'].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    print()


def example_6_generate_html_report():
    """示例 6: 生成 HTML 统计报告"""
    print("=== 示例 6: 生成 HTML 统计报告 ===\n")
    
    # 生成示例数据
    sample_rate = 10000
    duration = 5.0
    num_samples = int(sample_rate * duration)
    t = np.arange(num_samples) / sample_rate
    
    # 生成波形
    samples = 2048 + 800 * np.sin(2 * np.pi * 60 * t)
    samples += 200 * np.sin(2 * np.pi * 180 * t)
    samples = samples.astype(np.uint16)
    
    # 计算统计信息
    stats = {
        'sample_rate_hz': sample_rate,
        'total_samples': len(samples),
        'duration_s': duration,
        'mean': float(np.mean(samples)),
        'rms': float(np.sqrt(np.mean(samples.astype(float) ** 2))),
        'max': float(np.max(samples)),
        'min': float(np.min(samples)),
        'peak_to_peak': float(np.max(samples) - np.min(samples)),
        'frequency_hz': 60.0,
        'period_s': 1.0 / 60.0,
    }
    
    # 导出报告
    output_path = "waveform_report.html"
    
    success = WaveformExporter.export_statistics_html(
        stats,
        output_path,
        waveform_image_path=None
    )
    
    if success:
        print(f"✓ 成功生成报告: {output_path}")
        print(f"  在浏览器中打开查看详细统计信息")
        print()
    else:
        print("✗ 生成报告失败\n")


def main():
    """运行所有示例"""
    print("\n" + "="*60)
    print("xgen-waveform-viewer V2.4 新功能示例")
    print("="*60 + "\n")
    
    # 运行各个示例
    example_1_load_and_analyze_recording()
    example_2_export_to_matlab()
    example_3_export_to_hdf5()
    example_4_load_and_export_hdf5()
    example_5_compare_waveforms()
    example_6_generate_html_report()
    
    print("="*60)
    print("所有示例完成！")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
