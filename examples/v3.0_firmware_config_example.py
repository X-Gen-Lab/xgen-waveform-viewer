"""
V3.0 固件配置示例

演示如何：
- 获取固件版本信息
- 读取和修改固件配置
- 执行 OTA 固件更新
- 检查固件兼容性
"""

import sys
import time
import struct
from pathlib import Path

sys.path.insert(0, '../src')

from xgen_waveform_viewer.firmware_config import (
    FirmwareConfigManager, FirmwareVersion, FirmwareConfig,
    check_firmware_compatibility, FirmwareCommandType
)


def demo_firmware_version():
    """演示固件版本处理"""
    print("\n" + "=" * 60)
    print("演示 1: 固件版本信息")
    print("=" * 60)
    
    # 创建版本对象
    version = FirmwareVersion(
        major=3,
        minor=0,
        patch=1,
        build=42,
        commit_hash="a1b2c3d4e5f6",
        build_date="2026-07-22"
    )
    
    print(f"版本字符串: {version}")
    print(f"详细信息:")
    print(f"  主版本: {version.major}")
    print(f"  次版本: {version.minor}")
    print(f"  补丁版本: {version.patch}")
    print(f"  构建号: {version.build}")
    print(f"  Commit: {version.commit_hash}")
    print(f"  构建日期: {version.build_date}")
    
    # 版本比较
    print("\n版本兼容性检查:")
    
    test_cases = [
        (FirmwareVersion(3, 0, 0), FirmwareVersion(2, 4, 0), True),
        (FirmwareVersion(2, 3, 0), FirmwareVersion(2, 4, 0), False),
        (FirmwareVersion(3, 1, 0), FirmwareVersion(3, 0, 0), True),
    ]
    
    for current, minimum, expected in test_cases:
        is_compat, msg = check_firmware_compatibility(current, minimum)
        status = "✓" if is_compat == expected else "✗"
        print(f"{status} {current} vs {minimum}: {is_compat}")


def demo_firmware_config():
    """演示固件配置"""
    print("\n" + "=" * 60)
    print("演示 2: 固件配置参数")
    print("=" * 60)
    
    # 创建配置对象
    config = FirmwareConfig(
        sample_rate=100000,      # 100 kHz
        frame_length=512,        # 512 samples/frame
        channel_count=4,         # 4 通道
        channel_mask=0x0F,       # 启用通道 0-3
        adc_resolution=12,       # 12 位 ADC
        adc_vref=3.3,           # 3.3V 参考电压
        trigger_enabled=True,    # 启用触发
        trigger_level=2048,      # 触发电平
        trigger_edge="rising",   # 上升沿触发
    )
    
    print("配置参数:")
    print(f"  采样率: {config.sample_rate} Hz ({config.sample_rate/1000:.1f} kHz)")
    print(f"  帧长: {config.frame_length} samples")
    print(f"  通道数: {config.channel_count}")
    print(f"  通道掩码: 0x{config.channel_mask:04X}")
    print(f"  ADC 分辨率: {config.adc_resolution} bits")
    print(f"  ADC 参考电压: {config.adc_vref} V")
    print(f"  触发: {'启用' if config.trigger_enabled else '禁用'}")
    print(f"  触发电平: {config.trigger_level}")
    print(f"  触发边沿: {config.trigger_edge}")
    
    # 序列化
    print("\n序列化配置:")
    config_bytes = config.to_bytes()
    print(f"  字节长度: {len(config_bytes)}")
    print(f"  十六进制: {config_bytes.hex()}")
    
    # 反序列化
    print("\n反序列化配置:")
    restored_config = FirmwareConfig.from_bytes(config_bytes)
    print(f"  采样率: {restored_config.sample_rate} Hz")
    print(f"  帧长: {restored_config.frame_length} samples")
    print(f"  ✓ 配置序列化/反序列化成功")


def demo_firmware_commands():
    """演示固件命令构造"""
    print("\n" + "=" * 60)
    print("演示 3: 固件命令协议")
    print("=" * 60)
    
    def build_command(cmd_type: FirmwareCommandType, data: bytes = b""):
        """构造命令帧"""
        SYNC_0, SYNC_1 = 0xFC, 0xCF
        cmd_byte = cmd_type.value
        length = len(data)
        
        # 构建载荷
        payload = struct.pack("<BH", cmd_byte, length) + data
        
        # 计算 CRC
        crc = 0xFFFF
        for byte in payload:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        
        # 组装帧
        frame = bytes([SYNC_0, SYNC_1]) + payload + struct.pack("<H", crc)
        return frame
    
    # 示例 1: 获取版本命令
    print("\n命令 1: GET_VERSION")
    frame = build_command(FirmwareCommandType.GET_VERSION)
    print(f"  命令帧: {frame.hex()}")
    print(f"  长度: {len(frame)} bytes")
    
    # 示例 2: 设置采样率命令
    print("\n命令 2: SET_SAMPLE_RATE")
    data = struct.pack("<I", 50000)  # 50 kHz
    frame = build_command(FirmwareCommandType.SET_SAMPLE_RATE, data)
    print(f"  命令帧: {frame.hex()}")
    print(f"  长度: {len(frame)} bytes")
    print(f"  参数: 50000 Hz")
    
    # 示例 3: 设置完整配置命令
    print("\n命令 3: SET_CONFIG")
    config = FirmwareConfig(
        sample_rate=100000,
        frame_length=256,
        channel_count=2,
        channel_mask=0x03,
        adc_resolution=12,
        adc_vref=3.3,
    )
    data = config.to_bytes()
    frame = build_command(FirmwareCommandType.SET_CONFIG, data)
    print(f"  命令帧: {frame.hex()}")
    print(f"  长度: {len(frame)} bytes")


