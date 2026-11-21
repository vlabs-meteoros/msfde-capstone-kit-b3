# Participant VM bootstrap (Windows PowerShell). Installs Python/Git/Azure CLI if missing, clones (or updates)
# the capstone repo, creates a virtual environment and runs the offline validation.
#
#   iwr https://raw.githubusercontent.com/vlabs-meteoros/msfde-capstone-kit-b3/main/setup/vm_bootstrap.ps1 -OutFile $env:TEMP\b.ps1 -UseBasicParsing; powershell -ExecutionPolicy Bypass -File $env:TEMP\b.ps1
param(
  [string]$RepoUrl = "https://github.com/vlabs-meteoros/msfde-capstone-kit-b3.git",
  [string]$Target = "$env:USERPROFILE\msfde-capstone-kit"
)
$ErrorActionPreference = "Stop"

function Refresh-Path {
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}
function Ensure($cmd, $wingetId) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
    Write-Host "Installing $wingetId ..."
    winget install --id $wingetId -e --silent --accept-package-agreements --accept-source-agreements
    Refresh-Path
  } else { Write-Host "$cmd found" }
}
Ensure python "Python.Python.3.12"
Ensure git "Git.Git"
Ensure az "Microsoft.AzureCLI"

if (Test-Path "$Target\.git") {
  Write-Host "Repo exists - pulling latest"
  git -C $Target pull --ff-only
} else {
  if (Test-Path $Target) {
    $old = "$Target-old-$(Get-Date -Format yyyyMMddHHmmss)"
    Write-Host "Existing non-git folder moved to $old"
    Move-Item $Target $old
  }
  git clone $RepoUrl $Target
}
Set-Location $Target

if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if (-not (Test-Path .env)) { Copy-Item .env.sample .env }
& .\.venv\Scripts\python.exe tools\validate_kit.py

Write-Host ""
Write-Host "Next:"
Write-Host "  cd $Target ; .\.venv\Scripts\activate"
Write-Host "  notepad .env        # replace every N with your user number"
Write-Host "  az login            # sign in as fdeuserN@justlabs.online"
Write-Host "  python common\starter\agent_app.py doctor --usecase manufacturing"
