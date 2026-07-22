"""
Background recorder for parsed ADC frames.

The GUI thread must not do per-sample file IO. This module keeps recording as a
small producer operation and moves the actual writes to a dedicated thread.

V2.2 增强:
- 支持暂停/恢复录制
- 支持自动分段录制（按时间或大小）
- 实时录制预览（时长、文件大小）
"""

from __future__ import annotations

import json
import queue
import struct
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np

from .config import ADC_SAMPLE_RATE_HZ, BIN_MAGIC, BIN_VERSION


RecordFormat = Literal["bin", "csv"]
_STOP = object()
_PAUSE = object()
_RESUME = object()


@dataclass
class RecorderStats:
    path: str
    format: str
    sample_rate_hz: int
    started_at: str
    stopped_at: str = ""
    elapsed_s: float = 0.0
    frame_count: int = 0
    sample_count: int = 0
    first_seq: int | None = None
    last_seq: int | None = None
    seq_gap_count: int = 0
    queue_drop_count: int = 0
    first_dropped_seq: int | None = None
    writer_error: str = ""
    serial_stats: dict[str, Any] = field(default_factory=dict)
    
    # V2.2 新增字段
    paused: bool = False
    pause_count: int = 0
    total_pause_duration: float = 0.0
    file_size_bytes: int = 0
    segment_index: int = 0

    @property
    def complete(self) -> bool:
        return (
            self.queue_drop_count == 0
            and self.seq_gap_count == 0
            and not self.writer_error
            and int(self.serial_stats.get("crc_errors", 0)) == 0
            and int(self.serial_stats.get("seq_gaps", 0)) == 0
            and int(self.serial_stats.get("resyncs", 0)) == 0
            and int(self.serial_stats.get("short_frames", 0)) == 0
        )
    
    @property
    def duration_display(self) -> str:
        """格式化显示时长"""
        if self.elapsed_s < 60:
            return f"{self.elapsed_s:.1f}s"
        elif self.elapsed_s < 3600:
            return f"{self.elapsed_s/60:.1f}min"
        else:
            return f"{self.elapsed_s/3600:.1f}h"
    
    @property
    def file_size_display(self) -> str:
        """格式化显示文件大小"""
        if self.file_size_bytes < 1024:
            return f"{self.file_size_bytes}B"
        elif self.file_size_bytes < 1024*1024:
            return f"{self.file_size_bytes/1024:.1f}KB"
        elif self.file_size_bytes < 1024*1024*1024:
            return f"{self.file_size_bytes/(1024*1024):.1f}MB"
        else:
            return f"{self.file_size_bytes/(1024*1024*1024):.2f}GB"


