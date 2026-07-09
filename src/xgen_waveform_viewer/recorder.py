"""
Background recorder for parsed ADC frames.

The GUI thread must not do per-sample file IO. This module keeps recording as a
small producer operation and moves the actual writes to a dedicated thread.
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


class FrameRecorder:
    """Write parsed frames to disk without blocking the producer thread."""

    def __init__(
        self,
        path: str | Path,
        record_format: RecordFormat,
        sample_rate_hz: int = ADC_SAMPLE_RATE_HZ,
        queue_size: int = 8192,
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
        if not self._accepting:
            return

        try:
            self._queue.put_nowait((int(seq), samples.copy()))
        except queue.Full:
            with self._lock:
                self.stats.queue_drop_count += 1
                if self.stats.first_dropped_seq is None:
                    self.stats.first_dropped_seq = int(seq)

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
                    seq, samples = item
                    self._write_frame(seq, samples)
                finally:
                    self._queue.task_done()
        except Exception as exc:  # pragma: no cover - defensive boundary for IO thread
            with self._lock:
                self.stats.writer_error = str(exc)

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
        finally:
            self._file.close()
            self._file = None

    def _write_metadata(self) -> None:
        metadata_path = self.path.with_suffix(self.path.suffix + ".meta.json")
        metadata = asdict(self.stats)
        metadata["complete"] = self.stats.complete
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
