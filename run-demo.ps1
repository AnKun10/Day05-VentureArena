# Khoi dong ca he thong cho demo bang MOT lenh:  .\run-demo.ps1
# Dung tat ca:                                    .\run-demo.ps1 -Stop
#
# Vi sao can: demo phai bat 3 thu theo dung thu tu (backend truoc, vi bot va UI deu goi no).
# Go tay 3 terminal luc dang bi bam gio la cho de hong nhat - script nay bat ho va TU KIEM TRA
# tung cai da song chua, thay vi de phat hien luc dung truoc giam khao.
#
# LUU Y: file nay co y viet THUAN ASCII (khong dau). PowerShell 5.1 doc file .ps1 khong co BOM
# theo bang ma ANSI, nen ky tu tieng Viet co dau se vo va lam gay parser - da gap that.

param([switch]$Stop)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

function Stop-OnPort($port) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        $conns | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
        Write-Host "  Da dung tien trinh giu cong $port"
    }
}

if ($Stop) {
    Write-Host "Dang dung cac dich vu demo..." -ForegroundColor Yellow
    # Dung theo CONG, khong dung theo ten tien trinh: "Get-Process python" se giet ca
    # nhung python khac cua may, khong lien quan den demo.
    Stop-OnPort 8000
    Stop-OnPort 5173
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*main.py*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host "Da dung." -ForegroundColor Green
    exit 0
}

function Wait-Until($name, $check, $seconds = 40) {
    for ($i = 0; $i -lt $seconds; $i++) {
        if (& $check) { Write-Host "  [OK] $name" -ForegroundColor Green; return $true }
        Start-Sleep -Seconds 1
    }
    Write-Host "  [LOI] $name khong len sau $seconds giay" -ForegroundColor Red
    return $false
}

Write-Host ""
Write-Host "=== 1/3 Backend (cong 8000) ===" -ForegroundColor Cyan
Stop-OnPort 8000   # cong con bi giu thi tien trinh moi se chet am tham, va eval van goi vao ban cu
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command", "cd '$root\codebase\backend'; python -m uvicorn app:app --port 8000"
) -WindowStyle Minimized

$backendUp = Wait-Until "Backend" {
    try { $null = Invoke-RestMethod "http://127.0.0.1:8000/api/health" -TimeoutSec 2; $true } catch { $false }
}
if (-not $backendUp) {
    Write-Host "Dung lai - bot va UI deu can backend." -ForegroundColor Red
    exit 1
}

# Cho biet AI that co bat khong. Demo ma tuong co AI trong khi dang chay rule-based la tinh huong te nhat.
$health = Invoke-RestMethod "http://127.0.0.1:8000/api/health"
if ($health.ai_enabled) {
    Write-Host "  [OK] AI THAT dang bat - provider: $($health.providers -join ', ')" -ForegroundColor Green
} else {
    Write-Host "  [CANH BAO] AI DANG TAT (chua co API key) - dang chay bang luat." -ForegroundColor Yellow
    Write-Host "             Dat key vao codebase\backend\.env roi chay lai. Xem INTEGRATION.md." -ForegroundColor Yellow
}
Write-Host "  Da nap $($health.sessions_loaded) buoi hoc tu $($health.data_dir)"

Write-Host ""
Write-Host "=== 2/3 Web UI (cong 5173) ===" -ForegroundColor Cyan
if (-not (Test-Path "$root\codebase\ui\.env.local")) {
    Copy-Item "$root\codebase\ui\.env.local.example" "$root\codebase\ui\.env.local"
    Write-Host "  Da tao .env.local (goi backend that, khong dung mock)"
}
Stop-OnPort 5173
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command", "cd '$root\codebase\ui'; npm run dev"
) -WindowStyle Minimized

Wait-Until "Web UI" {
    try { $null = Invoke-WebRequest "http://localhost:5173/" -TimeoutSec 2 -UseBasicParsing; $true } catch { $false }
} | Out-Null

Write-Host ""
Write-Host "=== 3/3 Discord bot ===" -ForegroundColor Cyan
if (-not (Test-Path "$root\codebase\bot\.env")) {
    Write-Host "  [LOI] Thieu codebase\bot\.env - copy tu .env.example va dien DISCORD_TOKEN." -ForegroundColor Red
} else {
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command", "cd '$root\codebase\bot'; python main.py"
    ) -WindowStyle Minimized
    Write-Host "  Dang khoi dong - xem cua so bot, cho dong 'Da sync 5 slash command'."
}

Write-Host ""
Write-Host "--------------------------------------------" -ForegroundColor Cyan
Write-Host " Web UI : http://localhost:5173"
Write-Host " Backend: http://127.0.0.1:8000/api/health"
Write-Host " Discord: go /ask trong server test"
Write-Host " Kich ban demo: DEMO.md"
Write-Host "--------------------------------------------" -ForegroundColor Cyan
Write-Host ""