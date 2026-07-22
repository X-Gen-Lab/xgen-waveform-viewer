"""
串口读取与帧解析线程
在后台线程中持续读取 UART 数据，解析帧并通过 Qt Signal 发送给 GUI

帧格式 (v2):
  [SYNC0=0xA5][SYNC1=0x5A]  2B  同步头
  [SEQ]                      4B  uint32 LE 帧序列号
  [SAMPLES_CNT]              2B  uint16 LE 采样点数 (动态, 决定帧大小)
  [SAMPLES]              CNT×2B  CNT × uint16 LE
  [CRC16]                    2B  CRC-16-CCITT (覆盖 META+SAMPLES)
  Total: 8 + CNT*2 + 2 bytes (动态)

V2.3: 添加日志记录功能
"""

import time
import struct
import threading
from collections.abc import Callable
import numpy as np
import serial
from PyQt6.QtCore import QThread, pyqtSignal

from .config import (
    SYNC_BYTE_0,
    SYNC_BYTE_1,
    META_BYTES,
    CRC_BYTES,
    FRAME_HEADER_SIZE,
    MAX_FRAME_SAMPLES,
    UART_BAUDRATE,
)
from .logger import get_logger

# 最小帧大小: sync(2) + meta(6) + crc(2) = 10 bytes (CNT=0 时)
_MIN_FRAME_SIZE = FRAME_HEADER_SIZE + CRC_BYTES

# CNT 字段在帧内的偏移: sync(2) + seq(4) = 6
_CNT_OFFSET = 2 + 4


