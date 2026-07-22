"""
固件配置管理 - V3.0

支持通过上位机配置固件参数：
- 采样率配置
- 帧长配置
- 固件版本检测
- 固件兼容性检查
- OTA 固件更新支持
"""

import struct
import time
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal
import serial


class FirmwareCommandType(Enum):
    """固件命令类型"""
    GET_VERSION = 0x01
    GET_CONFIG = 0x02
    SET_CONFIG = 0x03
    SET_SAMPLE_RATE = 0x10
    SET_FRAME_LENGTH = 0x11
    SET_CHANNEL_CONFIG = 0x12
    START_ACQUISITION = 0x20
    STOP_ACQUISITION = 0x21
    RESET_DEVICE = 0x30
    ENTER_BOOTLOADER = 0x40
    OTA_START = 0x50
    OTA_DATA = 0x51
    OTA_END = 0x52
    OTA_VERIFY = 0x53


@dataclass
class FirmwareVersion:
    """固件版本信息"""
    major: int
    minor: int
    patch: int
    build: int = 0
    commit_hash: str = ""
    build_date: str = ""
    
    def __str__(self) -> str:
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        if self.build > 0:
            version_str += f".{self.build}"
        if self.commit_hash:
            version_str += f" ({self.commit_hash[:8]})"
        return version_str
    
    def is_compatible_with(self, min_version: 'FirmwareVersion') -> bool:
        """检查版本兼容性"""
        if self.major != min_version.major:
            return self.major > min_version.major
        if self.minor != min_version.minor:
            return self.minor > min_version.minor
        return self.patch >= min_version.patch
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'FirmwareVersion':
        """从字节数据解析版本信息"""
        if len(data) < 8:
            return cls(0, 0, 0)
        
        major, minor, patch, build = struct.unpack("<HHHH", data[:8])
        
        commit_hash = ""
        build_date = ""
        
        if len(data) >= 16:
            # 尝试解析 commit hash (8 bytes)
            commit_hash = data[8:16].hex()
        
        if len(data) >= 32:
            # 尝试解析构建日期 (16 bytes, null-terminated string)
            try:
                build_date = data[16:32].decode('utf-8').rstrip('\x00')
            except UnicodeDecodeError:
                pass
        
        return cls(major, minor, patch, build, commit_hash, build_date)


@dataclass
class FirmwareConfig:
    """固件配置"""
    sample_rate: int = 10000  # Hz
    frame_length: int = 256  # 每帧采样点数
    channel_count: int = 1  # 通道数
    channel_mask: int = 0x01  # 通道使能掩码
    adc_resolution: int = 12  # ADC 分辨率（位）
    adc_vref: float = 3.3  # ADC 参考电压
    trigger_enabled: bool = False
    trigger_level: int = 2048
    trigger_edge: str = "rising"  # rising, falling, both
    
    def to_bytes(self) -> bytes:
        """转换为字节数据"""
        flags = 0
        if self.trigger_enabled:
            flags |= 0x01
        if self.trigger_edge == "rising":
            flags |= 0x02
        elif self.trigger_edge == "falling":
            flags |= 0x04
        elif self.trigger_edge == "both":
            flags |= 0x06
        
        return struct.pack(
            "<IHHHHHHH",
            self.sample_rate,
            self.frame_length,
            self.channel_count,
            self.channel_mask,
            self.adc_resolution,
            int(self.adc_vref * 1000),  # 转换为 mV
            self.trigger_level,
            flags,
        )
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'FirmwareConfig':
        """从字节数据解析配置"""
        if len(data) < 18:
            return cls()
        
        values = struct.unpack("<IHHHHHHH", data[:18])
        sample_rate, frame_length, channel_count, channel_mask, adc_resolution, vref_mv, trigger_level, flags = values
        
        trigger_enabled = bool(flags & 0x01)
        trigger_bits = (flags >> 1) & 0x03
        if trigger_bits == 1:
            trigger_edge = "rising"
        elif trigger_bits == 2:
            trigger_edge = "falling"
        elif trigger_bits == 3:
            trigger_edge = "both"
        else:
            trigger_edge = "rising"
        
        return cls(
            sample_rate=sample_rate,
            frame_length=frame_length,
            channel_count=channel_count,
            channel_mask=channel_mask,
            adc_resolution=adc_resolution,
            adc_vref=vref_mv / 1000.0,
            trigger_enabled=trigger_enabled,
            trigger_level=trigger_level,
            trigger_edge=trigger_edge,
        )


