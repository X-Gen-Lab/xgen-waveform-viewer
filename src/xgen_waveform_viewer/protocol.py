"""
协议扩展框架 - V3.0

支持多种数据源协议：
- 自定义帧格式（配置文件）
- ASCII 协议支持
- TCP/UDP 数据源
- 协议自动检测
"""

import struct
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any
from enum import Enum
import numpy as np


class ProtocolType(Enum):
    """协议类型"""
    BINARY_V2 = "binary_v2"  # 现有的二进制协议
    BINARY_CUSTOM = "binary_custom"  # 自定义二进制协议
    ASCII = "ascii"  # ASCII 文本协议
    MODBUS_RTU = "modbus_rtu"  # Modbus RTU
    JSON = "json"  # JSON 协议


@dataclass
class FrameFormat:
    """帧格式定义"""
    sync_bytes: bytes  # 同步头
    meta_size: int  # 元数据大小
    has_crc: bool = True  # 是否有 CRC
    crc_size: int = 2  # CRC 大小
    crc_poly: int = 0x1021  # CRC 多项式
    crc_init: int = 0xFFFF  # CRC 初始值
    sample_size: int = 2  # 单个采样点字节数
    endianness: str = "little"  # 字节序 "little" 或 "big"
    has_sequence: bool = True  # 是否有序列号
    sequence_offset: int = 0  # 序列号偏移
    sequence_size: int = 4  # 序列号大小
    has_channel_id: bool = False  # 是否包含通道 ID
    channel_id_offset: int = 0  # 通道 ID 偏移
    sample_count_offset: int = 4  # 采样点数偏移
    max_samples: int = 1024  # 最大采样点数
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FrameFormat':
        """从字典创建"""
        sync_hex = data.get("sync_bytes", "A55A")
        sync_bytes = bytes.fromhex(sync_hex)
        return cls(
            sync_bytes=sync_bytes,
            meta_size=data.get("meta_size", 6),
            has_crc=data.get("has_crc", True),
            crc_size=data.get("crc_size", 2),
            crc_poly=int(data.get("crc_poly", "0x1021"), 16),
            crc_init=int(data.get("crc_init", "0xFFFF"), 16),
            sample_size=data.get("sample_size", 2),
            endianness=data.get("endianness", "little"),
            has_sequence=data.get("has_sequence", True),
            sequence_offset=data.get("sequence_offset", 0),
            sequence_size=data.get("sequence_size", 4),
            has_channel_id=data.get("has_channel_id", False),
            channel_id_offset=data.get("channel_id_offset", 0),
            sample_count_offset=data.get("sample_count_offset", 4),
            max_samples=data.get("max_samples", 1024),
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "sync_bytes": self.sync_bytes.hex().upper(),
            "meta_size": self.meta_size,
            "has_crc": self.has_crc,
            "crc_size": self.crc_size,
            "crc_poly": hex(self.crc_poly),
            "crc_init": hex(self.crc_init),
            "sample_size": self.sample_size,
            "endianness": self.endianness,
            "has_sequence": self.has_sequence,
            "sequence_offset": self.sequence_offset,
            "sequence_size": self.sequence_size,
            "has_channel_id": self.has_channel_id,
            "channel_id_offset": self.channel_id_offset,
            "sample_count_offset": self.sample_count_offset,
            "max_samples": self.max_samples,
        }


