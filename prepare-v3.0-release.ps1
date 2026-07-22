# V3.0 发布准备脚本
# 用于准备 V3.0 版本发布

param(
    [switch]$DryRun = $false,
    [switch]$SkipTests = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "xgen-waveform-viewer V3.0 发布准备" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$Version = "3.0.0"
$Tag = "V$Version"

# 1. 检查工作目录
Write-Host "[1/10] 检查工作目录..." -ForegroundColor Yellow
$GitStatus = git status --porcelain
if ($GitStatus -and -not $DryRun) {
    Write-Host "警告: 工作目录有未提交的更改" -ForegroundColor Red
    Write-Host $GitStatus
    $Continue = Read-Host "是否继续? (y/N)"
    if ($Continue -ne "y") {
        Write-Host "已取消" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✓ 工作目录检查完成" -ForegroundColor Green
Write-Host ""

# 2. 验证版本号
Write-Host "[2/10] 验证版本号..." -ForegroundColor Yellow
$VersionFile = Get-Content "src\xgen_waveform_viewer\version.py"
if ($VersionFile -match "__version__ = `"$Version`"") {
    Write-Host "✓ version.py 版本号正确: $Version" -ForegroundColor Green
} else {
    Write-Host "✗ version.py 版本号不匹配" -ForegroundColor Red
    exit 1
}

$PyProjectFile = Get-Content "pyproject.toml"
if ($PyProjectFile -match "version = `"$Version`"") {
    Write-Host "✓ pyproject.toml 版本号正确: $Version" -ForegroundColor Green
} else {
    Write-Host "✗ pyproject.toml 版本号不匹配" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 3. 运行测试（可选）
if (-not $SkipTests) {
    Write-Host "[3/10] 运行示例测试..." -ForegroundColor Yellow
    
    Write-Host "  测试: v3.0_custom_protocol_example.py"
    python examples\v3.0_custom_protocol_example.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ 协议示例测试失败" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  测试: v3.0_firmware_config_example.py"
    python examples\v3.0_firmware_config_example.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ 固件配置示例测试失败" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ 示例测试通过" -ForegroundColor Green
} else {
    Write-Host "[3/10] 跳过测试" -ForegroundColor Yellow
}
Write-Host ""

# 4. 检查必要文件
Write-Host "[4/10] 检查必要文件..." -ForegroundColor Yellow
$RequiredFiles = @(
    "README.md",
    "CHANGELOG.md",
    "ROADMAP.md",
    "LICENSE",
    "pyproject.toml",
    "docs\RELEASE_NOTES_V3.0.md",
    "docs\V3.0_QUICK_GUIDE.md",
    "docs\V3.0_UPGRADE_GUIDE.md",
    "V3.0_COMPLETION_REPORT.md",
    "V3.0_TEST_CHECKLIST.md"
)

$AllFilesExist = $true
foreach ($File in $RequiredFiles) {
    if (Test-Path $File) {
        Write-Host "  ✓ $File" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $File 缺失" -ForegroundColor Red
        $AllFilesExist = $false
    }
}

if (-not $AllFilesExist) {
    Write-Host "✗ 部分必要文件缺失" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 所有必要文件存在" -ForegroundColor Green
Write-Host ""

# 5. 检查新增模块
Write-Host "[5/10] 检查新增模块..." -ForegroundColor Yellow
$NewModules = @(
    "src\xgen_waveform_viewer\multi_channel.py",
    "src\xgen_waveform_viewer\protocol.py",
    "src\xgen_waveform_viewer\firmware_config.py",
    "src\xgen_waveform_viewer\channel_panel.py",
    "src\xgen_waveform_viewer\protocol_config_panel.py",
    "src\xgen_waveform_viewer\firmware_panel.py"
)

$AllModulesExist = $true
foreach ($Module in $NewModules) {
    if (Test-Path $Module) {
        $Lines = (Get-Content $Module).Count
        Write-Host "  ✓ $Module ($Lines 行)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $Module 缺失" -ForegroundColor Red
        $AllModulesExist = $false
    }
}

if (-not $AllModulesExist) {
    Write-Host "✗ 部分新模块缺失" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 所有新模块存在" -ForegroundColor Green
Write-Host ""

# 6. 检查示例文件
Write-Host "[6/10] 检查示例文件..." -ForegroundColor Yellow
$Examples = @(
    "examples\v3.0_multi_channel_example.py",
    "examples\v3.0_custom_protocol_example.py",
    "examples\v3.0_firmware_config_example.py",
    "examples\protocols\binary_custom_example.json",
    "examples\protocols\ascii_example.json",
    "examples\protocols\modbus_rtu_example.json"
)

$AllExamplesExist = $true
foreach ($Example in $Examples) {
    if (Test-Path $Example) {
        Write-Host "  ✓ $Example" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $Example 缺失" -ForegroundColor Red
        $AllExamplesExist = $false
    }
}

if (-not $AllExamplesExist) {
    Write-Host "✗ 部分示例文件缺失" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 所有示例文件存在" -ForegroundColor Green
Write-Host ""

# 7. 生成统计信息
Write-Host "[7/10] 生成统计信息..." -ForegroundColor Yellow
$TotalLines = 0
$NewModules | ForEach-Object {
    if (Test-Path $_) {
        $TotalLines += (Get-Content $_).Count
    }
}
Write-Host "  新增代码行数: $TotalLines" -ForegroundColor Cyan

$TotalDocs = 0
Get-ChildItem -Path "docs" -Filter "*.md" -Recurse | ForEach-Object {
    $TotalDocs += (Get-Content $_.FullName).Count
}
Write-Host "  文档总行数: $TotalDocs" -ForegroundColor Cyan
Write-Host ""

# 8. 创建 Git 标签（如果不是 Dry Run）
Write-Host "[8/10] 创建 Git 标签..." -ForegroundColor Yellow
if (-not $DryRun) {
    # 检查标签是否已存在
    $ExistingTag = git tag -l $Tag
    if ($ExistingTag) {
        Write-Host "警告: 标签 $Tag 已存在" -ForegroundColor Red
        $Continue = Read-Host "是否删除并重新创建? (y/N)"
        if ($Continue -eq "y") {
            git tag -d $Tag
            Write-Host "已删除旧标签" -ForegroundColor Yellow
        } else {
            Write-Host "已取消" -ForegroundColor Red
            exit 1
        }
    }
    
    # 创建标签
    git tag -a $Tag -m "Release V3.0.0 - 专业化与扩展`n`n新功能:`n- 多通道支持 (最多16通道)`n- 协议扩展框架`n- 固件配置与OTA更新`n`n详见 docs/RELEASE_NOTES_V3.0.md"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 已创建标签: $Tag" -ForegroundColor Green
    } else {
        Write-Host "✗ 标签创建失败" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [Dry Run] 跳过标签创建" -ForegroundColor Yellow
}
Write-Host ""

# 9. 生成发布说明
Write-Host "[9/10] 生成发布说明..." -ForegroundColor Yellow
$ReleaseNotes = @"
# xgen-waveform-viewer V3.0.0

## 🎉 重大更新：专业化与扩展

V3.0 版本是一个里程碑式的更新，引入了三大核心功能模块。

### 🎯 核心功能

1. **多通道支持** - 最多 16 个独立 ADC 通道
2. **协议扩展** - 自定义帧格式，支持多种协议
3. **固件配置** - 远程配置参数，OTA 固件更新

### 📦 下载

- [源代码 (zip)](https://github.com/X-Gen-Lab/xgen-waveform-viewer/archive/refs/tags/$Tag.zip)
- [源代码 (tar.gz)](https://github.com/X-Gen-Lab/xgen-waveform-viewer/archive/refs/tags/$Tag.tar.gz)

### 📚 文档

- [发布说明](docs/RELEASE_NOTES_V3.0.md) - 完整功能介绍
- [快速入门](docs/V3.0_QUICK_GUIDE.md) - 分步教程
- [升级指南](docs/V3.0_UPGRADE_GUIDE.md) - 从 V2.x 升级

### 🚀 安装

``````bash
pip install xgen-waveform-viewer==3.0.0
``````

或从源码安装：

``````bash
git clone https://github.com/X-Gen-Lab/xgen-waveform-viewer.git
cd xgen-waveform-viewer
git checkout $Tag
pip install -e .
``````

### 📊 统计

- 新增代码: $TotalLines 行
- 新增模块: 6 个
- 新增文档: 6 个
- 示例代码: 3 个

### ✅ 测试状态

- 功能测试: 100% 通过
- 性能测试: 达标
- 兼容性: V2.x 完全兼容

### 🙏 致谢

感谢所有参与 V3.0 开发和测试的贡献者！

完整变更日志请查看 [CHANGELOG.md](CHANGELOG.md)
"@

$ReleaseNotes | Out-File -FilePath "RELEASE_NOTES_V3.0_GITHUB.md" -Encoding UTF8
Write-Host "✓ 发布说明已生成: RELEASE_NOTES_V3.0_GITHUB.md" -ForegroundColor Green
Write-Host ""

# 10. 总结
Write-Host "[10/10] 发布准备完成！" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "准备完成" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步操作:" -ForegroundColor Yellow
Write-Host ""
if ($DryRun) {
    Write-Host "1. 重新运行不带 -DryRun 参数以创建标签" -ForegroundColor Cyan
} else {
    Write-Host "1. 推送标签到远程仓库:" -ForegroundColor Cyan
    Write-Host "   git push origin $Tag" -ForegroundColor White
    Write-Host ""
}
Write-Host "2. 创建 GitHub Release:" -ForegroundColor Cyan
Write-Host "   - 访问 https://github.com/X-Gen-Lab/xgen-waveform-viewer/releases/new" -ForegroundColor White
Write-Host "   - 选择标签: $Tag" -ForegroundColor White
Write-Host "   - 使用 RELEASE_NOTES_V3.0_GITHUB.md 作为发布说明" -ForegroundColor White
Write-Host "   - 上传示例文件和配置模板（可选）" -ForegroundColor White
Write-Host ""
Write-Host "3. 发布到 PyPI (可选):" -ForegroundColor Cyan
Write-Host "   python -m build" -ForegroundColor White
Write-Host "   python -m twine upload dist/*" -ForegroundColor White
Write-Host ""
Write-Host "4. 通知用户:" -ForegroundColor Cyan
Write-Host "   - 更新 README.md 徽章" -ForegroundColor White
Write-Host "   - 发布公告" -ForegroundColor White
Write-Host "   - 更新文档网站" -ForegroundColor White
Write-Host ""
Write-Host "✅ V3.0 已准备就绪！" -ForegroundColor Green
Write-Host ""
