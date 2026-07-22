# xgen-waveform-viewer V3.0 发布说明

## 🎉 重大更新：专业化与扩展

V3.0 版本是一个里程碑式的更新，引入了三大核心功能模块，使 xgen-waveform-viewer 从单通道工具升级为专业级多通道数据采集与分析平台。

---

## 📅 发布信息

- **版本号**: V3.0.0
- **发布日期**: 2026-07-22
- **重要程度**: ⭐⭐⭐⭐⭐ 重大更新
- **兼容性**: 需要固件版本 >= 3.0.0

---

## 🚀 核心功能

### 1️⃣ 多通道支持

#### 功能概述
支持同时采集和显示多个 ADC 通道数据，每个通道可独立配置和管理。

#### 主要特性
- ✅ **多通道数据模型** - 重构数据架构，支持最多 16 个独立通道
- ✅ **通道独立配置** - 每通道独立设置标签、颜色、可见性
- ✅ **通道分组显示** - 支持按功能将通道分组管理
- ✅ **独立 Y 轴设置** - 每通道可设置 Y 轴偏移和缩放
- ✅ **配置持久化** - 通道配置自动保存和恢复

#### 使用示例
```python
from xgen_waveform_viewer.multi_channel import MultiChannelManager

# 创建多通道管理器
manager = MultiChannelManager()

# 添加通道
ch0 = manager.add_channel(0, label="传感器A", color="#00ff00")
ch1 = manager.add_channel(1, label="传感器B", color="#ff0000")

# 更新通道配置
manager.update_channel_config(0, visible=True, group="温度传感器")
manager.update_channel_config(1, visible=True, group="压力传感器")

# 添加数据
manager.append_data(channel_id=0, samples=data_ch0, seq=seq_num, timestamp=t)
manager.append_data(channel_id=1, samples=data_ch1, seq=seq_num, timestamp=t)
```

#### UI 操作
1. 打开 `视图` → `通道管理面板`
2. 点击 `+ 添加通道` 创建新通道
3. 在表格中编辑通道标签、颜色、分组
4. 使用复选框切换通道可见性

---

### 2️⃣ 协议扩展

#### 功能概述
支持多种数据传输协议，可通过配置文件自定义帧格式，无需修改代码即可适配不同设备。

#### 支持的协议类型

##### Binary V2（默认）
现有的二进制协议，完全向后兼容。

**帧格式:**
```
[0xA5][0x5A] - 同步头
[SEQ:4B] - 序列号 (uint32 LE)
[CNT:2B] - 采样点数 (uint16 LE)
[SAMPLES:CNT×2B] - 采样数据 (uint16 LE)
[CRC:2B] - CRC-16-CCITT
```

##### Binary Custom（自定义二进制）
通过 JSON 配置文件定义帧格式。

**配置示例:**
```json
{
  "protocol_type": "binary_custom",
  "frame_format": {
    "sync_bytes": "AA55",
    "meta_size": 8,
    "has_crc": true,
    "crc_poly": "0x1021",
    "crc_init": "0xFFFF",
    "sample_size": 2,
    "endianness": "little",
    "has_sequence": true,
    "sequence_offset": 0,
    "sequence_size": 4,
    "has_channel_id": true,
    "channel_id_offset": 4,
    "sample_count_offset": 6,
    "max_samples": 2048
  }
}
```

##### ASCII Text（文本协议）
支持 CSV 格式和带通道标识的文本协议。

**格式示例:**
```
# 简单 CSV
1234,5678,9012

# 带通道前缀
#CH0:1234,5678,9012
#CH1:2345,6789,0123
```

**配置示例:**
```json
{
  "protocol_type": "ascii",
  "line_terminator": "\n",
  "delimiter": ",",
  "has_channel_prefix": true,
  "channel_prefix": "#CH"
}
```

#### 使用示例
```python
from xgen_waveform_viewer.protocol import ProtocolFactory, ProtocolType

# 方法 1: 直接创建
parser = ProtocolFactory.create_parser(ProtocolType.BINARY_V2)

# 方法 2: 从配置文件加载
parser = ProtocolFactory.load_from_file("my_protocol.json")

# 方法 3: 使用自定义配置
config = {
    "protocol_type": "ascii",
    "delimiter": ",",
    "has_channel_prefix": True
}
parser = ProtocolFactory.create_parser(ProtocolType.ASCII, config)

# 解析数据
result = parser.parse_frame(frame_data)
if result:
    print(f"Channel {result.channel_id}: {result.samples}")
```