@dataclass
class ParsedFrame:
    """解析后的帧数据"""
    samples: np.ndarray  # 采样数据
    sequence: int  # 序列号
    channel_id: int = 0  # 通道 ID
    timestamp: float = 0.0  # 时间戳
    metadata: Dict[str, Any] = None  # 额外元数据
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ProtocolParser(ABC):
    """协议解析器基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    @abstractmethod
    def parse_frame(self, data: bytes) -> Optional[ParsedFrame]:
        """解析单帧数据"""
        pass
    
    @abstractmethod
    def find_sync(self, buffer: bytes, start: int = 0) -> int:
        """在缓冲区中查找同步头，返回位置（-1 表示未找到）"""
        pass
    
    @abstractmethod
    def get_frame_size(self, buffer: bytes) -> int:
        """获取帧大小（如果数据不足则返回 0）"""
        pass
    
    @abstractmethod
    def validate_frame(self, data: bytes) -> bool:
        """验证帧完整性（CRC 等）"""
        pass


class BinaryV2Parser(ProtocolParser):
    """现有的二进制协议解析器（兼容现有代码）"""
    
    SYNC_BYTE_0 = 0xA5
    SYNC_BYTE_1 = 0x5A
    META_BYTES = 6
    CRC_BYTES = 2
    HEADER_SIZE = 2 + META_BYTES  # sync + meta
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
    
    def find_sync(self, buffer: bytes, start: int = 0) -> int:
        """查找同步头"""
        sync_pattern = bytes([self.SYNC_BYTE_0, self.SYNC_BYTE_1])
        return buffer.find(sync_pattern, start)
    
    def get_frame_size(self, buffer: bytes) -> int:
        """获取帧大小"""
        if len(buffer) < self.HEADER_SIZE:
            return 0
        
        # 验证同步头
        if buffer[0] != self.SYNC_BYTE_0 or buffer[1] != self.SYNC_BYTE_1:
            return -1
        
        # 读取采样点数
        cnt_offset = 2 + 4  # skip sync + seq
        samples_cnt = struct.unpack("<H", buffer[cnt_offset:cnt_offset + 2])[0]
        
        # 验证合理性
        max_samples = self.config.get("max_samples", 1024)
        if samples_cnt == 0 or samples_cnt > max_samples:
            return -1
        
        return self.HEADER_SIZE + samples_cnt * 2 + self.CRC_BYTES
    
    def validate_frame(self, data: bytes) -> bool:
        """验证 CRC"""
        if len(data) < self.HEADER_SIZE + self.CRC_BYTES:
            return False
        
        # CRC 覆盖 sync 之后的数据到 CRC 之前
        payload_size = len(data) - 2 - self.CRC_BYTES  # 减去 sync 和 CRC
        crc_calc = self._crc16_ccitt(data[2:2 + payload_size])
        crc_recv = struct.unpack("<H", data[-self.CRC_BYTES:])[0]
        return crc_calc == crc_recv
    
    def parse_frame(self, data: bytes) -> Optional[ParsedFrame]:
        """解析帧"""
        if not self.validate_frame(data):
            return None
        
        # 跳过 sync 头
        body = data[2:]
        
        # 解析序列号
        seq = struct.unpack("<I", body[0:4])[0]
        
        # 解析采样点数
        samples_cnt = struct.unpack("<H", body[4:6])[0]
        
        # 解析采样数据
        samples_data = body[self.META_BYTES:self.META_BYTES + samples_cnt * 2]
        samples = np.frombuffer(samples_data, dtype=np.uint16).copy()
        
        return ParsedFrame(samples=samples, sequence=seq, channel_id=0)
    
    @staticmethod
    def _crc16_ccitt(data: bytes) -> int:
        """CRC-16-CCITT"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc


