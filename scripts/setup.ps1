$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

function Ensure-Command {
    param(
        [string]$Command,
        [string]$WingetId,
        [string]$DisplayName
    )

    if (Get-Command $Command -ErrorAction SilentlyContinue) {
        return $true
    }

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Installing $DisplayName via winget..."
        winget install -e --id $WingetId --accept-source-agreements --accept-package-agreements
    } else {
        throw "Missing $DisplayName and winget is not available. Install it manually and re-run this script."
    }

    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        throw "$DisplayName install finished, but command not found. Restart the terminal and re-run this script."
    }
    return $true
}

Ensure-Command -Command "python" -WingetId "Python.Python.3.12" -DisplayName "Python 3.12+"
Ensure-Command -Command "node" -WingetId "OpenJS.NodeJS.LTS" -DisplayName "Node.js LTS"

$toolsDir = Join-Path $root "tools"
$ffmpegDir = Join-Path $toolsDir "ffmpeg"
$ffmpegExe = Join-Path $ffmpegDir "bin\ffmpeg.exe"

if (-not (Test-Path $ffmpegExe)) {
    Write-Host "Downloading ffmpeg..."
    New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null
    $zipPath = Join-Path $toolsDir "ffmpeg-release-essentials.zip"
    Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $toolsDir -Force

    $extractDir = Get-ChildItem -Path $toolsDir -Directory | Where-Object { $_.Name -like "ffmpeg-*-essentials_build" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $extractDir) {
        throw "ffmpeg archive layout unexpected."
    }

    if (-not (Test-Path $ffmpegDir)) {
        Move-Item -Path $extractDir.FullName -Destination $ffmpegDir
    }
}

$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

Write-Host "Setting up backend virtual environment..."
Set-Location $backendDir
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Deactivate

Write-Host "Installing frontend dependencies..."
Set-Location $frontendDir
npm install

Write-Host "Setup completed."
