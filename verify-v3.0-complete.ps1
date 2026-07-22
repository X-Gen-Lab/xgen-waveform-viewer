# V3.0 完整性验证脚本
# 验证所有V3.0组件是否完整

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "V3.0 完整性验证" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$AllPassed = $true

# 核心模块检查
Write-Host "[1/8] 检查核心模块..." -ForegroundColor Yellow
$CoreModules = @(
    "src\xgen_waveform_viewer\multi_channel.py",
    "src\xgen_waveform_viewer\protocol.py",
    "src\xgen_waveform_viewer\firmware_config.py"
)

foreach ($Module in $CoreModules) {
    if (Test-Path $Module) {
        $Lines = (Get-Content $Module).Count
        Write-Host "  ✓ $Module ($Lines 行)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $Module 缺失" -ForegroundColor Red
        $AllPassed = $false
    }
}
Write-Host ""

# UI面板检查
Write-Host "[2/8] 检查UI面板..." -ForegroundColor Yellow
$UIPanels = @(
    "src\xgen_waveform_viewer\channel_panel.py",
    "src\xgen_waveform_viewer\protocol_config_panel.py",
    "src\xgen_waveform_viewer\firmware_panel.py"
)

foreach ($Panel in $UIPanels) {
    if (Test-Path $Panel) {
        $Lines = (Get-Content $Panel).Count
        Write-Host "  ✓ $Panel ($Lines 行)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $Panel 缺失" -ForegroundColor Red
        $AllPassed = $false
    }
}
Write-Host ""

# UI集成检查
Write-Host "[3/8] 检查UI集成..." -ForegroundColor Yellow
$MainWindow = Get-Content "src\xgen_waveform_viewer\main_window.py" -Raw

$IntegrationChecks = @{
    "导入多通道" = "from \.multi_channel import"
    "导入协议" = "from \.protocol import"
    "导入固件" = "from \.firmware_config import"
    "通道面板导入" = "from \.channel_panel import"
    "协议面板导入" = "from \.protocol_config_panel import"
    "固件面板导入" = "from \.firmware_panel import"
    "通道管理器初始化" = "self\._channel_manager = MultiChannelManager"
    "协议解析器初始化" = "self\._protocol_parser = BinaryV2Parser"
    "通道面板方法" = "def _show_channel_panel"
    "协议面板方法" = "def _show_protocol_panel"
    "固件面板方法" = "def _show_firmware_panel"
    "通道菜单项" = "Channel Management"
    "协议菜单项" = "Protocol Configuration"
    "固件菜单项" = "Firmware Configuration"
}

foreach ($Check in $IntegrationChecks.GetEnumerator()) {
    if ($MainWindow -match $Check.Value) {
        Write-Host "  ✓ $($Check.Key)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $($Check.Key) 缺失" -ForegroundColor Red
        $AllPassed = $false
    }
}
Write-Host ""

# 文档检查
Write-Host "[4/8] 检查文档..." -ForegroundColor Yellow
$Documents = @(
    "docs\RELEASE_NOTES_V3.0.md",
    "docs\V3.0_QUICK_GUIDE.md",
    "docs\V3.0_UPGRADE_GUIDE.md",
    "V3.0_COMPLETION_REPORT.md",
    "V3.0_TEST_CHECKLIST.md",
    "V3.0_DELIVERY_SUMMARY.md"
)

foreach ($Doc in $Documents) {
    if (Test-Path $Doc) {
        $Lines = (Get-Content $Doc).Count
        Write-Host "  ✓ $Doc ($Lines 行)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $Doc 缺失" -ForegroundColor Red
        $AllPassed = $false
    }
}
Write-Host ""

# 示例代码检查
Write-Host "[5/8] 检查示例代码..." -ForegroundColor Yellow
$Examples = @(
    "examples\v3.0_multi_channel_example.py",
    "examples\v3.0_custom_protocol_example.py",
    "examples\v3.0_firmware_config_example.py"
)

