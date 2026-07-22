# 贡献指南

感谢您对 xgen-waveform-viewer 的关注！我们欢迎各种形式的贡献。

## 目录
- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境设置](#开发环境设置)
- [代码规范](#代码规范)
- [提交 Pull Request](#提交-pull-request)
- [报告问题](#报告问题)

## 行为准则

参与本项目即表示您同意遵守我们的行为准则：
- 尊重所有参与者
- 接受建设性批评
- 专注于对社区最有利的事情
- 展现同理心和善意

## 如何贡献

您可以通过以下方式贡献：

### 🐛 报告 Bug
在 [Issues](https://github.com/X-Gen-Lab/xgen-waveform-viewer/issues) 中创建详细的 Bug 报告

### 💡 功能建议
提出新功能想法或改进建议

### 📖 改进文档
修正文档错误、添加示例或翻译

### 💻 贡献代码
修复 Bug 或实现新功能

### 🧪 测试
在不同平台测试并报告结果

## 开发环境设置

### 1. Fork 和 Clone
```bash
# Fork 仓库到您的账号
# 然后 clone 您的 fork
git clone https://github.com/YOUR_USERNAME/xgen-waveform-viewer.git
cd xgen-waveform-viewer
```

### 2. 创建虚拟环境
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate    # Linux/macOS
```

### 3. 安装依赖
```powershell
pip install -r requirements.txt
```

### 4. 创建分支
```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/bug-description
```

### 5. 运行程序
```powershell
python main.py
```

## 代码规范

### Python 风格
- 遵循 [PEP 8](https://pep8.org/) 代码风格
- 使用 4 个空格缩进（不使用 Tab）
- 最大行长度：100 字符
- 使用类型注解（Type Hints）

### 示例
```python
def calculate_sample_rate(frame_count: int, elapsed_time: float) -> float:
    """
    计算采样率
    
    Args:
        frame_count: 帧数
        elapsed_time: 经过的时间（秒）
    
    Returns:
        采样率（Hz）
    """
    if elapsed_time <= 0:
        return 0.0
    return frame_count / elapsed_time
```

### 命名规范
- **类名**：PascalCase（例如：`SerialReader`）
- **函数/方法**：snake_case（例如：`read_frame`）
- **常量**：UPPER_SNAKE_CASE（例如：`MAX_BUFFER_SIZE`）
- **私有成员**：以 `_` 开头（例如：`_internal_buffer`）

### 文档字符串
- 使用 Google 风格的 docstring
- 为所有公共函数/类添加文档
- 包含参数说明和返回值

## 提交 Pull Request

### 1. 提交代码
```bash
git add .
git commit -m "feat: add new feature description"
# 或
git commit -m "fix: resolve issue #123"
```

### 提交消息格式
使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `style:` 代码格式调整（不影响功能）
- `refactor:` 代码重构
- `perf:` 性能优化
- `test:` 添加测试
- `chore:` 构建/工具链更新

### 2. 推送到您的 Fork
```bash
git push origin feature/your-feature-name
```

### 3. 创建 Pull Request
1. 访问您的 GitHub Fork 页面
2. 点击 "Compare & pull request"
3. 填写 PR 模板：
   - **标题**：简洁描述变更
   - **描述**：详细说明变更内容和原因
   - **关联 Issue**：如果适用，使用 `Closes #123`
   - **测试**：说明如何测试您的变更

### 4. 代码审查
- 响应审查意见
- 根据反馈进行修改
- 保持 PR 更新

## 报告问题

### Bug 报告模板
```markdown
**描述 Bug**
简要描述 Bug 是什么

**复现步骤**
1. 步骤 1
2. 步骤 2
3. ...

**期望行为**
应该发生什么

**实际行为**
实际发生了什么

**截图**
如果适用，添加截图

**环境信息**
- OS: [例如 Windows 11]
- Python 版本: [例如 3.11]
- 应用版本: [例如 V2.1]

**附加信息**
其他相关信息
```

### 功能请求模板
```markdown
**功能描述**
简要描述您希望的功能

**使用场景**
为什么需要这个功能？

**替代方案**
您考虑过哪些替代方案？

**附加信息**
其他相关信息或截图
```

## 开发提示

### 测试您的更改
```powershell
# 语法检查
python -m py_compile src/xgen_waveform_viewer/*.py

# 运行程序
python main.py

# 测试打包
pyinstaller xgen-waveform-viewer.spec
```

### 调试技巧
- 使用 PyCharm 或 VS Code 的 Python 调试器
- 在关键点添加 `print()` 或日志
- 检查状态栏的统计信息

### 常见陷阱
- **不要**直接修改主线程中的 UI（使用信号/槽）
- **记得**处理异常并给用户友好的错误消息
- **注意**跨平台兼容性（路径、换行符等）

## 项目结构

```
xgen-waveform-viewer/
├── src/xgen_waveform_viewer/
│   ├── __init__.py         # 包初始化
│   ├── main.py             # 程序入口
│   ├── main_window.py      # 主窗口
│   ├── waveform_widget.py  # 波形显示组件
│   ├── serial_reader.py    # 串口读取线程
│   ├── recorder.py         # 录制线程
│   ├── config.py           # 配置常量
│   ├── settings.py         # 设置管理
│   ├── theme.py            # 主题管理
│   └── version.py          # 版本信息
├── .github/workflows/      # CI/CD 配置
├── main.py                 # 命令行入口
├── requirements.txt        # Python 依赖
├── pyproject.toml          # 项目元数据
├── README.md               # 项目说明
├── CHANGELOG.md            # 变更日志
├── ROADMAP.md              # 开发路线图
└── CONTRIBUTING.md         # 本文件
```

## 获取帮助

- 💬 在 [Discussions](https://github.com/X-Gen-Lab/xgen-waveform-viewer/discussions) 提问
- 📧 联系维护者（通过 Issue 或邮件）
- 📖 阅读现有代码和文档

## 许可证

通过贡献代码，您同意您的贡献将按照 MIT 许可证授权。

---

再次感谢您的贡献！ 🙏
