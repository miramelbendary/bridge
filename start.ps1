# BRIDGE one-command local start (Windows PowerShell).
#   Double-click start.cmd, or run:  powershell -ExecutionPolicy Bypass -File start.ps1
# First run: creates a Python virtual environment, installs dependencies, creates a local SQLite
# database with demo data, builds the frontend. Later runs start in a few seconds.
# Requirements: Python 3.12+ and Node.js 20.9+ on PATH. No API keys or database server needed.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "`nERROR: $msg" -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }

if ($Root.Length -gt 120) {
  Write-Host "WARNING: this folder path is very long ($($Root.Length) characters)." -ForegroundColor Yellow
  Write-Host "Windows may fail to load some components. If setup fails, move the folder to e.g. C:\bridge." -ForegroundColor Yellow
}

# --- prerequisites -------------------------------------------------------------------------
# Windows Explorer keeps the PATH it had at sign-in, so a program installed afterwards (Node.js,
# Python) is invisible to anything double-clicked. Reload PATH from the registry, then add the
# default install folders as a last resort.
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = (@($machinePath, $userPath, $env:Path) | Where-Object { $_ }) -join ";"
foreach ($dir in @("$env:ProgramFiles\nodejs", "$env:LOCALAPPDATA\Programs\Python\Launcher")) {
  if ((Test-Path $dir) -and ($env:Path -notlike "*$dir*")) { $env:Path += ";$dir" }
}

$PyExe = $null
$PyArgs = @()
foreach ($candidate in @(@{ exe = "py"; args = @("-3") }, @{ exe = "python"; args = @() })) {
  if (-not (Get-Command $candidate.exe -ErrorAction SilentlyContinue)) { continue }
  try {
    $v = & $candidate.exe @($candidate.args + @("-c", "import sys; print('%d.%d' % sys.version_info[:2])")) 2>$null
    if ($LASTEXITCODE -eq 0 -and [version]$v -ge [version]"3.12") { $PyExe = $candidate.exe; $PyArgs = $candidate.args; break }
  } catch {}
}
if (-not $PyExe) { Fail "Python 3.12 or newer is required. Install it from https://www.python.org/downloads/ (tick 'Add to PATH')." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Fail "Node.js was not found. Install the LTS version from https://nodejs.org/, then sign out and back in (or restart) and try again."
}
$nodeVersion = (& node --version 2>$null | Out-String).Trim()
$nodeMajor = 0
if ($nodeVersion -match '^v(\d+)\.') { $nodeMajor = [int]$Matches[1] }
if ($nodeMajor -lt 20) { Fail "Node.js 20.9+ is required, but 'node --version' returned '$nodeVersion'. Install the LTS version from https://nodejs.org/." }
Write-Host "Using Python ($PyExe $($PyArgs -join ' ')) and Node.js $nodeVersion"
if ($env:BRIDGE_CHECK_ONLY) { Write-Host "Prerequisites OK."; exit 0 }

# --- backend --------------------------------------------------------------------------------
$Venv = Join-Path $Backend ".venv"
$VPy = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $VPy)) {
  Step "Creating Python virtual environment"
  & $PyExe @($PyArgs + @("-m", "venv", $Venv))
  if ($LASTEXITCODE -ne 0) { Fail "Could not create the virtual environment." }
}
$Stamp = Join-Path $Venv ".bridge-installed"
$Lock = Join-Path $Backend "requirements.lock"
if (-not (Test-Path $Stamp) -or (Get-Item $Lock).LastWriteTime -gt (Get-Item $Stamp).LastWriteTime) {
  Step "Installing backend dependencies (first run takes a minute)"
  & $VPy -m pip install --quiet --upgrade pip
  & $VPy -m pip install --quiet -r $Lock
  if ($LASTEXITCODE -ne 0) { Fail "Installing backend dependencies failed." }
  & $VPy -m pip install --quiet --no-deps -e $Backend
  if ($LASTEXITCODE -ne 0) { Fail "Installing the backend package failed." }
  Set-Content -Path $Stamp -Value (Get-Date)
}

$EnvFile = Join-Path $Backend ".env"
if (-not (Test-Path $EnvFile)) {
  Step "Creating backend/.env (local SQLite database, offline mock AI)"
  $secret = & $VPy -c "import secrets; print(secrets.token_urlsafe(48))"
  @"
ENVIRONMENT=development
DATABASE_URL=sqlite:///./bridge_local.db
AUTH_PROVIDER=local
LOCAL_JWT_SECRET=$secret
CORS_ORIGINS=http://localhost:3000
# AI: "mock" works offline for free. To use Claude, set AI_PROVIDER=anthropic and add your key:
AI_PROVIDER=mock
ANTHROPIC_API_KEY=
"@ | Set-Content -Path $EnvFile -Encoding ascii
}

Step "Preparing the database and scenarios"
Push-Location $Backend
& $VPy -m app.cli setup
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { Fail "Database setup failed." }

# --- frontend -------------------------------------------------------------------------------
Push-Location $Frontend
if (-not (Test-Path "node_modules")) {
  Step "Installing frontend dependencies (first run takes a minute)"
  npm ci --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { Pop-Location; Fail "npm ci failed." }
}
if (-not (Test-Path ".env.local")) {
  "BRIDGE_API_URL=http://127.0.0.1:8000`nBRIDGE_DEMO_MODE=1" | Set-Content -Path ".env.local" -Encoding ascii
}
$needBuild = -not (Test-Path ".next\BUILD_ID")
if (-not $needBuild) {
  $built = (Get-Item ".next\BUILD_ID").LastWriteTime
  $newer = Get-ChildItem -Recurse -File src | Where-Object { $_.LastWriteTime -gt $built } | Select-Object -First 1
  if ($newer) { $needBuild = $true }
}
if ($needBuild) {
  Step "Building the frontend"
  $env:NEXT_TELEMETRY_DISABLED = "1"
  npm run build
  if ($LASTEXITCODE -ne 0) { Pop-Location; Fail "Frontend build failed." }
}
Pop-Location

# --- run ------------------------------------------------------------------------------------
Step "Starting BRIDGE"
$api = Start-Process -FilePath $VPy -ArgumentList "-m","uvicorn","app.main:create_app","--factory","--host","127.0.0.1","--port","8000" -WorkingDirectory $Backend -PassThru -WindowStyle Hidden
try {
  Start-Sleep -Seconds 3
  Write-Host ""
  Write-Host "  BRIDGE is running:  http://localhost:3000" -ForegroundColor Green
  Write-Host "  Demo logins (password bridge-demo-2026):"
  Write-Host "    demo.student@example.com · demo.professor@example.com · demo.admin@example.com"
  Write-Host "  Press Ctrl+C to stop."
  if (-not $env:BRIDGE_NO_BROWSER) { Start-Process "http://localhost:3000" }
  Push-Location $Frontend
  $env:NEXT_TELEMETRY_DISABLED = "1"
  npm run start -- -p 3000
} finally {
  Pop-Location -ErrorAction SilentlyContinue
  if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue }
  Write-Host "BRIDGE stopped."
}