class FrameRecorder:
    """
    Write parsed frames to disk without blocking the producer thread.
    
    V2.2 新增功能:
    - pause(): 暂停录制
    - resume(): 恢复录制
    - get_preview(): 获取实时录制预览信息
    """

    def __init__(
        self,
        path: str | Path,
        record_format: RecordFormat,
        sample_rate_hz: int = ADC_SAMPLE_RATE_HZ,
        queue_size: int = 8192,
        auto_segment_duration: float = 0.0,  # 自动分段时长(秒)，0=禁用
        auto_segment_size: int = 0,  # 自动分段大小(MB)，0=禁用
    ):
        self.path = Path(path)
        self.record_format = record_format
        self.sample_rate_hz = sample_rate_hz
        self._queue: queue.Queue[tuple[int, np.ndarray] | object] = queue.Queue(maxsize=queue_size)
        self._accepting = False
        self._thread: threading.Thread | None = None
        self._file = None
        self._lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._started_perf = 0.0
        self._pause_start_time = 0.0
        self._paused = False
        
        # 自动分段参数
        self._auto_segment_duration = auto_segment_duration
        self._auto_segment_size = auto_segment_size * 1024 * 1024  # 转换为字节
        self._segment_index = 0
        
        self.stats = RecorderStats(
            path=str(self.path),
            format=record_format,
            sample_rate_hz=sample_rate_hz,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )

    def start(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.record_format == "csv":
            self._file = open(self.path, "w", encoding="utf-8", newline="")
            self._file.write("# ADC Waveform Recording\n")
            self._file.write(f"# sample_rate={self.sample_rate_hz}Hz\n")
            self._file.write("# frame_samples=dynamic\n")
            self._file.write("# format=uint16\n")
            self._file.write(f"# start_time={self.stats.started_at}\n")
            self._file.write("# seq,time_s,adc_value\n")
        else:
            self._file = open(self.path, "wb")
            header = struct.pack(
                "<4sIIIIq",
                BIN_MAGIC,
                BIN_VERSION,
                0,
                self.sample_rate_hz,
                0,
                int(time.time()),
            )
            self._file.write(header)

        self._accepting = True
        self._stop_requested.clear()
        self._started_perf = time.perf_counter()
        self._thread = threading.Thread(target=self._run, name="adc-frame-recorder", daemon=True)
        self._thread.start()

    def enqueue(self, seq: int, samples: np.ndarray) -> None:
        if not self._accepting or self._paused:
            return

        try:
            self._queue.put_nowait((int(seq), samples.copy()))
        except queue.Full:
            with self._lock:
                self.stats.queue_drop_count += 1
                if self.stats.first_dropped_seq is None:
                    self.stats.first_dropped_seq = int(seq)
    
    def pause(self) -> bool:
        """
        暂停录制
        
        返回: 操作是否成功
        """
        if not self._accepting or self._paused:
            return False
        
        self._paused = True
        self._pause_start_time = time.perf_counter()
        
        with self._lock:
            self.stats.paused = True
            self.stats.pause_count += 1
        
        try:
            self._queue.put_nowait(_PAUSE)
        except queue.Full:
            pass
        
        return True
    
    def resume(self) -> bool:
        """
        恢复录制
        
        返回: 操作是否成功
        """
        if not self._accepting or not self._paused:
            return False
        
        pause_duration = time.perf_counter() - self._pause_start_time
        self._paused = False
        
        with self._lock:
            self.stats.paused = False
            self.stats.total_pause_duration += pause_duration
        
        try:
            self._queue.put_nowait(_RESUME)
        except queue.Full:
            pass
        
        return True
    
    def is_paused(self) -> bool:
        """检查是否处于暂停状态"""
        return self._paused
    
    def get_preview(self) -> dict:
        """
        获取录制预览信息（实时）
        
        返回: {
            'duration': 录制时长(秒),
            'file_size': 文件大小(字节),
            'frame_count': 帧数,
            'sample_count': 采样点数,
            'paused': 是否暂停,
            'segment_index': 当前分段索引
        }
        """
        with self._lock:
            elapsed = time.perf_counter() - self._started_perf - self.stats.total_pause_duration
            
            # 估算文件大小
            if self._file:
                try:
                    file_size = self._file.tell()
                except:
                    file_size = 0
            else:
                file_size = 0
            
            return {
                'duration': elapsed,
                'file_size': file_size,
                'frame_count': self.stats.frame_count,
                'sample_count': self.stats.sample_count,
                'paused': self._paused,
                'segment_index': self._segment_index,
            }

    def stop(self, serial_stats: dict[str, Any] | None = None, timeout_s: float = 10.0) -> RecorderStats:
        self._accepting = False
        self._stop_requested.set()
        try:
            self._queue.put_nowait(_STOP)
        except queue.Full:
            pass
        if self._thread:
            self._thread.join(timeout=timeout_s)
            if self._thread.is_alive():
                with self._lock:
                    self.stats.writer_error = "recorder thread did not stop before timeout"

        self.stats.stopped_at = datetime.now().isoformat(timespec="seconds")
        self.stats.elapsed_s = time.perf_counter() - self._started_perf
        if serial_stats:
            self.stats.serial_stats = dict(serial_stats)

        self._close_file()
        self._write_metadata()
        return self.stats

    def snapshot(self) -> RecorderStats:
        with self._lock:
            return RecorderStats(**asdict(self.stats))

    def _run(self) -> None:
        try:
            while True:
                try:
                    item = self._queue.get(timeout=0.1)
                except queue.Empty:
                    if self._stop_requested.is_set():
                        return
                    continue
                try:
                    if item is _STOP:
                        if self._queue.empty():
                            return
                        continue
                    elif item is _PAUSE:
                        # 暂停命令 - 刷新缓冲区
                        if self._file:
                            self._file.flush()
                        continue
                    elif item is _RESUME:
                        # 恢复命令 - 无需特殊处理
                        continue
                    
                    seq, samples = item
                    
                    # 检查是否需要自动分段
                    if self._should_create_segment():
                        self._create_new_segment()
                    
                    self._write_frame(seq, samples)
                finally:
                    self._queue.task_done()
        except Exception as exc:  # pragma: no cover - defensive boundary for IO thread
            with self._lock:
                self.stats.writer_error = str(exc)
    
    def _should_create_segment(self) -> bool:
        """检查是否应该创建新的分段文件"""
        if self._segment_index == 0:
            return False  # 第一个文件不需要分段
        
        # 按时长分段
        if self._auto_segment_duration > 0:
            elapsed = time.perf_counter() - self._started_perf - self.stats.total_pause_duration
            if elapsed >= self._auto_segment_duration * (self._segment_index + 1):
                return True
        
        # 按大小分段
        if self._auto_segment_size > 0 and self._file:
            try:
                current_size = self._file.tell()
                if current_size >= self._auto_segment_size:
                    return True
            except:
                pass
        
        return False
    
    def _create_new_segment(self):
        """创建新的分段文件"""
        # 关闭当前文件
        self._close_file()
        
        # 生成新文件名
        self._segment_index += 1
        base_path = self.path.parent / self.path.stem
        new_path = Path(f"{base_path}_part{self._segment_index:03d}{self.path.suffix}")
        self.path = new_path
        
        # 更新统计
        with self._lock:
            self.stats.path = str(self.path)
            self.stats.segment_index = self._segment_index
        
        # 打开新文件
        if self.record_format == "csv":
            self._file = open(self.path, "w", encoding="utf-8", newline="")
            self._file.write("# ADC Waveform Recording (Segment)\n")
            self._file.write(f"# segment_index={self._segment_index}\n")
            self._file.write(f"# sample_rate={self.sample_rate_hz}Hz\n")
            self._file.write("# frame_samples=dynamic\n")
            self._file.write("# format=uint16\n")
            self._file.write(f"# start_time={datetime.now().isoformat(timespec='seconds')}\n")
            self._file.write("# seq,time_s,adc_value\n")
        else:
            self._file = open(self.path, "wb")
            header = struct.pack(
                "<4sIIIIq",
                BIN_MAGIC,
                BIN_VERSION,
                0,
                self.sample_rate_hz,
                self._segment_index,
                int(time.time()),
            )
            self._file.write(header)

    def _write_frame(self, seq: int, samples: np.ndarray) -> None:
        if self._file is None:
            return

        samples_count = len(samples)
        with self._lock:
            if self.stats.first_seq is None:
                self.stats.first_seq = seq
            elif self.stats.last_seq is not None and seq != ((self.stats.last_seq + 1) & 0xFFFFFFFF):
                self.stats.seq_gap_count += 1
            self.stats.last_seq = seq
            base_sample = self.stats.sample_count
            self.stats.frame_count += 1
            self.stats.sample_count += samples_count

        if self.record_format == "csv":
            lines = []
            for i, value in enumerate(samples):
                t = (base_sample + i) / self.sample_rate_hz
                lines.append(f"{seq},{t:.8f},{int(value)}\n")
            self._file.writelines(lines)
        else:
            self._file.write(struct.pack("<IH", seq, samples_count))
            self._file.write(samples.tobytes())

    def _close_file(self) -> None:
        if self._file is None:
            return

        try:
            self._file.flush()
            if self.record_format == "bin":
                self._file.seek(8)
                self._file.write(struct.pack("<I", self.stats.frame_count))
                self._file.flush()
            
            # 更新文件大小统计
            try:
                file_size = self._file.tell()
                with self._lock:
                    self.stats.file_size_bytes = file_size
            except:
                pass
        finally:
            self._file.close()
            self._file = None

    def _write_metadata(self) -> None:
        metadata_path = self.path.with_suffix(self.path.suffix + ".meta.json")
        metadata = asdict(self.stats)
        metadata["complete"] = self.stats.complete
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
