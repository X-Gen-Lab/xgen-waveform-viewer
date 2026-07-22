"""
V3.0 自定义协议示例

演示如何：
- 创建自定义协议配置
- 使用协议工厂加载协议
- 解析不同格式的数据帧
- 导出和导入协议配置
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, '../src')

from xgen_waveform_viewer.protocol import (
    ProtocolFactory, ProtocolType, FrameFormat,
    BinaryV2Parser, CustomBinaryParser, ASCIIParser
)


def demo_binary_v2():
    """演示默认 Binary V2 协议"""
    print("\n" + "=" * 60)
    print("演示 1: Binary V2 协议（默认）")
    print("=" * 60)
    
    parser = ProtocolFactory.create_parser(ProtocolType.BINARY_V2)
    
    # 构造测试帧
    import struct
    sync = bytes([0xA5, 0x5A])
    seq = struct.pack("<I", 12345)
    cnt = struct.pack("<H", 4)
    samples = struct.pack("<HHHH", 1000, 2000, 3000, 4000)
    
    # 计算 CRC
    payload = seq + cnt + samples
    crc = parser._crc16_ccitt(payload)
    crc_bytes = struct.pack("<H", crc)
    
    frame = sync + payload + crc_bytes
    
    print(f"帧大小: {len(frame)} bytes")
    print(f"帧内容: {frame.hex()}")
    
    # 解析帧
    result = parser.parse_frame(frame)
    
    if result:
        print(f"✓ 解析成功:")
        print(f"  序列号: {result.sequence}")
        print(f"  通道: {result.channel_id}")
        print(f"  采样点: {result.samples}")
    else:
        print("✗ 解析失败")


def demo_custom_binary():
    """演示自定义二进制协议"""
    print("\n" + "=" * 60)
    print("演示 2: 自定义二进制协议")
    print("=" * 60)
    
    # 定义自定义帧格式
    # 格式: [0xAA][0x55][CH:1B][LEN:2B][DATA:LEN×2B][CRC:2B]
    frame_format = FrameFormat(
        sync_bytes=bytes([0xAA, 0x55]),
        meta_size=3,  # CH(1) + LEN(2)
        has_crc=True,
        crc_poly=0x1021,
        crc_init=0xFFFF,
        sample_size=2,
        endianness="big",
        has_sequence=False,
        has_channel_id=True,
        channel_id_offset=0,
        sample_count_offset=1,
        max_samples=1024,
    )
    
    # 保存配置
    config = {"frame_format": frame_format.to_dict()}
    
    print("帧格式配置:")
    print(json.dumps(config, indent=2))
    
    # 创建解析器
    parser = CustomBinaryParser(config)
    parser.format = frame_format
    
    # 构造测试帧
    import struct
    sync = bytes([0xAA, 0x55])
    channel_id = struct.pack("B", 2)  # 通道 2
    sample_count = struct.pack(">H", 3)  # 3 个采样点，big endian
    samples = struct.pack(">HHH", 1234, 5678, 9012)  # big endian
    
    # 计算 CRC
    payload = channel_id + sample_count + samples
    crc = parser._crc16_generic(payload, 0x1021, 0xFFFF)
    crc_bytes = struct.pack(">H", crc)  # big endian
    
    frame = sync + payload + crc_bytes
    
    print(f"\n测试帧:")
    print(f"  大小: {len(frame)} bytes")
    print(f"  内容: {frame.hex()}")
    
    # 解析帧
    result = parser.parse_frame(frame)
    
    if result:
        print(f"\n✓ 解析成功:")
        print(f"  通道: {result.channel_id}")
        print(f"  采样点: {result.samples}")
    else:
        print("\n✗ 解析失败")


def demo_ascii_protocol():
    """演示 ASCII 协议"""
    print("\n" + "=" * 60)
    print("演示 3: ASCII 文本协议")
    print("=" * 60)
    
    # 简单 CSV 格式
    print("\n3.1 简单 CSV 格式")
    config = {
        "line_terminator": b"\n",
        "delimiter": ",",
        "has_channel_prefix": False,
    }
    
    parser = ASCIIParser(config)
    
    test_data = b"1234,5678,9012,3456\n"
    print(f"测试数据: {test_data.decode()}")
    
    result = parser.parse_frame(test_data)
    if result:
        print(f"✓ 解析成功: {result.samples}")
    else:
        print("✗ 解析失败")
    
    # 带通道前缀格式
    print("\n3.2 带通道前缀格式")
    config = {
        "line_terminator": b"\n",
        "delimiter": ",",
        "has_channel_prefix": True,
        "channel_prefix": "#CH",
    }
    
    parser = ASCIIParser(config)
    
    test_data = b"#CH0:1234,5678,9012\n"
    print(f"测试数据: {test_data.decode()}")
    
    result = parser.parse_frame(test_data)
    if result:
        print(f"✓ 解析成功:")
        print(f"  通道: {result.channel_id}")
        print(f"  采样点: {result.samples}")
    else:
        print("✗ 解析失败")


def demo_protocol_export_import():
    """演示协议配置导出和导入"""
    print("\n" + "=" * 60)
    print("演示 4: 协议配置导出和导入")
    print("=" * 60)
    
    # 创建自定义协议
    config = {
        "frame_format": {
            "sync_bytes": "ABCD",
            "meta_size": 4,
            "has_crc": True,
            "crc_poly": "0x8005",
            "crc_init": "0x0000",
            "sample_size": 2,
            "endianness": "little",
            "has_sequence": True,
            "sequence_offset": 0,
            "sequence_size": 2,
            "has_channel_id": False,
            "sample_count_offset": 2,
            "max_samples": 512,
        }
    }
    
    parser = CustomBinaryParser(config)
    parser.format = FrameFormat.from_dict(config["frame_format"])
    
    # 导出到文件
    output_file = Path("example_protocol.json")
    ProtocolFactory.save_to_file(parser, str(output_file))
    print(f"✓ 协议配置已导出到: {output_file}")
    
    # 读取并显示
    with open(output_file, 'r') as f:
        saved_config = json.load(f)
    
    print("\n保存的配置:")
    print(json.dumps(saved_config, indent=2))
    
    # 从文件导入
    loaded_parser = ProtocolFactory.load_from_file(str(output_file))
    print(f"\n✓ 协议配置已从文件加载")
    print(f"  类型: {type(loaded_parser).__name__}")
    
    # 清理
    output_file.unlink()
    print(f"✓ 临时文件已清理")


def demo_multi_protocol_switching():
    """演示多协议切换"""
    print("\n" + "=" * 60)
    print("演示 5: 多协议切换")
    print("=" * 60)
    
    protocols = {
        "Binary V2": ProtocolFactory.create_parser(ProtocolType.BINARY_V2),
        "ASCII": ProtocolFactory.create_parser(ProtocolType.ASCII, {
            "line_terminator": b"\n",
            "delimiter": ",",
        }),
    }
    
    print("已创建协议解析器:")
    for name, parser in protocols.items():
        print(f"  - {name}: {type(parser).__name__}")
    
    print("\n模拟数据流切换场景:")
    
    # 场景 1: Binary V2 数据
    print("\n  场景 1: 接收 Binary V2 数据")
    import struct
    sync = bytes([0xA5, 0x5A])
    data = sync + struct.pack("<IHH", 100, 2, 1000, 2000)
    
    parser = protocols["Binary V2"]
    if data.startswith(bytes([0xA5, 0x5A])):
        print("    ✓ 检测到 Binary V2 同步头")
        # 实际解析需要完整帧（含 CRC）
    
    # 场景 2: ASCII 数据
    print("\n  场景 2: 接收 ASCII 数据")
    data = b"1234,5678\n"
    
    parser = protocols["ASCII"]
    if b"," in data:
        print("    ✓ 检测到 ASCII 分隔符")
        result = parser.parse_frame(data)
        if result:
            print(f"    ✓ 解析成功: {result.samples}")


def main():
    """主函数"""
    print("=" * 60)
    print("xgen-waveform-viewer V3.0 - 自定义协议示例")
    print("=" * 60)
    
    try:
        demo_binary_v2()
        demo_custom_binary()
        demo_ascii_protocol()
        demo_protocol_export_import()
        demo_multi_protocol_switching()
        
        print("\n" + "=" * 60)
        print("所有演示完成！")
        print("=" * 60)
        print("\n提示:")
        print("- 查看生成的配置文件了解格式")
        print("- 在实际应用中根据设备修改配置")
        print("- 使用 UI 面板可视化配置协议")
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