#### UI 操作
1. 打开 `工具` → `协议配置`
2. 选择协议类型
3. 根据协议类型配置参数
4. 点击 `应用配置`
5. 可选：导出配置文件供后续使用

---

### 3️⃣ 固件配置与管理

#### 功能概述
通过上位机直接配置固件参数，无需重新编译和烧录固件。支持 OTA（Over-The-Air）远程固件更新。

#### 主要特性

##### 固件版本检测
- 自动获取固件版本信息
- 显示版本号、构建日期、Git commit hash
- 兼容性检查和警告

##### 固件参数配置
可配置的参数包括：
- **采样率** (100 Hz - 1 MHz)
- **帧长** (1 - 4096 采样点/帧)
- **通道配置** (通道数、通道掩码)
- **ADC 参数** (分辨率、参考电压)
- **触发配置** (触发使能、触发电平、触发边沿)

##### OTA 固件更新
- 通过串口更新固件
- 实时显示更新进度
- 自动验证固件完整性
- 更新失败自动回滚

#### 固件命令协议

**命令帧格式:**
```
[0xFC][0xCF] - 命令同步头
[CMD:1B] - 命令类型
[LEN:2B] - 数据长度 (uint16 LE)
[DATA:LEN] - 命令数据
[CRC:2B] - CRC-16-CCITT
```

**支持的命令:**
| 命令 | 代码 | 说明 |
|------|------|------|
| GET_VERSION | 0x01 | 获取固件版本 |
| GET_CONFIG | 0x02 | 获取当前配置 |
| SET_CONFIG | 0x03 | 设置配置参数 |
| SET_SAMPLE_RATE | 0x10 | 设置采样率 |
| SET_FRAME_LENGTH | 0x11 | 设置帧长 |
| SET_CHANNEL_CONFIG | 0x12 | 设置通道配置 |
| START_ACQUISITION | 0x20 | 启动数据采集 |
| STOP_ACQUISITION | 0x21 | 停止数据采集 |
| RESET_DEVICE | 0x30 | 复位设备 |
| ENTER_BOOTLOADER | 0x40 | 进入 Bootloader |
| OTA_START | 0x50 | 开始 OTA 更新 |
| OTA_DATA | 0x51 | 发送固件数据块 |
| OTA_END | 0x52 | 结束 OTA 更新 |
| OTA_VERIFY | 0x53 | 验证固件 |

#### 使用示例
```python
from xgen_waveform_viewer.firmware_config import (
    FirmwareConfigManager, FirmwareConfig, FirmwareVersion
)

# 创建固件配置管理器
manager = FirmwareConfigManager(serial_port)

# 获取固件版本
manager.get_firmware_version()
# 等待响应...
# 信号: version_received(FirmwareVersion)

# 读取固件配置
manager.get_firmware_config()
# 信号: config_received(FirmwareConfig)

# 设置采样率
manager.set_sample_rate(50000)  # 50 kHz
# 信号: config_updated(bool)

# OTA 更新固件
with open("firmware.bin", "rb") as f:
    firmware_data = f.read()

manager.ota_update(firmware_data)
# 信号: ota_progress(current, total)
# 信号: ota_completed(success)
```

#### UI 操作
1. 打开 `工具` → `固件配置`
2. 点击 `获取版本信息` 查看当前固件版本
3. 点击 `读取配置` 获取当前固件参数
4. 修改参数后点击 `写入配置`
5. OTA 更新：
   - 点击 `选择固件文件` 选择 .bin 文件
   - 点击 `开始更新`
   - 等待更新完成（请勿断开连接）

---

## 🛠️ 技术实现

### 架构改进

#### 模块化设计
- `multi_channel.py` - 多通道数据管理
- `protocol.py` - 协议解析框架
- `firmware_config.py` - 固件配置管理
- `channel_panel.py` - 通道管理 UI
- `protocol_config_panel.py` - 协议配置 UI
- `firmware_panel.py` - 固件配置 UI

#### 数据模型
```python
@dataclass
class ChannelConfig:
    channel_id: int
    label: str
    color: str
    visible: bool
    y_offset: float
    y_scale: float
    group: str

@dataclass
class ChannelData:
    channel_id: int
    samples: np.ndarray
    timestamps: np.ndarray
    sequence_numbers: List[int]
```

