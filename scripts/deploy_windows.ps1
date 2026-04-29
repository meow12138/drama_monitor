# ============================================================
#  海外短剧爆款监控 - Windows Server 一键部署脚本
#  适用于：Windows Server 2022 (阿里云 ECS)
#
#  使用方法：
#    1. 远程桌面登录 ECS
#    2. 以管理员身份打开 PowerShell
#    3. 执行：Set-ExecutionPolicy RemoteSigned -Force
#    4. 执行：.\deploy_windows.ps1
#
#  前置要求：
#    - 已安装 Python 3.10+（勾选 Add to PATH）
#    - 已安装 Git for Windows
#    - 阿里云安全组已放行 TCP 8000 端口
# ============================================================

$ErrorActionPreference = "Stop"

$PROJECT_NAME = "drama_monitor"
$REPO_URL = "https://github.com/meow12138/drama_monitor.git"
$BRANCH = "feat/zhangwan-ui-rewrite"
$INSTALL_DIR = "C:\$PROJECT_NAME"
$NSSM_DIR = "C:\nssm"
$NSSM_URL = "https://nssm.cc/release/nssm-2.24.zip"
$SERVICE_NAME = "DramaMonitor"
$PORT = 8000

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  海外短剧爆款监控 - 部署脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ------ Step 1: 检查前置依赖 ------
Write-Host "[1/7] 检查前置依赖..." -ForegroundColor Yellow

try { $pyVer = python --version 2>&1; Write-Host "  Python: $pyVer" -ForegroundColor Green }
catch { Write-Host "  ERROR: 未检测到 Python，请先安装 Python 3.10+ 并勾选 Add to PATH" -ForegroundColor Red; exit 1 }

try { $gitVer = git --version 2>&1; Write-Host "  Git: $gitVer" -ForegroundColor Green }
catch { Write-Host "  ERROR: 未检测到 Git，请先安装 Git for Windows" -ForegroundColor Red; exit 1 }

# ------ Step 2: 拉取代码 ------
Write-Host "[2/7] 拉取代码..." -ForegroundColor Yellow

if (Test-Path $INSTALL_DIR) {
    Write-Host "  目录已存在，拉取最新代码..."
    Set-Location $INSTALL_DIR
    git fetch origin
    git checkout $BRANCH
    git pull origin $BRANCH
} else {
    Set-Location C:\
    git clone $REPO_URL
    Set-Location $INSTALL_DIR
    git checkout $BRANCH
}
Write-Host "  代码就绪: $INSTALL_DIR" -ForegroundColor Green

# ------ Step 3: 创建虚拟环境 ------
Write-Host "[3/7] 创建虚拟环境并安装依赖..." -ForegroundColor Yellow

if (-not (Test-Path "$INSTALL_DIR\venv")) {
    python -m venv venv
    Write-Host "  虚拟环境已创建"
} else {
    Write-Host "  虚拟环境已存在，跳过创建"
}

& "$INSTALL_DIR\venv\Scripts\pip.exe" install -r requirements.txt -q
Write-Host "  依赖安装完成" -ForegroundColor Green

# ------ Step 4: 创建日志目录 ------
Write-Host "[4/7] 创建日志目录..." -ForegroundColor Yellow

$logsDir = "$INSTALL_DIR\logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
Write-Host "  日志目录: $logsDir" -ForegroundColor Green

# ------ Step 5: 下载 NSSM ------
Write-Host "[5/7] 配置 NSSM 服务管理器..." -ForegroundColor Yellow

if (-not (Test-Path "$NSSM_DIR\nssm.exe")) {
    Write-Host "  下载 NSSM..."
    $zipPath = "$env:TEMP\nssm.zip"
    Invoke-WebRequest -Uri $NSSM_URL -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath "$env:TEMP\nssm_extract" -Force
    if (-not (Test-Path $NSSM_DIR)) { New-Item -ItemType Directory -Path $NSSM_DIR | Out-Null }
    Copy-Item "$env:TEMP\nssm_extract\nssm-2.24\win64\nssm.exe" "$NSSM_DIR\nssm.exe" -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
    Remove-Item "$env:TEMP\nssm_extract" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  NSSM 已安装到 $NSSM_DIR" -ForegroundColor Green
} else {
    Write-Host "  NSSM 已存在，跳过下载" -ForegroundColor Green
}