class CustomBinaryParser(ProtocolParser):
    """自定义二进制协议解析器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        if "frame_format" in config:
            self.format = FrameFormat.from_dict(config["frame_format"])
        else:
            # 默认使用 V2 格式
            self.format = FrameFormat(
                sync_bytes=bytes([0xA5, 0x5A]),
                meta_size=6,
            )
    
    def find_sync(self, buffer: bytes, start: int = 0) -> int:
        """查找同步头"""
        return buffer.find(self.format.sync_bytes, start)
    
    def get_frame_size(self, buffer: bytes) -> int:
        """获取帧大小"""
        sync_len = len(self.format.sync_bytes)
        header_size = sync_len + self.format.meta_size
        
        if len(buffer) < header_size:
            return 0
        
        # 验证同步头
        if buffer[:sync_len] != self.format.sync_bytes:
            return -1
        
        # 读取采样点数
        cnt_offset = sync_len + self.format.sample_count_offset
        if self.format.endianness == "little":
            samples_cnt = struct.unpack("<H", buffer[cnt_offset:cnt_offset + 2])[0]
        else:
            samples_cnt = struct.unpack(">H", buffer[cnt_offset:cnt_offset + 2])[0]
        
        # 验证合理性
        if samples_cnt == 0 or samples_cnt > self.format.max_samples:
            return -1
        
        frame_size = header_size + samples_cnt * self.format.sample_size
        if self.format.has_crc:
            frame_size += self.format.crc_size
        
        return frame_size
    
    def validate_frame(self, data: bytes) -> bool:
        """验证帧"""
        if not self.format.has_crc:
            return True
        
        sync_len = len(self.format.sync_bytes)
        payload_size = len(data) - sync_len - self.format.crc_size
        
        if payload_size <= 0:
            return False
        
        # 计算 CRC
        crc_data = data[sync_len:sync_len + payload_size]
        crc_calc = self._crc16_generic(crc_data, self.format.crc_poly, self.format.crc_init)
        
        # 读取 CRC
        crc_offset = len(data) - self.format.crc_size
        if self.format.endianness == "little":
            crc_recv = struct.unpack("<H", data[crc_offset:crc_offset + 2])[0]
        else:
            crc_recv = struct.unpack(">H", data[crc_offset:crc_offset + 2])[0]
        
        return crc_calc == crc_recv
    
    def parse_frame(self, data: bytes) -> Optional[ParsedFrame]:
        """解析帧"""
        if not self.validate_frame(data):
            return None
        
        sync_len = len(self.format.sync_bytes)
        body = data[sync_len:]
        
        # 解析序列号
        sequence = 0
        if self.format.has_sequence:
            seq_offset = self.format.sequence_offset
            seq_size = self.format.sequence_size
            if self.format.endianness == "little":
                if seq_size == 4:
                    sequence = struct.unpack("<I", body[seq_offset:seq_offset + 4])[0]
                elif seq_size == 2:
                    sequence = struct.unpack("<H", body[seq_offset:seq_offset + 2])[0]
            else:
                if seq_size == 4:
                    sequence = struct.unpack(">I", body[seq_offset:seq_offset + 4])[0]
                elif seq_size == 2:
                    sequence = struct.unpack(">H", body[seq_offset:seq_offset + 2])[0]
        
        # 解析通道 ID
        channel_id = 0
        if self.format.has_channel_id:
            ch_offset = self.format.channel_id_offset
            channel_id = body[ch_offset]
        
        # 解析采样点数
        cnt_offset = self.format.sample_count_offset
        if self.format.endianness == "little":
            samples_cnt = struct.unpack("<H", body[cnt_offset:cnt_offset + 2])[0]
        else:
            samples_cnt = struct.unpack(">H", body[cnt_offset:cnt_offset + 2])[0]
        
        # 解析采样数据
        samples_offset = self.format.meta_size
        samples_size = samples_cnt * self.format.sample_size
        samples_data = body[samples_offset:samples_offset + samples_size]
        
        # 根据采样大小选择数据类型
        if self.format.sample_size == 2:
            dtype = np.uint16
        elif self.format.sample_size == 4:
            dtype = np.uint32
        elif self.format.sample_size == 1:
            dtype = np.uint8
        else:
            dtype = np.uint16
        
        if self.format.endianness == "big":
            dtype = dtype.newbyteorder('>')
        
        samples = np.frombuffer(samples_data, dtype=dtype).copy()
        
        return ParsedFrame(samples=samples, sequence=sequence, channel_id=channel_id)
    
    @staticmethod
    def _crc16_generic(data: bytes, poly: int, init: int) -> int:
        """通用 CRC-16 计算"""
        crc = init
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ poly) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc


class ASCIIParser(ProtocolParser):
    """ASCII 文本协议解析器
    
    支持格式：
    - CSV: channel,value,value,value,...
    - 简单格式: value1,value2,value3
    - 带标识: #CH0:1234,5678,9012
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.line_terminator = config.get("line_terminator", b"\n")
        self.delimiter = config.get("delimiter", ",")
        self.has_channel_prefix = config.get("has_channel_prefix", False)
        self.channel_prefix = config.get("channel_prefix", "#CH")
    
    def find_sync(self, buffer: bytes, start: int = 0) -> int:
        """ASCII 协议无需同步头"""
        return start
    
    def get_frame_size(self, buffer: bytes) -> int:
        """查找行结束符"""
        pos = buffer.find(self.line_terminator)
        if pos == -1:
            return 0
        return pos + len(self.line_terminator)
    
    def validate_frame(self, data: bytes) -> bool:
        """ASCII 协议总是有效（除非解析失败）"""
        return True
    
    def parse_frame(self, data: bytes) -> Optional[ParsedFrame]:
        """解析 ASCII 帧"""
        try:
            line = data.decode('utf-8').strip()
            if not line:
                return None
            
            channel_id = 0
            
            # 检查通道前缀
            if self.has_channel_prefix and line.startswith(self.channel_prefix):
                # 格式: #CH0:1234,5678,9012
                prefix_end = line.find(":")
                if prefix_end > 0:
                    channel_str = line[len(self.channel_prefix):prefix_end]
                    channel_id = int(channel_str)
                    line = line[prefix_end + 1:]
            
            # 解析数值
            parts = line.split(self.delimiter)
            values = []
            for part in parts:
                part = part.strip()
                if part:
                    try:
                        values.append(int(part))
                    except ValueError:
                        try:
                            values.append(int(float(part)))
                        except ValueError:
                            pass
            
            if not values:
                return None
            
            samples = np.array(values, dtype=np.uint16)
            return ParsedFrame(samples=samples, sequence=0, channel_id=channel_id)
        
        except Exception:
            return None


class ProtocolFactory:
    """协议工厂"""
    
    _parsers = {
        ProtocolType.BINARY_V2: BinaryV2Parser,
        ProtocolType.BINARY_CUSTOM: CustomBinaryParser,
        ProtocolType.ASCII: ASCIIParser,
    }
    
    @classmethod
    def create_parser(cls, protocol_type: ProtocolType, config: Optional[Dict[str, Any]] = None) -> ProtocolParser:
        """创建协议解析器"""
        parser_class = cls._parsers.get(protocol_type)
        if parser_class is None:
            raise ValueError(f"Unsupported protocol type: {protocol_type}")
        return parser_class(config)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> ProtocolParser:
        """从配置文件加载协议"""
        with open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        protocol_type_str = config.get("protocol_type", "binary_v2")
        protocol_type = ProtocolType(protocol_type_str)
        
        return cls.create_parser(protocol_type, config)
    
    @classmethod
    def save_to_file(cls, parser: ProtocolParser, filepath: str):
        """保存协议配置到文件"""
        config = parser.config.copy()
        
        # 确定协议类型
        if isinstance(parser, BinaryV2Parser):
            config["protocol_type"] = ProtocolType.BINARY_V2.value
        elif isinstance(parser, CustomBinaryParser):
            config["protocol_type"] = ProtocolType.BINARY_CUSTOM.value
            if hasattr(parser, 'format'):
                config["frame_format"] = parser.format.to_dict()
        elif isinstance(parser, ASCIIParser):
            config["protocol_type"] = ProtocolType.ASCII.value
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