def demo_ota_update_process():
    """演示 OTA 更新流程（模拟）"""
    print("\n" + "=" * 60)
    print("演示 4: OTA 固件更新流程（模拟）")
    print("=" * 60)
    
    # 模拟固件数据
    firmware_data = b"\xAA" * 1024  # 1 KB 测试固件
    total_size = len(firmware_data)
    
    print(f"固件大小: {total_size} bytes")
    
    # 步骤 1: 发送 OTA_START 命令
    print("\n步骤 1: 发送 OTA_START 命令")
    start_data = struct.pack("<I", total_size)
    print(f"  参数: 固件大小 = {total_size} bytes")
    
    # 步骤 2: 分块发送固件数据
    print("\n步骤 2: 分块发送固件")
    chunk_size = 256
    chunks = (total_size + chunk_size - 1) // chunk_size
    
    for i in range(chunks):
        offset = i * chunk_size
        chunk = firmware_data[offset:offset + chunk_size]
        progress = (offset + len(chunk)) * 100 / total_size
        
        if i % 2 == 0:  # 只打印部分进度
            print(f"  块 {i+1}/{chunks}: offset={offset}, size={len(chunk)}, progress={progress:.1f}%")
    
    # 步骤 3: 发送 OTA_END 命令
    print("\n步骤 3: 发送 OTA_END 命令")
    print("  等待固件写入完成...")
    
    # 步骤 4: 发送 OTA_VERIFY 命令
    print("\n步骤 4: 发送 OTA_VERIFY 命令")
    print("  验证固件完整性...")
    
    print("\n✓ OTA 更新流程完成")
    print("  设备将重启并运行新固件")


def demo_practical_usage():
    """演示实际使用场景"""
    print("\n" + "=" * 60)
    print("演示 5: 实际使用场景")
    print("=" * 60)
    
    print("\n场景 1: 启动时检查固件版本")
    print("-" * 40)
    
    # 模拟获取到的版本
    current_version = FirmwareVersion(2, 4, 1)
    required_version = FirmwareVersion(3, 0, 0)
    
    is_compatible, message = check_firmware_compatibility(current_version, required_version)
    
    if not is_compatible:
        print(f"⚠️  {message}")
        print("   建议操作:")
        print("   1. 下载最新固件")
        print("   2. 使用 OTA 功能更新")
        print("   3. 或使用固件烧录工具更新")
    else:
        print(f"✓ {message}")
    
    print("\n场景 2: 动态调整采样参数")
    print("-" * 40)
    
    scenarios = [
        ("低速采样（省电）", 1000, 64),
        ("标准采样", 10000, 256),
        ("高速采样", 100000, 1024),
        ("超高速采样（最大）", 1000000, 2048),
    ]
    
    for name, rate, frame_len in scenarios:
        print(f"\n  {name}:")
        print(f"    采样率: {rate} Hz")
        print(f"    帧长: {frame_len} samples")
        
        # 计算数据率
        bytes_per_second = rate * 2  # 每采样点 2 字节
        frames_per_second = rate / frame_len
        
        print(f"    数据率: {bytes_per_second/1024:.1f} KB/s")
        print(f"    帧率: {frames_per_second:.1f} frames/s")
    
    print("\n场景 3: 多通道配置")
    print("-" * 40)
    
    channel_configs = [
        (1, 0x01, "单通道"),
        (2, 0x03, "双通道（CH0+CH1）"),
        (4, 0x0F, "四通道（CH0-CH3）"),
        (8, 0xFF, "八通道（CH0-CH7）"),
    ]
    
    for count, mask, desc in channel_configs:
        print(f"\n  {desc}:")
        print(f"    通道数: {count}")
        print(f"    通道掩码: 0x{mask:04X}")
        print(f"    启用通道: ", end="")
        
        enabled = []
        for i in range(16):
            if mask & (1 << i):
                enabled.append(f"CH{i}")
        print(", ".join(enabled))


def main():
    """主函数"""
    print("=" * 60)
    print("xgen-waveform-viewer V3.0 - 固件配置示例")
    print("=" * 60)
    
    try:
        demo_firmware_version()
        demo_firmware_config()
        demo_firmware_commands()
        demo_ota_update_process()
        demo_practical_usage()
        
        print("\n" + "=" * 60)
        print("所有演示完成！")
        print("=" * 60)
        print("\n注意事项:")
        print("- 实际使用需要连接串口设备")
        print("- OTA 更新需要固件支持（V3.0+）")
        print("- 更新过程中不要断开连接")
        print("- 建议使用 UI 面板进行配置")
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