# ------ Step 6: 注册 Windows 服务 ------
Write-Host "[6/7] 注册 Windows 服务..." -ForegroundColor Yellow

$nssmExe = "$NSSM_DIR\nssm.exe"
$status = & $nssmExe status $SERVICE_NAME 2>&1

if ($status -match "SERVICE_RUNNING") {
    Write-Host "  服务正在运行，先停止..."
    & $nssmExe stop $SERVICE_NAME
    Start-Sleep -Seconds 2
}

if ($status -notmatch "SERVICE_") {
    & $nssmExe install $SERVICE_NAME "$INSTALL_DIR\venv\Scripts\uvicorn.exe"
    Write-Host "  服务已注册"
} else {
    Write-Host "  服务已存在，更新配置"
}

& $nssmExe set $SERVICE_NAME AppParameters "app.main:app --host 0.0.0.0 --port $PORT"
& $nssmExe set $SERVICE_NAME AppDirectory $INSTALL_DIR
& $nssmExe set $SERVICE_NAME AppStdout "$logsDir\service.log"
& $nssmExe set $SERVICE_NAME AppStderr "$logsDir\error.log"
& $nssmExe set $SERVICE_NAME AppRotateFiles 1
& $nssmExe set $SERVICE_NAME AppRotateBytes 10485760
& $nssmExe set $SERVICE_NAME DisplayName "Drama Monitor - 短剧爆款监控"
& $nssmExe set $SERVICE_NAME Description "海外短剧爆款监控系统"
& $nssmExe set $SERVICE_NAME Start SERVICE_AUTO_START

Write-Host "  服务配置完成" -ForegroundColor Green

# ------ Step 7: Windows 防火墙放行 ------
Write-Host "[7/7] 配置 Windows 防火墙..." -ForegroundColor Yellow

$rule = Get-NetFirewallRule -DisplayName "DramaMonitor_$PORT" -ErrorAction SilentlyContinue
if (-not $rule) {
    New-NetFirewallRule -DisplayName "DramaMonitor_$PORT" -Direction Inbound -Protocol TCP -LocalPort $PORT -Action Allow | Out-Null
    Write-Host "  防火墙规则已添加 (TCP $PORT)" -ForegroundColor Green
} else {
    Write-Host "  防火墙规则已存在，跳过" -ForegroundColor Green
}

# ------ 启动服务 ------
Write-Host ""
Write-Host "启动服务..." -ForegroundColor Yellow
& $nssmExe start $SERVICE_NAME
Start-Sleep -Seconds 3

$finalStatus = & $nssmExe status $SERVICE_NAME 2>&1
if ($finalStatus -match "SERVICE_RUNNING") {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  部署成功!" -ForegroundColor Green
    Write-Host "  访问地址: http://localhost:$PORT" -ForegroundColor Green
    Write-Host "  外网地址: http://<ECS公网IP>:$PORT" -ForegroundColor Green
    Write-Host "" -ForegroundColor Green
    Write-Host "  管理命令:" -ForegroundColor White
    Write-Host "    查看状态: $nssmExe status $SERVICE_NAME" -ForegroundColor White
    Write-Host "    停止服务: $nssmExe stop $SERVICE_NAME" -ForegroundColor White
    Write-Host "    重启服务: $nssmExe restart $SERVICE_NAME" -ForegroundColor White
    Write-Host ('    查看日志: Get-Content ' + $INSTALL_DIR + '\logs\service.log -Tail 50') -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  服务启动异常，请检查日志:" -ForegroundColor Red
    Write-Host ('    ' + $INSTALL_DIR + '\logs\error.log') -ForegroundColor Red
}
