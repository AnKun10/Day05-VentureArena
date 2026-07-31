# Khởi động cả hệ thống cho demo bằng MỘT lệnh: .\run-demo.ps1
#
# Vì sao cần: demo phải bật 3 thứ theo đúng thứ tự (backend trước, vì bot và UI đều gọi nó).
# Gõ tay 3 terminal lúc đang bị bấm giờ là chỗ dễ hỏng nhất — script này bật hộ và TỰ KIỂM TRA
# từng cái đã sống chưa, thay vì để phát hiện lúc đứng trước giám khảo.
#
# Dừng tất cả: .\run-demo.ps1 -Stop

param([switch]$Stop)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

if ($Stop) {
    Write-Host "Dang dung cac tien trinh demo..." -ForegroundColor Yellow
    Get-Process python, node -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and $_.Path -notlike "*WindowsApps*" } |
        Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "Da dung." -ForegroundColor Green
    exit 0
}

function Wait-Until($name, $check, $seconds = 30) {
    for ($i = 0; $i -lt $seconds; $i++) {
        if (& $check) { Write-Host "  [OK] $name" -ForegroundColor Green; return $true }
        Start-Sleep -Seconds 1
    }
    Write-Host "  [LOI] $name khong len sau $seconds giay" -ForegroundColor Red
    return $false
}

Write-Host "`n=== 1/3 Backend (cong 8000) ===" -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\codebase\backend'; python -m uvicorn app:app --port 8000"
) -WindowStyle Minimized

$backendUp = Wait-Until "Backend" {
    try { $null = Invoke-RestMethod "http://127.0.0.1:8000/api/health" -TimeoutSec 2; $true } catch { $false }
}
if (-not $backendUp) { Write-Host "Dung lai — bot va UI deu can backend." -ForegroundColor Red; exit 1 }

# Cho biet AI that co bat khong. Demo ma tuong co AI trong khi dang chay rule-based la tinh huong te nhat.
$health = Invoke-RestMethod "http://127.0.0.1:8000/api/health"
if ($health.ai_enabled) {
    Write-Host "  [OK] AI THAT dang bat — provider: $($health.providers -join ', ')" -ForegroundColor Green
} else {
    Write-Host "  [CANH BAO] AI DANG TAT (chua co API key) — dang chay bang luat." -ForegroundColor Yellow
    Write-Host "             Dat key vao codebase\backend\.env roi chay lai. Xem INTEGRATION.md." -ForegroundColor Yellow
}
Write-Host "  Da nap $($health.sessions_loaded) buoi hoc tu $($health.data_dir)"

Write-Host "`n=== 2/3 Web UI (cong 5173) ===" -ForegroundColor Cyan
if (-not (Test-Path "$root\codebase\ui\.env.local")) {
    Copy-Item "$root\codebase\ui\.env.local.example" "$root\codebase\ui\.env.local"
    Write-Host "  Da tao .env.local (goi backend that, khong dung mock)"
}
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command", "cd '$root\codebase\ui'; npm run dev"
) -WindowStyle Minimized

Wait-Until "Web UI" {
    try { $null = Invoke-WebRequest "http://localhost:5173/" -TimeoutSec 2 -UseBasicParsing; $true } catch { $false }
} | Out-Null

Write-Host "`n=== 3/3 Discord bot ===" -ForegroundColor Cyan
if (-not (Test-Path "$root\codebase\bot\.env")) {
    Write-Host "  [LOI] Thieu codebase\bot\.env — copy tu .env.example va dien DISCORD_TOKEN." -ForegroundColor Red
} else {
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command", "cd '$root\codebase\bot'; python main.py"
    ) -WindowStyle Minimized
    Write-Host "  Dang khoi dong — xem cua so bot, cho dong 'Da sync 5 slash command'."
}

Write-Host "`n--------------------------------------------" -ForegroundColor Cyan
Write-Host " Web UI : http://localhost:5173"
Write-Host " Backend: http://127.0.0.1:8000/api/health"
Write-Host " Discord: go /ask trong server test"
Write-Host " Kich ban demo: DEMO.md"
Write-Host "--------------------------------------------`n" -ForegroundColor Cyan