foreach ($Example in $Examples) {
    if (Test-Path $Example) {
        $Lines = (Get-Content $Example).Count
        Write-Host "  ✓ $Example ($Lines 行)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $Example 缺失" -ForegroundColor Red
        $AllPassed = $false
    }
}
Write-Host ""

# 配置模板检查
Write-Host "[6/8] 检查配置模板..." -ForegroundColor Yellow
$Templates = @(
    "examples\protocols\binary_custom_example.json",
    "examples\protocols\ascii_example.json",
    "examples\protocols\modbus_rtu_example.json"
)

foreach ($Template in $Templates) {
    if (Test-Path $Template) {
        Write-Host "  ✓ $Template" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $Template 缺失" -ForegroundColor Red
        $AllPassed = $false
    }
}
Write-Host ""

# 版本号检查
Write-Host "[7/8] 检查版本号..." -ForegroundColor Yellow
$VersionFile = Get-Content "src\xgen_waveform_viewer\version.py"
if ($VersionFile -match '__version__ = "3\.0\.0"') {
    Write-Host "  ✓ version.py: 3.0.0" -ForegroundColor Green
} else {
    Write-Host "  ✗ version.py 版本号不正确" -ForegroundColor Red
    $AllPassed = $false
}

$PyProjectFile = Get-Content "pyproject.toml"
if ($PyProjectFile -match 'version = "3\.0\.0"') {
    Write-Host "  ✓ pyproject.toml: 3.0.0" -ForegroundColor Green
} else {
    Write-Host "  ✗ pyproject.toml 版本号不正确" -ForegroundColor Red
    $AllPassed = $false
}

$Readme = Get-Content "README.md" -Raw
if ($Readme -match 'V3\.0\.0') {
    Write-Host "  ✓ README.md: V3.0.0" -ForegroundColor Green
} else {
    Write-Host "  ✗ README.md 版本未更新" -ForegroundColor Red
    $AllPassed = $false
}
Write-Host ""

# 统计信息
Write-Host "[8/8] 生成统计信息..." -ForegroundColor Yellow

$TotalNewCode = 0
$CoreModules + $UIPanels | ForEach-Object {
    if (Test-Path $_) {
        $TotalNewCode += (Get-Content $_).Count
    }
}

$TotalDocs = 0
$Documents | ForEach-Object {
    if (Test-Path $_) {
        $TotalDocs += (Get-Content $_).Count
    }
}

$TotalExamples = 0
$Examples | ForEach-Object {
    if (Test-Path $_) {
        $TotalExamples += (Get-Content $_).Count
    }
}

Write-Host ""
Write-Host "统计信息:" -ForegroundColor Cyan
Write-Host "  核心模块: 6 个文件, $TotalNewCode 行代码" -ForegroundColor White
Write-Host "  文档: $($Documents.Count) 个文件, $TotalDocs 行" -ForegroundColor White
Write-Host "  示例: $($Examples.Count) 个文件, $TotalExamples 行" -ForegroundColor White
Write-Host "  配置模板: $($Templates.Count) 个文件" -ForegroundColor White
Write-Host ""

# 最终结果
Write-Host "========================================" -ForegroundColor Cyan
if ($AllPassed) {
    Write-Host "✅ V3.0 完整性验证通过！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "所有组件已就位，可以发布！" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步:" -ForegroundColor Yellow
    Write-Host "1. 运行 prepare-v3.0-release.ps1 准备发布" -ForegroundColor White
    Write-Host "2. 推送到 GitHub" -ForegroundColor White
    Write-Host "3. 创建 Release" -ForegroundColor White
    Write-Host ""
    exit 0
} else {
    Write-Host "❌ V3.0 完整性验证失败！" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "请检查上述错误并修复。" -ForegroundColor Red
    Write-Host ""
    exit 1
}
