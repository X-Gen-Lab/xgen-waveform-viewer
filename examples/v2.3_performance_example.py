"""
xgen-waveform-viewer V2.3 性能优化示例

演示如何使用 V2.3 新增的性能优化功能：
1. 降采样算法
2. 帧率限制
3. 内存管理
4. 日志系统
5. 统计面板
"""

import sys
import numpy as np
from pathlib import Path

# 添加源码路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xgen_waveform_viewer.performance import PerformanceOptimizer, MemoryOptimizer
from xgen_waveform_viewer.logger import init_logger, get_logger


def example_1_downsampling():
    """示例 1: 使用降采样算法"""
    print("=" * 60)
    print("示例 1: 降采样算法")
    print("=" * 60)
    
    # 创建性能优化器
    optimizer = PerformanceOptimizer()
    
    # 生成测试数据（100,000 点正弦波）
    n_points = 100000
    time = np.linspace(0, 10, n_points)
    data = np.sin(2 * np.pi * time) * 1000 + 2048
    data = data.astype(np.uint16)
    
    print(f"原始数据点数: {len(data):,}")
    
    # 检查是否需要降采样
    if optimizer.should_downsample(len(data)):
        print("数据量超过阈值，触发降采样")
        
        # 计算降采样因子
        factor = optimizer.calculate_downsample_factor(len(data))
        print(f"降采样因子: {factor}")
        
        # 执行降采样
        result = optimizer.downsample_minmax(time, data, factor)
        
        print(f"降采样后点数: {result.downsampled_length:,}")
        print(f"压缩比: {result.original_length / result.downsampled_length:.1f}x")
        print(f"保留的最小值范围: {result.min_values.min():.0f} - {result.min_values.max():.0f}")
        print(f"保留的最大值范围: {result.max_values.min():.0f} - {result.max_values.max():.0f}")
    else:
        print("数据量未超过阈值，不需要降采样")
    
    # 准备渲染数据（自动降采样）
    time_render, data_render = optimizer.prepare_render_data(time, data)
    print(f"渲染数据点数: {len(data_render):,}")
    print()


def example_2_fps_limit():
    """示例 2: 帧率限制"""
    print("=" * 60)
    print("示例 2: 帧率限制")
    print("=" * 60)
    
    optimizer = PerformanceOptimizer()
    
    # 设置不同的帧率限制
    fps_values = [15, 30, 60, 120]
    
    for fps in fps_values:
        optimizer.set_fps_limit(fps)
        interval = optimizer.get_refresh_interval_ms()
        print(f"FPS: {fps:3d} -> 刷新间隔: {interval:3d} ms")
    
    # 推荐设置
    print("\n推荐设置:")
    print("  低功耗模式: 15-20 FPS")
    print("  平衡模式: 30 FPS (默认)")
    print("  高性能模式: 60 FPS")
    print("  极限模式: 120 FPS")
    print()


def example_3_memory_management():
    """示例 3: 内存管理"""
    print("=" * 60)
    print("示例 3: 内存管理")
    print("=" * 60)
    
    mem_optimizer = MemoryOptimizer()
    
    # 设置内存限制
    mem_optimizer.set_memory_limit_mb(100.0)
    print(f"内存限制: {mem_optimizer.get_memory_limit_mb():.1f} MB")
    
    # 计算可容纳的最大样本数
    max_samples = mem_optimizer.calculate_max_samples()
    print(f"最大样本数: {max_samples:,}")
    
    # 测试不同的样本数
    test_samples = [1_000_000, 10_000_000, 50_000_000, 100_000_000]
    
    print("\n样本数测试:")
    for n_samples in test_samples:
        usage = mem_optimizer.estimate_memory_usage(n_samples)
        within_limit = mem_optimizer.is_within_limit(n_samples)
        status = "✓" if within_limit else "✗"
        print(f"  {status} {n_samples:>12,} 样本 -> {mem_optimizer.format_bytes(usage):>10}")
    
    # 建议缓冲区大小
    requested = 100_000_000
    suggested = mem_optimizer.suggest_buffer_size(requested)
    print(f"\n请求 {requested:,} 样本")
    print(f"建议 {suggested:,} 样本")
    print()


def example_4_logging():
    """示例 4: 日志系统"""
    print("=" * 60)
    print("示例 4: 日志系统")
    print("=" * 60)
    
    # 初始化日志器
    logger = init_logger()
    
    print(f"日志文件位置: {logger.get_log_file_path()}")
    print()
    
    # 记录不同类型的事件
    logger.info("应用程序启动", category="app")
    logger.log_serial_event("opened", details={"port": "COM3", "baudrate": 921600})
    logger.log_frame_event("received", seq=1, details={"samples": 256})
    logger.log_crc_error(seq=10, expected=0xABCD, received=0x1234)
    logger.log_seq_gap(expected=100, received=105, gap=5)
    logger.log_resync("sync_header_mismatch")
    logger.warning("高错误率", category="performance", details={"error_rate": 5.2})
    
    # 获取事件统计
    error_count = logger.get_error_count()
    warning_count = logger.get_warning_count()
    
    print(f"错误数量: {error_count}")
    print(f"警告数量: {warning_count}")
    
    # 获取特定类别的事件
    crc_errors = logger.get_events(category="crc_error")
    print(f"CRC 错误事件: {len(crc_errors)}")
    
    seq_gaps = logger.get_events(category="seq_gap")
    print(f"序列号间隙事件: {len(seq_gaps)}")
    
    # 导出日志（可选）
    # output_file = Path("example_log_export.json")
    # logger.export_events_json(output_file)
    # print(f"日志已导出到: {output_file}")
    print()


def example_5_performance_tuning():
    """示例 5: 性能调优建议"""
    print("=" * 60)
    print("示例 5: 性能调优建议")
    print("=" * 60)
    
    print("场景 1: 高速数据采集 (>10 kHz)")
    print("  - FPS 限制: 30 FPS")
    print("  - 启用降采样: True")
    print("  - 降采样阈值: 10,000 点")
    print("  - 内存限制: 200 MB")
    print()
    
    print("场景 2: 长时间运行")
    print("  - FPS 限制: 20 FPS")
    print("  - 启用降采样: True")
    print("  - 内存限制: 100 MB")
    print("  - 定期清理日志")
    print()
    
    print("场景 3: 低功耗模式（笔记本）")
    print("  - FPS 限制: 15 FPS")
    print("  - 启用降采样: True")
    print("  - 降采样阈值: 5,000 点")
    print("  - 内存限制: 50 MB")
    print()
    
    print("场景 4: 高精度分析")
    print("  - FPS 限制: 60 FPS")
    print("  - 启用降采样: False")
    print("  - 内存限制: 500 MB")
    print("  - 减小 X 轴窗口")
    print()


def main():
    """运行所有示例"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  xgen-waveform-viewer V2.3 性能优化示例".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    print("\n")
    
    try:
        example_1_downsampling()
        example_2_fps_limit()
        example_3_memory_management()
        example_4_logging()
        example_5_performance_tuning()
        
        print("=" * 60)
        print("所有示例运行完成！")
        print("=" * 60)
        print("\n查看 docs/RELEASE_NOTES_V2.3.md 获取更多信息")
        print()
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
