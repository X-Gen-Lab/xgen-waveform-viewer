# xgen-waveform-viewer

xgen-waveform-viewer 是 X-GEN-LAB 归属的 PyQt6/pyqtgraph 桌面工具，用于通过 UART 串口实时查看 ADC 采样波形，并支持基础统计与数据录制。

仓库归属：[X-GEN-LAB](https://github.com/X-Gen-Lab)
仓库命名：[xgen-waveform-viewer](https://github.com/X-Gen-Lab/xgen-waveform-viewer)

当前上位机版本：`V2.2`，内部语义化版本号：`2.2.0`。

## 功能特性

### 核心功能
- ✅ 实时串口读取 ADC 帧数据
- ✅ CRC-16-CCITT 帧校验
- ✅ 自动重同步与序列号间隙统计
- ✅ pyqtgraph 实时波形显示
- ✅ 支持命令行指定串口和波特率
- ✅ 支持保存和导出采样数据（BIN v2 / CSV）

### V2.1 用户体验增强
- ✨ **配置持久化** - 自动保存和恢复用户设置
- ✨ **键盘快捷键** - 快速访问常用操作
- ✨ **主题切换** - 支持暗色/亮色主题
- ✨ **自动重连** - 串口断开后自动重新连接
- ✨ **菜单栏** - 更好的功能组织和访问

### 🆕 V2.2 数据分析工具
- 📏 **测量工具**
  - 可拖动标尺：测量时间间隔和幅值差
  - 峰值检测：自动识别并标注正负峰值
  - 频率计算：基于峰值间隔自动计算频率
  - 统计分析：RMS、平均值、最大最小值、峰峰值
- ⚡ **触发功能**
  - 多种触发模式：自动、正常、单次触发
  - 多种触发类型：上升沿、下降沿、双边沿、电平触发
  - 可配置阈值和滞回，有效抑制噪声
  - 触发事件可视化和状态指示
- 🎬 **录制增强**
  - 暂停/恢复：录制过程中可随时暂停
  - 自动分段：按时间或文件大小自动分段
  - 实时预览：显示录制时长、文件大小、帧数

## 项目结构

```text
.
+-- src/
|   +-- xgen_waveform_viewer/
|       +-- __init__.py            # 包初始化
|       +-- __main__.py            # 命令行入口
|       +-- config.py              # 配置常量
|       +-- main.py                # 程序入口
|       +-- main_window.py         # 主窗口（UI + 业务逻辑）
|       +-- serial_reader.py       # 串口读取线程
|       +-- recorder.py            # 数据录制线程（V2.2 增强：暂停/恢复、自动分段）
|       +-- waveform_widget.py     # 波形显示组件
|       +-- measurement_tools.py   # 测量工具（V2.2：标尺、峰值检测、统计）
|       +-- trigger.py             # 触发系统（V2.2：多种触发模式和类型）
|       +-- settings.py            # 配置持久化
|       +-- theme.py               # 主题管理
|       +-- version.py             # 版本信息
+-- docs/
|   +-- RELEASE_NOTES_V2.1.md      # V2.1 发布说明
|   +-- RELEASE_NOTES_V2.2.md      # V2.2 发布说明
+-- examples/
|   +-- v2.2_measurement_example.py # V2.2 测量工具示例
+-- .github/
|   +-- workflows/
|       +-- release.yml            # 自动发布工作流
|   +-- ISSUE_TEMPLATE/            # Issue 模板
|   +-- PULL_REQUEST_TEMPLATE.md   # PR 模板
+-- main.py                        # 开发环境入口（添加 src 到 path）
+-- xgen-waveform-viewer.spec      # PyInstaller 打包配置
+-- pyproject.toml                 # 项目元数据（语义化版本 2.2.0）
+-- requirements.txt               # Python 依赖
+-- README.md                      # 项目说明
+-- CHANGELOG.md                   # 版本更新日志
+-- ROADMAP.md                     # 开发路线图
+-- QUICKSTART.md                  # 快速入门指南
+-- CONTRIBUTING.md                # 贡献指南
+-- LICENSE                        # MIT 许可证
+-- .gitignore
+-- release.ps1                    # 发布脚本
+-- setup-dev.ps1                  # 开发环境设置脚本
```

## 文档

- 📖 [快速入门指南](QUICKSTART.md) - 5 分钟上手
- 🗺️ [开发路线图](ROADMAP.md) - 未来计划
- 📝 [更新日志](CHANGELOG.md) - 版本变更
- 🤝 [贡献指南](CONTRIBUTING.md) - 参与开发

## 环境要求

- Python 3.10 或更高版本
- Windows、Linux 或 macOS
- 可用的串口设备

## 安装与运行

创建虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
pip install -r requirements.txt
```

从源码直接运行：

```powershell
python main.py
```

指定串口和波特率：

```powershell
python main.py --port COM3 --baud 460800
```

查看版本：

```powershell
python main.py --version
```

如果使用可编辑安装，也可以运行命令行入口：

```powershell
pip install -e .
xgen-waveform-viewer --port COM3 --baud 460800
```

## 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Space` | 恢复 X 轴自动滚动 (Follow) |
| `C` | 连接/断开串口 |
| `R` | 开始/停止录制 |
| `F` | 显示缓冲区全部数据 |
| `Y` | 切换 Y 轴自动/手动模式 |
| `+` / `-` | X 轴放大/缩小 |
| `Ctrl+S` | 保存缓冲区到文件 |
| `Ctrl+E` | 导出缓冲区为 CSV |
| `Ctrl+Q` | 退出应用 |

鼠标操作：
- 左键拖拽：平移视图
- 滚轮：缩放
- 双击：恢复自动滚动

## 配置说明

应用会自动保存以下设置：
- 串口配置（最后使用的端口、波特率等）
- 显示设置（X/Y 轴范围、缓冲区大小、主题）
- 录制设置（格式、保存目录）
- 窗口大小和位置

配置文件位置：
- Windows: `%APPDATA%\X-GEN-LAB\xgen-waveform-viewer.ini`
- Linux: `~/.config/X-GEN-LAB/xgen-waveform-viewer.conf`
- macOS: `~/Library/Preferences/com.X-GEN-LAB.xgen-waveform-viewer.plist`

## 数据帧格式

当前解析器按以下 UART 帧格式读取数据：

```text
[SYNC0=0xA5][SYNC1=0x5A]  2 bytes
[SEQ]                      uint32 little-endian
[SAMPLES_CNT]              uint16 little-endian
[SAMPLES]                  SAMPLES_CNT * uint16 little-endian
[CRC16]                    CRC-16-CCITT, covers SEQ + SAMPLES_CNT + SAMPLES
```

默认参数在 `src/xgen_waveform_viewer/config.py` 中配置。

## 打包

项目保留了 PyInstaller spec 文件。安装 PyInstaller 后可执行：

```powershell
pip install pyinstaller
pyinstaller xgen-waveform-viewer.spec
```

生成文件会输出到 `dist/`，该目录不会提交到 Git。

## GitHub Actions 发布

仓库包含 `.github/workflows/release.yml`。推送形如 `V2.0` 或 `v2.0.0` 的 Git 标签后，GitHub Actions 会自动：

- 在 Windows runner 上安装 Python 依赖
- 运行 `python -m compileall src main.py`
- 使用 PyInstaller 构建 `xgen-waveform-viewer.exe`
- 打包 zip 文件并生成 SHA256 校验文件
- 创建或更新对应 GitHub Release

发布新版本：

```powershell
git add .
git commit -m "chore: prepare release workflow"
git tag V2.0
git push origin main
git push origin V2.0
```

也可以在 GitHub 页面进入 `Actions` -> `Release` -> `Run workflow` 手动输入版本号触发。

版本号约定：

- 对外显示版本使用 `V主版本.次版本`，例如 `V2.1`
- 代码和包元数据使用完整语义化版本 `主版本.次版本.修订号`，例如 `2.1.0`
- 修复问题但不改变功能：`2.1.1`
- 新增兼容功能：`2.2.0`
- 不兼容升级：`3.0.0`

## 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)。

## License

本项目使用 MIT License，版权归属为 X-GEN-LAB。详见 [LICENSE](LICENSE)。
