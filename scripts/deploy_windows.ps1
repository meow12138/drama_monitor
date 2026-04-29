# ============================================================
#  Drama Monitor - Windows Server Deploy Script
#  For: Windows Server 2022 (Alibaba Cloud ECS)
#
#  Usage:
#    1. RDP into ECS
#    2. Open PowerShell as Administrator
#    3. Run: Set-ExecutionPolicy RemoteSigned -Force
#    4. Run: .\deploy_windows.ps1
#
#  Prerequisites:
#    - Python 3.10+ installed (with Add to PATH checked)
#    - Git for Windows installed
#    - Alibaba Cloud security group allows TCP 8000
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
Write-Host "  Drama Monitor - Deploy Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ------ Step 1: Check prerequisites ------
Write-Host "[1/7] Checking prerequisites..." -ForegroundColor Yellow

try { $pyVer = python --version 2>&1; Write-Host "  Python: $pyVer" -ForegroundColor Green }
catch { Write-Host "  ERROR: Python not found. Install Python 3.10+ with Add to PATH." -ForegroundColor Red; exit 1 }

try { $gitVer = git --version 2>&1; Write-Host "  Git: $gitVer" -ForegroundColor Green }
catch { Write-Host "  ERROR: Git not found. Install Git for Windows first." -ForegroundColor Red; exit 1 }

# ------ Step 2: Clone / pull code ------
Write-Host "[2/7] Fetching code..." -ForegroundColor Yellow

if (Test-Path $INSTALL_DIR) {
    Write-Host "  Directory exists, pulling latest..."
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
Write-Host "  Code ready: $INSTALL_DIR" -ForegroundColor Green

# ------ Step 3: Create venv ------
Write-Host "[3/7] Setting up virtual environment..." -ForegroundColor Yellow

if (-not (Test-Path "$INSTALL_DIR\venv")) {
    python -m venv venv
    Write-Host "  venv created"
} else {
    Write-Host "  venv already exists, skipping"
}

& "$INSTALL_DIR\venv\Scripts\pip.exe" install -r requirements.txt -q
Write-Host "  Dependencies installed" -ForegroundColor Green

# ------ Step 4: Create logs directory ------
Write-Host "[4/7] Creating logs directory..." -ForegroundColor Yellow

$logsDir = Join-Path $INSTALL_DIR "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}
Write-Host "  Logs: $logsDir" -ForegroundColor Green

# ------ Step 5: Download NSSM ------
Write-Host "[5/7] Setting up NSSM..." -ForegroundColor Yellow

$nssmExe = Join-Path $NSSM_DIR "nssm.exe"
if (-not (Test-Path $nssmExe)) {
    Write-Host "  Downloading NSSM..."
    $zipPath = Join-Path $env:TEMP "nssm.zip"
    Invoke-WebRequest -Uri $NSSM_URL -OutFile $zipPath -UseBasicParsing
    $extractDir = Join-Path $env:TEMP "nssm_extract"
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
    if (-not (Test-Path $NSSM_DIR)) { New-Item -ItemType Directory -Path $NSSM_DIR | Out-Null }
    Copy-Item (Join-Path $extractDir "nssm-2.24\win64\nssm.exe") $nssmExe -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
    Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  NSSM installed: $NSSM_DIR" -ForegroundColor Green
} else {
    Write-Host "  NSSM already exists, skipping" -ForegroundColor Green
}

# ------ Step 6: Register Windows service ------
Write-Host "[6/7] Registering Windows service..." -ForegroundColor Yellow

$status = & $nssmExe status $SERVICE_NAME 2>&1

if ($status -match "SERVICE_RUNNING") {
    Write-Host "  Service is running, stopping first..."
    & $nssmExe stop $SERVICE_NAME
    Start-Sleep -Seconds 2
}

$uvicornExe = Join-Path $INSTALL_DIR "venv\Scripts\uvicorn.exe"
$serviceLog = Join-Path $logsDir "service.log"
$errorLog = Join-Path $logsDir "error.log"

if ($status -notmatch "SERVICE_") {
    & $nssmExe install $SERVICE_NAME $uvicornExe
    Write-Host "  Service registered"
} else {
    Write-Host "  Service exists, updating config"
}

& $nssmExe set $SERVICE_NAME AppParameters "app.main:app --host 0.0.0.0 --port $PORT"
& $nssmExe set $SERVICE_NAME AppDirectory $INSTALL_DIR
& $nssmExe set $SERVICE_NAME AppStdout $serviceLog
& $nssmExe set $SERVICE_NAME AppStderr $errorLog
& $nssmExe set $SERVICE_NAME AppRotateFiles 1
& $nssmExe set $SERVICE_NAME AppRotateBytes 10485760
& $nssmExe set $SERVICE_NAME DisplayName "Drama Monitor"
& $nssmExe set $SERVICE_NAME Description "Drama Monitor Service"
& $nssmExe set $SERVICE_NAME Start SERVICE_AUTO_START

Write-Host "  Service configured" -ForegroundColor Green

# ------ Step 7: Firewall rule ------
Write-Host "[7/7] Configuring Windows Firewall..." -ForegroundColor Yellow

$ruleName = "DramaMonitor_$PORT"
$rule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $rule) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $PORT -Action Allow | Out-Null
    Write-Host "  Firewall rule added (TCP $PORT)" -ForegroundColor Green
} else {
    Write-Host "  Firewall rule exists, skipping" -ForegroundColor Green
}

# ------ Start service ------
Write-Host ""
Write-Host "Starting service..." -ForegroundColor Yellow
& $nssmExe start $SERVICE_NAME
Start-Sleep -Seconds 3

$finalStatus = & $nssmExe status $SERVICE_NAME 2>&1
if ($finalStatus -match "SERVICE_RUNNING") {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Deploy SUCCESS!" -ForegroundColor Green
    Write-Host "  Local:  http://localhost:$PORT" -ForegroundColor Green
    Write-Host "  Public: http://<ECS_PUBLIC_IP>:$PORT" -ForegroundColor Green
    Write-Host "" -ForegroundColor Green
    Write-Host "  Commands:" -ForegroundColor White
    Write-Host "    Status:  $nssmExe status $SERVICE_NAME" -ForegroundColor White
    Write-Host "    Stop:    $nssmExe stop $SERVICE_NAME" -ForegroundColor White
    Write-Host "    Restart: $nssmExe restart $SERVICE_NAME" -ForegroundColor White
    Write-Host "    Logs:    Get-Content $serviceLog -Tail 50" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  Service start FAILED. Check error log:" -ForegroundColor Red
    Write-Host "    $errorLog" -ForegroundColor Red
}
