# xgen-waveform-viewer V2.1 发布说明

🎉 我们很高兴发布 **xgen-waveform-viewer V2.1**！本版本专注于用户体验提升和稳定性改进。

## 📦 下载

- [Windows x64 可执行文件](https://github.com/X-Gen-Lab/xgen-waveform-viewer/releases/tag/V2.1)
- [源代码 (zip)](https://github.com/X-Gen-Lab/xgen-waveform-viewer/archive/refs/tags/V2.1.zip)
- [源代码 (tar.gz)](https://github.com/X-Gen-Lab/xgen-waveform-viewer/archive/refs/tags/V2.1.tar.gz)

## ✨ 新增功能

### 1. 配置持久化 🎯
应用现在会自动记住您的偏好设置！

**自动保存的设置包括：**
- 串口配置（端口、波特率、校验位等）
- 显示设置（X/Y 轴范围、缓冲区大小）
- 录制设置（格式、保存目录）
- 窗口大小和位置
- 主题偏好

**无需每次重新配置** - 下次启动时，所有设置都会自动恢复！

### 2. 键盘快捷键 ⌨️
通过快捷键快速访问常用功能：

| 快捷键 | 功能 |
|--------|------|
| `Space` | 恢复自动滚动 |
| `C` | 连接/断开串口 |
| `R` | 开始/停止录制 |
| `F` | 显示全部缓冲区 |
| `Y` | 切换 Y 轴模式 |
| `+` / `-` | X 轴缩放 |
| `Ctrl+S` | 保存缓冲区 |
| `Ctrl+E` | 导出 CSV |
| `Ctrl+Q` | 退出程序 |

提示：在应用中按 `Help > Keyboard Shortcuts` 查看完整列表。

### 3. 主题切换 🎨
支持暗色和亮色两种主题：

- **暗色主题**（默认）- 适合长时间观察，减少眼睛疲劳
- **亮色主题** - 适合明亮环境，打印友好

切换方式：`View > Theme > Dark / Light`

主题偏好会自动保存，下次启动自动应用。

### 4. 自动重连 🔄
串口意外断开？不用担心！

启用自动重连后（`Connection > Auto Reconnect`），应用会在串口断开后自动尝试重新连接：
- 默认延迟 3 秒
- 保留上次连接配置
- 连接成功后自动恢复显示

非常适合：
- 不稳定的 USB 连接
- 设备重启场景
- 长时间运行监控

### 5. 菜单栏 📋
新增完整的菜单系统，功能组织更清晰：

- **File** - 保存、导出、退出
- **View** - 主题、视图控制
- **Connection** - 连接管理、自动重连
- **Help** - 快捷键帮助、关于

### 6. 增强的 UI
- 优化的按钮布局和间距
- 改进的状态栏信息显示
- 更好的视觉反馈（连接状态、录制状态）
- 新的关于对话框（显示版本信息）

## 🔧 改进

- 窗口状态（大小、位置）现在会正确保存和恢复
- 主题颜色动态应用到波形显示
- 改进的设置同步机制
- 更好的错误处理和用户提示

## 📚 新增文档

本版本添加了完整的项目文档：

- 📖 [QUICKSTART.md](QUICKSTART.md) - 5 分钟快速入门指南
- 🗺️ [ROADMAP.md](ROADMAP.md) - 开发路线图
- 📝 [CHANGELOG.md](CHANGELOG.md) - 详细变更日志
- 🤝 [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南
- 🏷️ Issue 和 PR 模板

## 🚀 快速开始

### 首次用户
1. 下载并运行 `xgen-waveform-viewer.exe`
2. 选择串口并点击 "Connect"（或按 `C`）
3. 开始查看实时波形！

详细教程：[QUICKSTART.md](QUICKSTART.md)

### 从 V2.0 升级
- 直接替换可执行文件即可
- V2.0 的录制文件完全兼容
- 首次启动会使用默认配置，可在界面调整

## 🐛 已知问题

目前没有已知的重大问题。如发现问题，请[提交 Issue](https://github.com/X-Gen-Lab/xgen-waveform-viewer/issues)。

## 🔮 下一步计划

V2.2 版本将专注于数据分析功能：
- 测量工具（标尺、峰值检测）
- 触发功能（边沿触发、阈值触发）
- 录制增强（分段录制、暂停/恢复）

查看完整路线图：[ROADMAP.md](ROADMAP.md)

## 🙏 致谢

感谢所有测试和提供反馈的用户！

## 📞 反馈

- 🐛 报告 Bug：[GitHub Issues](https://github.com/X-Gen-Lab/xgen-waveform-viewer/issues)
- 💡 功能建议：[GitHub Issues](https://github.com/X-Gen-Lab/xgen-waveform-viewer/issues)
- 💬 讨论交流：[GitHub Discussions](https://github.com/X-Gen-Lab/xgen-waveform-viewer/discussions)

---

**完整变更日志**：[CHANGELOG.md](CHANGELOG.md)

祝使用愉快！ 🎊

---
*xgen-waveform-viewer V2.1 | 发布日期: 2024-12-20 | MIT License*
