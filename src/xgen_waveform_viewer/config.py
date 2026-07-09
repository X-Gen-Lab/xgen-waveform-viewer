"""
xgen-waveform-viewer - 配置常量
与固件 adc_stream.h 保持一致
"""

# UART 参数
UART_BAUDRATE = 460_800
UART_DATA_BITS = 8
UART_STOP_BITS = 1
UART_PARITY = "N"

# 帧协议
SYNC_BYTE_0 = 0xA5
SYNC_BYTE_1 = 0x5A
FRAME_SAMPLES = 64           # 默认每帧采样点数 (实际由帧头 CNT 字段动态决定)
SAMPLE_BYTES = 2             # uint16
META_BYTES = 6               # seq(4) + samples_count(2)
CRC_BYTES = 2                # CRC-16 CCITT
FRAME_HEADER_SIZE = 2 + META_BYTES  # sync(2) + seq(4) + cnt(2) = 8 bytes (读取 CNT 前需要的最小字节数)
FRAME_PAYLOAD_SIZE = FRAME_SAMPLES * SAMPLE_BYTES  # 默认 payload 字节数
FRAME_DATA_SIZE = META_BYTES + FRAME_PAYLOAD_SIZE  # 默认 CRC 计算范围
FRAME_TOTAL_SIZE = 2 + FRAME_DATA_SIZE + CRC_BYTES # 默认整帧字节数
MAX_FRAME_SAMPLES = 4096     # 允许的最大采样点数/帧 (防止异常 CNT 值)

# ADC 参数
ADC_SAMPLE_RATE_HZ = 400     # 实际采样率 (与固件 ADC_STREAM_ACTUAL_RATE_HZ 一致)
ADC_RESOLUTION_BITS = 12
ADC_MAX_VALUE = (1 << ADC_RESOLUTION_BITS) - 1  # 4095

# 显示参数
DISPLAY_DURATION_SEC = 5.0   # 波形窗口显示时长 (秒)
DISPLAY_BUFFER_SIZE = int(ADC_SAMPLE_RATE_HZ * DISPLAY_DURATION_SEC)

# 数据保存
BIN_MAGIC = b"ADCW"          # .bin 文件 magic
BIN_VERSION = 2              # v2: 每帧含 seq + cnt + samples

# 默认值
DEFAULT_PORT = ""
DEFAULT_BAUDRATE = UART_BAUDRATE
