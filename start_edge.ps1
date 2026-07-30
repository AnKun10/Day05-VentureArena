param(
    [string]$ProfilePath = (Join-Path $PSScriptRoot "edge-profile"),
    [int]$Port = 9222
)

$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edge)) { $edge = "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe" }
if (-not (Test-Path $edge)) { throw "Microsoft Edge was not found. Set the Edge path in start_edge.ps1." }
New-Item -ItemType Directory -Force -Path $ProfilePath | Out-Null
Start-Process -FilePath $edge -ArgumentList "--remote-debugging-port=$Port", "--user-data-dir=$ProfilePath"
Write-Host "Edge started. Log into Discord manually, then run the collector."
