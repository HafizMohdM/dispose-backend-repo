$ErrorActionPreference = "Stop"

# Check if the virtual environment exists
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    # Dot-source the activation script
    . .\venv\Scripts\Activate.ps1
    
    Write-Host "Starting Uvicorn server..." -ForegroundColor Green
    uvicorn app.main:app --reload
} else {
    Write-Host "Error: Virtual environment not found in .\venv" -ForegroundColor Red
    Write-Host "Please recreate it using 'python -m venv venv' first." -ForegroundColor Yellow
}

