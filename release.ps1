# xgen-waveform-viewer 发布脚本
# 用法: .\release.ps1 -Version "2.1.0"

param(
    [Parameter(Mandatory=$true)]
    [string]$Version,
    
    [switch]$SkipTests = $false,
    [switch]$SkipBuild = $false
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "xgen-waveform-viewer Release Script" -ForegroundColor Cyan
Write-Host "Target Version: V$Version" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 验证版本号格式
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    Write-Host "❌ 错误: 版本号格式不正确，应为 X.Y.Z (例如 2.1.0)" -ForegroundColor Red
    exit 1
}

# 2. 检查工作区是否干净
Write-Host "📋 检查 Git 工作区..." -ForegroundColor Yellow
$gitStatus = git status --porcelain
if ($gitStatus -and !$SkipTests) {
    Write-Host "⚠️  警告: 工作区有未提交的变更" -ForegroundColor Yellow
    $continue = Read-Host "是否继续? (y/N)"
    if ($continue -ne "y") {
        exit 1
    }
}

# 3. 运行语法检查
if (!$SkipTests) {
    Write-Host "🔍 运行语法检查..." -ForegroundColor Yellow
    python -m compileall src main.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 语法检查失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ 语法检查通过" -ForegroundColor Green
    Write-Host ""
}

# 4. 更新版本号
Write-Host "📝 更新版本号到 $Version..." -ForegroundColor Yellow

$versionParts = $Version -split '\.'
$displayVersion = "V$($versionParts[0]).$($versionParts[1])"

# 更新 version.py
$versionFile = "src\xgen_waveform_viewer\version.py"
$versionContent = @"
"""Application version information."""

__version__ = "$Version"
APP_DISPLAY_VERSION = "$displayVersion"
APP_NAME = "xgen-waveform-viewer"
APP_TITLE = f"{APP_NAME} {APP_DISPLAY_VERSION}"
"@
Set-Content -Path $versionFile -Value $versionContent -Encoding UTF8

# 更新 pyproject.toml
$pyprojectFile = "pyproject.toml"
$pyprojectContent = Get-Content $pyprojectFile -Raw
$pyprojectContent = $pyprojectContent -replace 'version = "[\d\.]+"', "version = `"$Version`""
Set-Content -Path $pyprojectFile -Value $pyprojectContent -Encoding UTF8 -NoNewline

Write-Host "✅ 版本号已更新" -ForegroundColor Green
Write-Host ""

# 5. 构建可执行文件
if (!$SkipBuild) {
    Write-Host "🔨 构建可执行文件..." -ForegroundColor Yellow
    
    # 清理旧的构建
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
    if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
    
    # 运行 PyInstaller
    pyinstaller xgen-waveform-viewer.spec --clean --noconfirm
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 构建失败" -ForegroundColor Red
        exit 1
    }
    
    if (!(Test-Path "dist\xgen-waveform-viewer.exe")) {
        Write-Host "❌ 可执行文件未生成" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ 构建成功" -ForegroundColor Green
    Write-Host ""
}

# 6. 提交变更
Write-Host "💾 提交版本变更..." -ForegroundColor Yellow
git add src/xgen_waveform_viewer/version.py pyproject.toml
git commit -m "chore: bump version to $Version"

Write-Host "✅ 变更已提交" -ForegroundColor Green
Write-Host ""

# 7. 创建标签
Write-Host "🏷️  创建 Git 标签 $displayVersion..." -ForegroundColor Yellow
git tag -a "$displayVersion" -m "Release $displayVersion"

Write-Host "✅ 标签已创建" -ForegroundColor Green
Write-Host ""

# 8. 总结
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ 发布准备完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步操作:" -ForegroundColor Yellow
Write-Host "1. 推送代码和标签:" -ForegroundColor White
Write-Host "   git push origin main" -ForegroundColor Gray
Write-Host "   git push origin $displayVersion" -ForegroundColor Gray
Write-Host ""
Write-Host "2. GitHub Actions 将自动构建并创建 Release" -ForegroundColor White
Write-Host ""
Write-Host "3. 或者手动上传 dist\xgen-waveform-viewer.exe 到 GitHub Release" -ForegroundColor White
Write-Host ""

$push = Read-Host "是否立即推送到远程? (y/N)"
if ($push -eq "y") {
    Write-Host "🚀 推送到远程..." -ForegroundColor Yellow
    git push origin main
    git push origin "$displayVersion"
    Write-Host "✅ 推送完成!" -ForegroundColor Green
}