def crc16_ccitt(data: bytes) -> int:
    """CRC-16-CCITT, poly=0x1021, init=0xFFFF (与固件一致)"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def _frame_total_size(samples_cnt: int) -> int:
    """根据采样点数计算帧总大小"""
    return FRAME_HEADER_SIZE + samples_cnt * 2 + CRC_BYTES


class SerialReader(QThread):
    """串口读取线程，解析 ADC 帧数据（动态帧长 + CRC 验证 + 序列号跟踪）"""

    # 信号: (numpy uint16 数组, 序列号)
    frame_ready = pyqtSignal(object, int)
    # 信号: 统计信息 (帧率, 采样率, 总帧数, CRC错误数, 序列号间隙数, 重同步次数, 短帧数)
    stats_updated = pyqtSignal(float, float, int, int, int, int, int)
    # 信号: 错误信息
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._serial: serial.Serial | None = None
        self._running = False
        self._port = ""
        self._baudrate = UART_BAUDRATE
        self._databits = serial.EIGHTBITS
        self._stopbits = serial.STOPBITS_ONE
        self._parity = serial.PARITY_NONE
        self._record_sink: Callable[[int, np.ndarray], None] | None = None
        self._record_sink_lock = threading.Lock()

        # 统计
        self._frame_count = 0
        self._crc_error_count = 0
        self._seq_gap_count = 0
        self._resync_count = 0
        self._short_frame_count = 0
        self._last_seq = -1
        self._stats_time = 0.0
        self._stats_frames = 0
        self._stats_samples = 0
        
        # V2.3: 日志记录
        self._logger = get_logger()

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def configure(self, port: str, baudrate: int = UART_BAUDRATE,
                  databits: int = serial.EIGHTBITS,
                  stopbits: float = serial.STOPBITS_ONE,
                  parity: str = serial.PARITY_NONE):
        self._port = port
        self._baudrate = baudrate
        self._databits = databits
        self._stopbits = stopbits
        self._parity = parity

    def set_record_sink(self, sink: Callable[[int, np.ndarray], None] | None):
        """Set a thread-safe frame sink used by the recorder.

        The sink is called from the serial reader thread before the GUI signal is
        emitted, so recording is not delayed by paint/event handling.
        """
        with self._record_sink_lock:
            self._record_sink = sink

    def _parse_frame(self, raw: bytes, samples_cnt: int) -> tuple[np.ndarray, int] | None:
        """
        解析一帧数据 (不含同步头)
        raw 长度 = META + SAMPLES + CRC
        返回 (samples, seq) 或 None (CRC 错误)
        """
        payload_size = samples_cnt * 2
        data_size = META_BYTES + payload_size  # META + SAMPLES (CRC 计算范围)

        # CRC 验证: 覆盖 META + SAMPLES
        crc_calc = crc16_ccitt(raw[:data_size])
        crc_recv = struct.unpack("<H", raw[data_size : data_size + CRC_BYTES])[0]

        if crc_calc != crc_recv:
            return None

        # 解析 META
        seq = struct.unpack("<I", raw[:4])[0]

        # 解析 SAMPLES
        samples = np.frombuffer(raw[META_BYTES : META_BYTES + payload_size], dtype=np.uint16).copy()

        return samples, seq

    def _try_extract_frame(self, buf: bytearray) -> tuple[bool, int]:
        """
        尝试从 buf 起始位置提取一帧。
        返回 (success, consumed_bytes)
        - success=True: 成功解析并发送一帧, consumed = 帧总大小
        - success=False, consumed>0: CRC 失败但帧头有效, consumed = 建议丢弃字节数
        - success=False, consumed=0: 数据不足或 CNT 无效, 需要更多数据或跳过
        """
        buf_len = len(buf)

        # 至少需要 FRAME_HEADER_SIZE 字节才能读取 CNT
        if buf_len < FRAME_HEADER_SIZE:
            return False, 0

        # 验证同步头
        if buf[0] != SYNC_BYTE_0 or buf[1] != SYNC_BYTE_1:
            return False, -1  # -1 表示同步头不匹配

        # 读取 CNT (动态帧大小)
        samples_cnt = struct.unpack("<H", buf[_CNT_OFFSET : _CNT_OFFSET + 2])[0]

        # 合理性检查
        if samples_cnt == 0 or samples_cnt > MAX_FRAME_SAMPLES:
            return False, -1  # CNT 异常，视为无效帧头

        frame_size = _frame_total_size(samples_cnt)
        next_sync = buf.find(bytes([SYNC_BYTE_0, SYNC_BYTE_1]), 2)
        if next_sync != -1 and next_sync < frame_size:
            self._short_frame_count += 1
            self._resync_count += 1
            # V2.3: 记录短帧事件
            self._logger.log_frame_event("short_frame", details={"expected_size": frame_size, "found_sync_at": next_sync})
            return False, next_sync

        # 数据不足，等待更多
        if buf_len < frame_size:
            return False, 0

        # 提取帧体 (跳过 2 字节同步头)
        body = bytes(buf[2:frame_size])
        result = self._parse_frame(body, samples_cnt)

        if result is not None:
            samples, seq = result
            self._process_frame(samples, seq)
            return True, frame_size
        else:
            # CRC 失败
            self._crc_error_count += 1
            # V2.3: 记录 CRC 错误
            self._logger.log_crc_error()
            return False, 1

    def run(self):
        """线程主循环"""
        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=self._databits,
                stopbits=self._stopbits,
                parity=self._parity,
                timeout=0.05,
            )
            # 增大内部读缓冲区，减少高波特率下的 FIFO 溢出
            try:
                self._serial.set_buffer_size(rx_size=65536)
            except (AttributeError, ValueError):
                pass  # 部分平台/驱动不支持
            # V2.3: 记录串口打开成功
            self._logger.log_serial_event("opened", details={
                "port": self._port,
                "baudrate": self._baudrate
            })
        except serial.SerialException as e:
            self.error_occurred.emit(f"串口打开失败: {e}")
            self._logger.error(f"Failed to open serial port {self._port}: {e}", 
                             category="serial", exc_info=True)
            return

        self._running = True
        self._frame_count = 0
        self._crc_error_count = 0
        self._seq_gap_count = 0
        self._resync_count = 0
        self._short_frame_count = 0
        self._last_seq = -1
        self._stats_time = time.perf_counter()
        self._stats_frames = 0
        self._stats_samples = 0

        buf = bytearray()
        synced = False

        while self._running:
            try:
                # 积极读取：优先 read_all() 一次取尽所有缓冲数据
                chunk = self._serial.read_all() if self._serial.in_waiting else self._serial.read(4096)
                if chunk:
                    buf.extend(chunk)
                else:
                    continue

                # ── 帧解析状态机 ──
                while True:
                    if not synced:
                        # ── 搜索同步头 ──
                        if len(buf) < _MIN_FRAME_SIZE:
                            break

                        idx = buf.find(bytes([SYNC_BYTE_0, SYNC_BYTE_1]))
                        if idx == -1:
                            # 没找到同步头，丢弃大部分数据（保留最后 1 字节防止截断）
                            if len(buf) > 1:
                                del buf[:-1]
                            break
                        if idx > 0:
                            del buf[:idx]
                        if len(buf) < _MIN_FRAME_SIZE:
                            break

                        # 尝试提取帧
                        success, consumed = self._try_extract_frame(buf)

                        if success:
                            del buf[:consumed]
                            synced = True
                        elif consumed > 0:
                            # CRC 失败，跳过此帧继续搜索
                            del buf[:consumed]
                        elif consumed == -1:
                            # 同步头不匹配或 CNT 异常，跳 1 字节继续搜索
                            del buf[:1]
                        else:
                            # 数据不足，等待更多
                            break

                    else:
                        # ── 已同步: 验证帧边界 ──
                        if len(buf) < 2:
                            break

                        if buf[0] == SYNC_BYTE_0 and buf[1] == SYNC_BYTE_1:
                            # 同步头正确，尝试提取帧
                            success, consumed = self._try_extract_frame(buf)

                            if success:
                                del buf[:consumed]
                            elif consumed > 0:
                                # CRC 失败 → 同步丢失
                                synced = False
                                del buf[:consumed]
                            elif consumed == 0:
                                # 数据不足，等待更多
                                break
                            else:
                                # CNT 异常 → 同步丢失
                                synced = False
                                self._resync_count += 1
                                del buf[:1]
                        else:
                            # 同步头不匹配 → 帧对齐丢失
                            synced = False
                            self._resync_count += 1
                            # V2.3: 记录重同步事件
                            self._logger.log_resync("sync_header_mismatch")
                            del buf[:1]

                    # 定期发送统计信息 (每 0.5 秒)
                    now = time.perf_counter()
                    elapsed = now - self._stats_time
                    if elapsed >= 0.5:
                        fps = self._stats_frames / elapsed
                        sample_rate_hz = self._stats_samples / elapsed
                        self.stats_updated.emit(
                            fps,
                            sample_rate_hz,
                            self._frame_count,
                            self._crc_error_count,
                            self._seq_gap_count,
                            self._resync_count,
                            self._short_frame_count,
                        )
                        self._stats_time = now
                        self._stats_frames = 0
                        self._stats_samples = 0

            except serial.SerialException as e:
                self.error_occurred.emit(f"串口读取错误: {e}")
                break

        # 清理
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None

    def _process_frame(self, samples: np.ndarray, seq: int):
        """处理一帧有效数据：序列号检查 + 发送信号"""
        self._frame_count += 1
        self._stats_frames += 1
        self._stats_samples += len(samples)

        # 序列号间隙检测
        if self._last_seq >= 0 and seq != (self._last_seq + 1) & 0xFFFFFFFF:
            self._seq_gap_count += 1
            # V2.3: 记录序列号间隙
            expected = (self._last_seq + 1) & 0xFFFFFFFF
            gap = (seq - expected) & 0xFFFFFFFF
            self._logger.log_seq_gap(expected, seq, gap)
        self._last_seq = seq

        with self._record_sink_lock:
            record_sink = self._record_sink
        if record_sink is not None:
            record_sink(seq, samples)

        self.frame_ready.emit(samples, seq)

    def stop(self):
        """停止读取线程"""
        self._running = False
        self.wait(2000)

    def get_stats(self) -> dict:
        return {
            "frames": self._frame_count,
            "crc_errors": self._crc_error_count,
            "seq_gaps": self._seq_gap_count,
            "resyncs": self._resync_count,
            "short_frames": self._short_frame_count,
        }
