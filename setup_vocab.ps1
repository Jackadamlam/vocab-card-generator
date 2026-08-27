# Setup script: add the `vocab` command to your user PATH and verify dependencies.
# Run this once from anywhere; it locates its own folder via $PSScriptRoot.

$ErrorActionPreference = "Stop"
$toolDir = $PSScriptRoot

Write-Host "Setting up vocab from: $toolDir" -ForegroundColor Cyan

# 1. Sanity check that the tool files are present.
foreach ($f in @("vocab.bat", "vocab_card_generator.py")) {
    if (-not (Test-Path (Join-Path $toolDir $f))) {
        Write-Host "Error: '$f' not found in $toolDir" -ForegroundColor Red
        exit 1
    }
}

# 2. Verify Python is available.
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Error: Python was not found on PATH. Install Python 3.8+ first." -ForegroundColor Red
    exit 1
}
Write-Host "Found: $(python --version)" -ForegroundColor Green

# 3. Verify the 'requests' dependency, offer to install it.
$hasRequests = python -c "import requests" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "The 'requests' package is missing." -ForegroundColor Yellow
    try {
        python -m pip install -r (Join-Path $toolDir "requirements.txt")
    } catch {
        Write-Host "Auto-install failed. Run manually: pip install -r requirements.txt" -ForegroundColor Red
    }
} else {
    Write-Host "Dependency OK: requests" -ForegroundColor Green
}

# 4. Add the folder to the user PATH (idempotent).
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($currentPath -split ';') -contains $toolDir) {
    Write-Host "vocab is already on your PATH." -ForegroundColor Green
} else {
    $newPath = ($currentPath.TrimEnd(';') + ';' + $toolDir)
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "Added $toolDir to your user PATH." -ForegroundColor Green
    Write-Host "Restart your terminal for changes to take effect." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Usage examples:" -ForegroundColor Cyan
Write-Host "  vocab embed" -ForegroundColor White
Write-Host "  vocab tokenizer -t ML LLM" -ForegroundColor White
Write-Host "  vocab embedded --merge" -ForegroundColor White
Write-Host ""
Write-Host "Cards are saved to the tool folder by default (override with -o)." -ForegroundColor Gray
