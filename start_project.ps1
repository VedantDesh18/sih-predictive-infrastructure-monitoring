# Start Backend and Frontend concurrently from the repository root.
$repositoryRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $repositoryRoot "venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Python virtual environment not found at $python. Create it and install apps/api/requirements.txt first."
}

Write-Host "Starting SIH Project..." -ForegroundColor Green

# The app-dir keeps imports correct while Settings resolves the repository-root .env.
$apiJob = Start-Job -ArgumentList $repositoryRoot, $python -ScriptBlock {
    param($root, $pythonExecutable)
    Set-Location $root
    & $pythonExecutable -m uvicorn app.main:app --app-dir "$root\apps\api" --host 0.0.0.0 --port 8000 --reload
}

$webJob = Start-Job -ArgumentList $repositoryRoot -ScriptBlock {
    param($root)
    Set-Location "$root\apps\web"
    npm run dev
}

Write-Host "API starting on http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Web frontend starting on http://localhost:3000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop both." -ForegroundColor Yellow

try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "Stopping servers..." -ForegroundColor Red
    Stop-Job -Job $apiJob
    Stop-Job -Job $webJob
    Remove-Job -Job $apiJob
    Remove-Job -Job $webJob
}
