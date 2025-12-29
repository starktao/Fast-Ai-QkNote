$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "Running first-time setup..."
& "$root\\scripts\\setup.ps1"

Write-Host "Starting services..."
& "$root\\scripts\\start.ps1"
