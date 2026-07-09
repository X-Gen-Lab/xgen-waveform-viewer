# xgen-waveform-viewer

xgen-waveform-viewer 是 X-GEN-LAB 归属的 PyQt6/pyqtgraph 桌面工具，用于通过 UART 串口实时查看 ADC 采样波形，并支持基础统计与数据录制。

仓库归属：[X-GEN-LAB](https://github.com/X-Gen-Lab)
仓库命名：[xgen-waveform-viewer](https://github.com/X-Gen-Lab/xgen-waveform-viewer)

当前上位机版本：`V2.0`，内部语义化版本号：`2.0.0`。

## 功能特性

- 实时串口读取 ADC 帧数据
- CRC-16-CCITT 帧校验
- 自动重同步与序列号间隙统计
- pyqtgraph 实时波形显示
- 支持命令行指定串口和波特率
- 支持保存采样数据

## 项目结构

```text
.
+-- src/
|   +-- xgen_waveform_viewer/
|       +-- __init__.py
|       +-- __main__.py
|       +-- config.py
|       +-- main.py
|       +-- main_window.py
|       +-- serial_reader.py
|       +-- waveform_widget.py
+-- xgen-waveform-viewer.spec
+-- pyproject.toml
+-- requirements.txt
+-- .gitignore
+-- README.md
+-- LICENSE
```

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

- 对外显示版本使用 `V主版本.次版本`，例如 `V2.0`
- 代码和包元数据使用完整语义化版本 `主版本.次版本.修订号`，例如 `2.0.0`
- 修复问题但不改变功能：`2.0.1`
- 新增兼容功能：`2.1.0`
- 不兼容升级：`3.0.0`

## License

本项目使用 MIT License，版权归属为 X-GEN-LAB。详见 [LICENSE](LICENSE)。