#### 协议解析器基类
```python
class ProtocolParser(ABC):
    @abstractmethod
    def parse_frame(self, data: bytes) -> Optional[ParsedFrame]
    
    @abstractmethod
    def find_sync(self, buffer: bytes, start: int = 0) -> int
    
    @abstractmethod
    def get_frame_size(self, buffer: bytes) -> int
    
    @abstractmethod
    def validate_frame(self, data: bytes) -> bool
```

---

## 📦 新增文件

### 核心模块
- `src/xgen_waveform_viewer/multi_channel.py`
- `src/xgen_waveform_viewer/protocol.py`
- `src/xgen_waveform_viewer/firmware_config.py`

### UI 面板
- `src/xgen_waveform_viewer/channel_panel.py`
- `src/xgen_waveform_viewer/protocol_config_panel.py`
- `src/xgen_waveform_viewer/firmware_panel.py`

### 文档和示例
- `docs/RELEASE_NOTES_V3.0.md`
- `docs/V3.0_QUICK_GUIDE.md`
- `examples/v3.0_multi_channel_example.py`
- `examples/v3.0_custom_protocol_example.py`
- `examples/v3.0_firmware_config_example.py`

### 配置文件示例
- `examples/protocols/binary_custom_example.json`
- `examples/protocols/ascii_example.json`

---

## 🔄 向后兼容性

### 完全兼容 V2.x
- 默认使用 Binary V2 协议，现有设备无需修改
- 单通道模式作为多通道的特例（通道 0）
- 现有录制文件格式保持兼容

### 升级建议
1. **固件升级**: 建议升级到 V3.0+ 固件以使用新功能
2. **配置迁移**: 自动保留原有设置
3. **数据文件**: 新格式支持多通道，但仍可读取旧格式

---

## 📊 性能优化

### 多通道性能
- **内存管理**: 每通道独立缓冲区，自动限制大小
- **渲染优化**: 仅渲染可见通道，降低 CPU 负载
- **数据传输**: 支持通道多路复用，提高带宽利用率

### 协议解析性能
- **零拷贝解析**: 使用 `numpy.frombuffer` 避免数据复制
- **快速同步**: 优化的同步头搜索算法
- **批量处理**: 支持批量解析多个帧

---

## 🐛 已知问题与限制

### 当前限制
1. **最大通道数**: 16 个通道（硬件限制）
2. **OTA 更新**: 仅支持串口方式，更新时间取决于波特率
3. **TCP/UDP 数据源**: 计划在 V3.1 实现

### 已知问题
无重大已知问题。

---

## 🔮 下一步计划 (V3.1)

### 计划功能
- [ ] TCP/UDP 网络数据源
- [ ] 蓝牙 BLE 支持
- [ ] 多设备同步采集
- [ ] 云端数据存储
- [ ] 远程监控功能

---

## 📝 更新日志

### V3.0.0 (2026-07-22)

#### 新增功能
- ✨ 多通道支持（最多 16 通道）
- ✨ 协议扩展框架（支持自定义协议）
- ✨ ASCII 文本协议支持
- ✨ 固件配置管理
- ✨ OTA 固件更新
- ✨ 固件版本检测与兼容性检查
- ✨ 通道管理 UI 面板
- ✨ 协议配置 UI 面板
- ✨ 固件配置 UI 面板

#### 改进
- 🚀 重构数据模型支持多通道
- 🚀 优化协议解析性能
- 🚀 改进 UI 布局和交互
- 📚 完善文档和示例代码

#### 修复
- 🐛 修复多通道数据同步问题
- 🐛 修复协议解析边界情况
- 🐛 改进错误处理和日志记录

---

## 🙏 致谢

感谢所有用户的反馈和建议！V3.0 的许多功能都来自于社区的需求。

特别感谢：
- 提出多通道需求的用户们
- 贡献自定义协议配置的开发者
- 测试 OTA 更新功能的早期用户

---

## 📞 支持与反馈

- **GitHub Issues**: https://github.com/X-Gen-Lab/xgen-waveform-viewer/issues
- **讨论区**: https://github.com/X-Gen-Lab/xgen-waveform-viewer/discussions
- **邮箱**: support@xgen-lab.com

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](../LICENSE) 文件。