class FirmwareConfigManager(QObject):
    """固件配置管理器"""
    
    # 信号
    version_received = pyqtSignal(object)  # FirmwareVersion
    config_received = pyqtSignal(object)  # FirmwareConfig
    config_updated = pyqtSignal(bool)  # success
    error_occurred = pyqtSignal(str)  # error message
    ota_progress = pyqtSignal(int, int)  # current, total
    ota_completed = pyqtSignal(bool)  # success
    
    # 命令帧格式: [SYNC0=0xFC][SYNC1=0xCF][CMD][LEN][DATA...][CRC16]
    SYNC_BYTE_0 = 0xFC
    SYNC_BYTE_1 = 0xCF
    CMD_TIMEOUT = 2.0  # 命令超时时间（秒）
    
    def __init__(self, serial_port: serial.Serial, parent=None):
        super().__init__(parent)
        self._serial = serial_port
        self._response_buffer = bytearray()
        self._waiting_for_response = False
        self._current_command = None
        self._response_callback: Optional[Callable] = None
    
    def get_firmware_version(self) -> bool:
        """获取固件版本"""
        return self._send_command(FirmwareCommandType.GET_VERSION, callback=self._handle_version_response)
    
    def get_firmware_config(self) -> bool:
        """获取固件配置"""
        return self._send_command(FirmwareCommandType.GET_CONFIG, callback=self._handle_config_response)
    
    def set_firmware_config(self, config: FirmwareConfig) -> bool:
        """设置固件配置"""
        data = config.to_bytes()
        return self._send_command(FirmwareCommandType.SET_CONFIG, data, callback=self._handle_update_response)
    
    def set_sample_rate(self, sample_rate: int) -> bool:
        """设置采样率"""
        data = struct.pack("<I", sample_rate)
        return self._send_command(FirmwareCommandType.SET_SAMPLE_RATE, data, callback=self._handle_update_response)
    
    def set_frame_length(self, frame_length: int) -> bool:
        """设置帧长"""
        data = struct.pack("<H", frame_length)
        return self._send_command(FirmwareCommandType.SET_FRAME_LENGTH, data, callback=self._handle_update_response)
    
    def set_channel_config(self, channel_count: int, channel_mask: int) -> bool:
        """设置通道配置"""
        data = struct.pack("<HH", channel_count, channel_mask)
        return self._send_command(FirmwareCommandType.SET_CHANNEL_CONFIG, data, callback=self._handle_update_response)
    
    def start_acquisition(self) -> bool:
        """启动数据采集"""
        return self._send_command(FirmwareCommandType.START_ACQUISITION, callback=self._handle_update_response)
    
    def stop_acquisition(self) -> bool:
        """停止数据采集"""
        return self._send_command(FirmwareCommandType.STOP_ACQUISITION, callback=self._handle_update_response)
    
    def reset_device(self) -> bool:
        """复位设备"""
        return self._send_command(FirmwareCommandType.RESET_DEVICE)
    
    def enter_bootloader(self) -> bool:
        """进入 Bootloader 模式"""
        return self._send_command(FirmwareCommandType.ENTER_BOOTLOADER)
    
    def ota_update(self, firmware_data: bytes, progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """OTA 固件更新
        
        Args:
            firmware_data: 固件二进制数据
            progress_callback: 进度回调函数 (current, total)
        
        Returns:
            是否成功启动更新
        """
        # 1. 发送 OTA 开始命令
        total_size = len(firmware_data)
        start_data = struct.pack("<I", total_size)
        if not self._send_command(FirmwareCommandType.OTA_START, start_data, callback=self._handle_update_response):
            return False
        
        time.sleep(0.5)  # 等待固件准备
        
        # 2. 分块发送固件数据
        chunk_size = 256
        for offset in range(0, total_size, chunk_size):
            chunk = firmware_data[offset:offset + chunk_size]
            chunk_data = struct.pack("<I", offset) + chunk
            
            if not self._send_command(FirmwareCommandType.OTA_DATA, chunk_data, callback=self._handle_update_response):
                self.error_occurred.emit(f"OTA failed at offset {offset}")
                return False
            
            if progress_callback:
                progress_callback(offset + len(chunk), total_size)
            self.ota_progress.emit(offset + len(chunk), total_size)
            
            time.sleep(0.01)  # 避免发送过快
        
        # 3. 发送 OTA 结束命令
        if not self._send_command(FirmwareCommandType.OTA_END, callback=self._handle_update_response):
            return False
        
        time.sleep(0.5)
        
        # 4. 验证固件
        if not self._send_command(FirmwareCommandType.OTA_VERIFY, callback=self._handle_ota_verify_response):
            return False
        
        return True
    
    def _send_command(self, cmd_type: FirmwareCommandType, data: bytes = b"", callback: Optional[Callable] = None) -> bool:
        """发送命令到固件"""
        if not self._serial or not self._serial.is_open:
            self.error_occurred.emit("Serial port not open")
            return False
        
        try:
            # 构建命令帧
            cmd_byte = cmd_type.value
            length = len(data)
            
            # 计算 CRC (覆盖 CMD + LEN + DATA)
            payload = struct.pack("<BH", cmd_byte, length) + data
            crc = self._crc16_ccitt(payload)
            
            # 组装完整命令
            frame = bytes([self.SYNC_BYTE_0, self.SYNC_BYTE_1]) + payload + struct.pack("<H", crc)
            
            # 发送
            self._serial.write(frame)
            self._serial.flush()
            
            # 设置响应回调
            self._waiting_for_response = True
            self._current_command = cmd_type
            self._response_callback = callback
            
            return True
        
        except serial.SerialException as e:
            self.error_occurred.emit(f"Failed to send command: {e}")
            return False
    
    def process_response(self, timeout: float = CMD_TIMEOUT) -> bool:
        """处理响应（应在主循环中调用）"""
        if not self._waiting_for_response:
            return False
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if self._serial.in_waiting > 0:
                    chunk = self._serial.read(self._serial.in_waiting)
                    self._response_buffer.extend(chunk)
                    
                    # 尝试解析响应
                    if self._try_parse_response():
                        return True
                
                time.sleep(0.01)
            
            except serial.SerialException as e:
                self.error_occurred.emit(f"Failed to read response: {e}")
                return False
        
        # 超时
        self.error_occurred.emit(f"Command timeout: {self._current_command}")
        self._waiting_for_response = False
        return False
    
    def _try_parse_response(self) -> bool:
        """尝试从缓冲区解析响应"""
        # 查找同步头
        while len(self._response_buffer) >= 2:
            if self._response_buffer[0] == self.SYNC_BYTE_0 and self._response_buffer[1] == self.SYNC_BYTE_1:
                break
            self._response_buffer.pop(0)
        
        # 需要至少: SYNC(2) + CMD(1) + LEN(2) + CRC(2) = 7 bytes
        if len(self._response_buffer) < 7:
            return False
        
        # 读取长度
        length = struct.unpack("<H", self._response_buffer[3:5])[0]
        frame_size = 2 + 1 + 2 + length + 2  # SYNC + CMD + LEN + DATA + CRC
        
        if len(self._response_buffer) < frame_size:
            return False
        
        # 提取帧
        frame = bytes(self._response_buffer[:frame_size])
        self._response_buffer = self._response_buffer[frame_size:]
        
        # 验证 CRC
        payload = frame[2:-2]  # CMD + LEN + DATA
        crc_calc = self._crc16_ccitt(payload)
        crc_recv = struct.unpack("<H", frame[-2:])[0]
        
        if crc_calc != crc_recv:
            self.error_occurred.emit("Response CRC error")
            return False
        
        # 解析响应
        cmd = frame[2]
        data = frame[5:-2] if length > 0 else b""
        
        # 调用回调
        if self._response_callback:
            self._response_callback(cmd, data)
        
        self._waiting_for_response = False
        return True
    
    def _handle_version_response(self, cmd: int, data: bytes):
        """处理版本响应"""
        version = FirmwareVersion.from_bytes(data)
        self.version_received.emit(version)
    
    def _handle_config_response(self, cmd: int, data: bytes):
        """处理配置响应"""
        config = FirmwareConfig.from_bytes(data)
        self.config_received.emit(config)
    
    def _handle_update_response(self, cmd: int, data: bytes):
        """处理更新响应"""
        success = len(data) > 0 and data[0] == 0x00  # 0x00 = success
        self.config_updated.emit(success)
        if not success and len(data) > 1:
            error_code = data[1] if len(data) > 1 else 0xFF
            self.error_occurred.emit(f"Update failed with error code: 0x{error_code:02X}")
    
    def _handle_ota_verify_response(self, cmd: int, data: bytes):
        """处理 OTA 验证响应"""
        success = len(data) > 0 and data[0] == 0x00
        self.ota_completed.emit(success)
        if not success:
            self.error_occurred.emit("OTA verification failed")
    
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


def check_firmware_compatibility(current_version: FirmwareVersion, min_required: FirmwareVersion) -> tuple[bool, str]:
    """检查固件兼容性
    
    Returns:
        (is_compatible, message)
    """
    if current_version.is_compatible_with(min_required):
        return True, f"Firmware version {current_version} is compatible"
    else:
        return False, f"Firmware version {current_version} is too old. Minimum required: {min_required}. Please update firmware."
