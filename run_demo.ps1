# Start Field Shift for the demo (plan §3.3, Step 15).
#
#   .\run_demo.ps1            offline: demo fields only, served from snapshots/ (no internet needed)
#   .\run_demo.ps1 -Online    live NASA POWER / soil / EONET data for any point
#   .\run_demo.ps1 -Rebuild   rebuild the website first (after code changes)
#
# Backend on http://localhost:8000, website on http://localhost:3000. Close the two
# windows (or press Ctrl+C in each) to stop.
param([switch]$Online, [switch]$Rebuild)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# Child windows inherit this, so the backend reads snapshots instead of the network
if ($Online) { Remove-Item Env:OFFLINE -ErrorAction SilentlyContinue } else { $env:OFFLINE = "1" }

if ($Rebuild -or -not (Test-Path "$root\frontend\.next\BUILD_ID")) {
    Write-Host "Building the website..."
    Push-Location "$root\frontend"
    npm run build
    $built = $LASTEXITCODE
    Pop-Location
    if ($built -ne 0) { throw "Website build failed" }
}

Start-Process powershell -WorkingDirectory "$root\backend" -ArgumentList "-NoExit", "-Command",
    ".\.venv\Scripts\python.exe -m uvicorn main:app --port 8000"
Start-Process powershell -WorkingDirectory "$root\frontend" -ArgumentList "-NoExit", "-Command", "npm run start"

Write-Host "Waiting for the servers..."
foreach ($url in "http://localhost:8000/api/demo-sites", "http://localhost:3000") {
    for ($i = 0; $i -lt 60; $i++) {
        try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 $url | Out-Null; break } catch { Start-Sleep 1 }
    }
}
Start-Process "http://localhost:3000"
Write-Host ("Field Shift is running ({0} mode): http://localhost:3000" -f ($(if ($Online) { "online" } else { "offline" })))
