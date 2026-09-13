# install.ps1 — 1-Click Installer for Forge Harness on Windows
# Installs Forge into an isolated user environment and configures global PATH.

[CmdletBinding()]
param(
    [switch]$Dev = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=== Forge Harness Windows Installer ===" -ForegroundColor Cyan

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "Python is not found on PATH. Please install Python 3.11+ from https://www.python.org/ or via 'winget install Python.Python.3.13'"
    exit 1
}

$pyVer = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$major, $minor = $pyVer.Split('.') | ForEach-Object { [int]$_ }
if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
    Write-Error "Forge requires Python 3.11 or higher. Detected Python version: $pyVer"
    exit 1
}
Write-Host "[✓] Detected Python $pyVer ($($pythonCmd.Source))" -ForegroundColor Green

# 2. Paths
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$forgeHome = Join-Path $HOME ".forge-harness"
$venvDir = Join-Path $forgeHome "venv"
$binDir = Join-Path $HOME ".local\bin"

Write-Host "[*] Target Environment: $venvDir" -ForegroundColor Gray
Write-Host "[*] Shim Directory:     $binDir" -ForegroundColor Gray

if (-not (Test-Path $forgeHome)) {
    New-Item -ItemType Directory -Path $forgeHome -Force | Out-Null
}
if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}

# 3. Create or reuse dedicated virtualenv
if (-not (Test-Path (Join-Path $venvDir "Scripts\python.exe"))) {
    Write-Host "[*] Creating dedicated virtualenv at $venvDir..." -ForegroundColor Yellow
    & python -m venv $venvDir
} else {
    Write-Host "[✓] Dedicated virtualenv already exists" -ForegroundColor Green
}

$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip = Join-Path $venvDir "Scripts\pip.exe"
$venvForge = Join-Path $venvDir "Scripts\forge.exe"

# 4. Install Forge Package
Write-Host "[*] Installing/updating Forge Harness package..." -ForegroundColor Yellow
$installTarget = if ($Dev) { "$repoRoot[grammars,dev]" } else { "$repoRoot[grammars]" }
& $venvPython -m pip install --disable-pip-version-check --quiet -e $installTarget

# 5. Create Shims in ~/.local/bin
$cmdContent = @"
@echo off
"$venvForge" %*
"@
Set-Content -Path (Join-Path $binDir "forge.cmd") -Value $cmdContent -Encoding ASCII

$ps1Content = @"
& "$venvForge" @args
"@
Set-Content -Path (Join-Path $binDir "forge.ps1") -Value $ps1Content -Encoding UTF8

Write-Host "[✓] Created shims: forge.cmd and forge.ps1 in $binDir" -ForegroundColor Green

# 6. Check and update User PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$paths = $userPath -split ';' | Where-Object { $_ -ne "" }
if ($paths -notcontains $binDir) {
    Write-Host "[*] Adding $binDir to User PATH..." -ForegroundColor Yellow
    $newPath = if ($userPath) { "$userPath;$binDir" } else { $binDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "[✓] Added $binDir to User PATH permanently" -ForegroundColor Green
} else {
    Write-Host "[✓] $binDir is already in User PATH" -ForegroundColor Green
}

# Update current session PATH so test works immediately
if (($env:PATH -split ';') -notcontains $binDir) {
    $env:PATH = "$binDir;$env:PATH"
}

# 7. Verification
Write-Host "`n[*] Verifying installation..." -ForegroundColor Cyan
& $venvForge doctor

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host " [SUCCESS] Forge Harness đã được cài đặt thành công!" -ForegroundColor Green
Write-Host " Bạn có thể mở bất kỳ terminal nào và gõ lệnh: forge" -ForegroundColor Green
Write-Host " Ví dụ: forge --help  hoặc  forge doctor" -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Green
