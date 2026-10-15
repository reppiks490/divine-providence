# Install and verify the Divine Providence hub plus the separate ICARUS runtime.
# The runtime starts in delayed Yahoo read-only mode unless -NoStartPlant is set.
param(
    [string]$EnginePath = "",
    [string]$DataPath = "",
    [switch]$NoStartPlant
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$EngineUrl = "https://github.com/reppiks490/Icarus.git"

function Invoke-Checked([string]$Command, [string[]]$Arguments) {
    $savedErrorAction = $ErrorActionPreference
    try {
        # PowerShell 5.1 can treat native stderr as a terminating PowerShell error.
        $ErrorActionPreference = "Continue"
        & $Command @Arguments
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedErrorAction
    }
    if ($code -ne 0) {
        throw "Command failed ($code): $Command $($Arguments -join ' ')"
    }
}

function Test-PlantHealth {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8791/healthz" -TimeoutSec 2
        return ([bool]$health.ok -and @($health.assets) -contains "NQ")
    } catch {
        return $false
    }
}

if (-not $EnginePath) {
    $EnginePath = Join-Path (Split-Path -Parent $Root) "icarus-engine"
}
if (-not $DataPath) {
    $DataPath = Join-Path $env:LOCALAPPDATA "ICARUS"
}
$EnginePath = [System.IO.Path]::GetFullPath($EnginePath)
$DataPath = [System.IO.Path]::GetFullPath($DataPath)
if ([string]::Equals($EnginePath, [System.IO.Path]::GetFullPath($Root), [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "EnginePath must be separate from the Divine Providence checkout"
}

Push-Location $Root
try {
    # Install and fully validate the 12-subsystem Divine Providence build first.
    & (Join-Path $PSScriptRoot "bootstrap.ps1") -Validate
    if ($LASTEXITCODE -ne 0) { throw "Divine Providence bootstrap/validation failed" }
    $HubPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path $HubPython)) { throw "Divine Providence Python environment was not created" }

    # Reuse the validated Python version, but keep each repository isolated.
    if (-not (Test-Path $EnginePath)) {
        $parent = Split-Path -Parent $EnginePath
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        Invoke-Checked "git" @("clone", "--branch", "main", "--single-branch", $EngineUrl, $EnginePath)
    } else {
        if (-not (Test-Path (Join-Path $EnginePath ".git"))) {
            throw "Engine path exists but is not a Git checkout: $EnginePath"
        }
        $remote = (& git -C $EnginePath remote get-url origin 2>$null).Trim()
        if ($LASTEXITCODE -ne 0) { throw "Cannot read the engine checkout's origin: $EnginePath" }
        if ($remote -notmatch "^(https://github\.com/reppiks490/Icarus\.git|git@github\.com:reppiks490/Icarus\.git)$") {
            throw "Engine checkout has an unexpected origin: $remote"
        }
        $changes = & git -C $EnginePath status --porcelain
        if ($changes) { throw "Engine checkout has local changes; refusing to overwrite them: $EnginePath" }
        Invoke-Checked "git" @("-C", $EnginePath, "fetch", "origin", "main")
        Invoke-Checked "git" @("-C", $EnginePath, "checkout", "main")
        Invoke-Checked "git" @("-C", $EnginePath, "pull", "--ff-only", "origin", "main")
    }

    $EnginePython = Join-Path $EnginePath ".venv\Scripts\python.exe"
    if (-not (Test-Path $EnginePython)) {
        Invoke-Checked $HubPython @("-m", "venv", (Join-Path $EnginePath ".venv"))
    }
    Push-Location $EnginePath
    try {
        Invoke-Checked $EnginePython @("-m", "pip", "install", "--upgrade", "pip")
        Invoke-Checked $EnginePython @("-m", "pip", "install", "-e", ".[bridge,dev,ml,databento]")
        Invoke-Checked $EnginePython @("-m", "pytest", "tests_engine", "-q")
        Invoke-Checked $EnginePython @("-m", "icarus_engine", "doctor")

        $env:ICARUS_HOME = $DataPath
        Invoke-Checked $EnginePython @("-m", "icarus_plant", "--root", $DataPath, "init")

        if (-not $NoStartPlant) {
            if (-not (Test-PlantHealth)) {
                Invoke-Checked $EnginePython @("-m", "icarus_plant", "--root", $DataPath,
                                               "start", "--assets", "NQ", "--feed", "yahoo", "--no-browser")
            }
            $healthy = $false
            for ($attempt = 0; $attempt -lt 30; $attempt++) {
                if (Test-PlantHealth) { $healthy = $true; break }
                Start-Sleep -Seconds 2
            }
            if (-not $healthy) { throw "ICARUS plant did not become healthy at http://127.0.0.1:8791/healthz" }
        }
    } finally {
        Pop-Location
    }

    Write-Host "Full ICARUS install and validation completed."
    Write-Host "Divine Providence: $Root"
    Write-Host "Trading engine:    $EnginePath"
    Write-Host "Engine data:       $DataPath"
    Write-Host "Phone UI:          https://icarus-command-center-mobile.cloudyrook1.chatgpt.site"
    if ($NoStartPlant) {
        Write-Host "Plant: installed and initialized; not started (-NoStartPlant)."
    } else {
        Write-Host "Plant: healthy on loopback using delayed Yahoo NQ data."
    }
    Write-Host "TradingView alerts, broker credentials, and paid market-data entitlements require their own configuration."
    Write-Host "Phone UI pairing additionally needs the local phone relay and a Cloudflare Quick Tunnel; see the runtime docs/PHONE_ACCESS.md."
} finally {
    Pop-Location
}
