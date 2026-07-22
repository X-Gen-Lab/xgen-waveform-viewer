# xgen-waveform-viewer 开发环境设置脚本
# 用法: .\setup-dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "xgen-waveform-viewer 开发环境设置" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Python
Write-Host "🐍 检查 Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 错误: 未找到 Python" -ForegroundColor Red
    Write-Host "请先安装 Python 3.10 或更高版本" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 找到 $pythonVersion" -ForegroundColor Green

# 检查版本
$versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
if ($versionMatch) {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
        Write-Host "⚠️  警告: Python 版本过低，建议 3.10+" -ForegroundColor Yellow
    }
}
Write-Host ""

# 2. 创建虚拟环境
Write-Host "📦 创建虚拟环境..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "⚠️  虚拟环境已存在" -ForegroundColor Yellow
    $recreate = Read-Host "是否重新创建? (y/N)"
    if ($recreate -eq "y") {
        Remove-Item -Recurse -Force ".venv"
        python -m venv .venv
        Write-Host "✅ 虚拟环境已重新创建" -ForegroundColor Green
    } else {
        Write-Host "⏭️  跳过虚拟环境创建" -ForegroundColor Gray
    }
} else {
    python -m venv .venv
    Write-Host "✅ 虚拟环境已创建" -ForegroundColor Green
}
Write-Host ""

# 3. 激活虚拟环境并安装依赖
Write-Host "📥 安装依赖..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# 升级 pip
python -m pip install --upgrade pip --quiet

# 安装项目依赖
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 依赖安装失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 依赖安装完成" -ForegroundColor Green
Write-Host ""

# 4. 安装开发工具（可选）
Write-Host "🛠️  安装开发工具..." -ForegroundColor Yellow
$devTools = @(
    "pyinstaller",  # 打包工具
    "black",        # 代码格式化
    "flake8",       # 代码检查
    "mypy"          # 类型检查
)

foreach ($tool in $devTools) {
    pip install $tool --quiet
}
Write-Host "✅ 开发工具已安装" -ForegroundColor Green
Write-Host ""

# 5. 验证安装
Write-Host "🔍 验证安装..." -ForegroundColor Yellow
python -c "import PyQt6; import pyqtgraph; import serial; import numpy; print('所有依赖导入成功')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 依赖验证失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 安装验证通过" -ForegroundColor Green
Write-Host ""

# 6. 运行语法检查
Write-Host "🔍 运行语法检查..." -ForegroundColor Yellow
python -m compileall src main.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 语法检查失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ 语法检查通过" -ForegroundColor Green
Write-Host ""

# 7. 总结
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ 开发环境设置完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "1. 激活虚拟环境 (如果还没有):" -ForegroundColor White
Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 运行程序:" -ForegroundColor White
Write-Host "   python main.py" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 构建可执行文件:" -ForegroundColor White
Write-Host "   pyinstaller xgen-waveform-viewer.spec" -ForegroundColor Gray
Write-Host ""
Write-Host "4. 查看开发文档:" -ForegroundColor White
Write-Host "   - CONTRIBUTING.md - 贡献指南" -ForegroundColor Gray
Write-Host "   - ROADMAP.md - 开发路线图" -ForegroundColor Gray
Write-Host ""

$runNow = Read-Host "是否立即运行程序? (y/N)"
if ($runNow -eq "y") {
    Write-Host "🚀 启动应用..." -ForegroundColor Yellow
    python main.py
}
