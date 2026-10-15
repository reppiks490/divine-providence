# Install and verify the Divine Providence hub plus the separate ICARUS runtime.
# The runtime starts in delayed Yahoo read-only mode unless -NoStartPlant is set.
param(
    [string]$EnginePath = "",
    [string]$DataPath = "",
    [ValidateSet("yahoo", "file", "databento")]
    [string]$Feed = "yahoo",
    [switch]$NoStartPlant,
    [switch]$StopPlantAfterVerification
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

function Test-OwnerToken([string]$Token) {
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:8791/api/access" `
            -Headers @{ Authorization = "Bearer $Token" } -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

function Get-OwnerToken([string]$TokenPath) {
    if (Test-Path $TokenPath) {
        $existing = (Get-Content -Raw -Path $TokenPath).Trim()
        if ($existing.Length -ge 32 -and $existing -ne "icarus") { return $existing }
    }
    $directory = Split-Path -Parent $TokenPath
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $token = [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
    [System.IO.File]::WriteAllText($TokenPath, $token, [System.Text.Encoding]::ASCII)
    return $token
}

function Protect-OwnerTokenInLogs([string[]]$Paths, [string]$Token) {
    if ([string]::IsNullOrWhiteSpace($Token)) { return }
    foreach ($path in $Paths) {
        if ([string]::IsNullOrWhiteSpace($path) -or -not (Test-Path $path)) { continue }
        try {
            $contents = [System.IO.File]::ReadAllText($path)
            if ($contents.Contains($Token)) {
                [System.IO.File]::WriteAllText(
                    $path,
                    $contents.Replace($Token, "[REDACTED]"),
                    [System.Text.Encoding]::UTF8
                )
            }
        } catch [System.IO.IOException] {
            # A running plant still owns its redirected stderr handle; retry
            # from the caller's finally block after the process is stopped.
            continue
        } catch [System.UnauthorizedAccessException] {
            continue
        }
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
    $startedByBootstrap = $false
    $plantHealthy = $false
    $ownerTokenPath = Join-Path $DataPath "secrets\owner-token.txt"
    try {
        Invoke-Checked $EnginePython @("-m", "pip", "install", "--upgrade", "pip")
        Invoke-Checked $EnginePython @("-m", "pip", "install", "-e", ".[bridge,dev,ml,databento]")
        Invoke-Checked $EnginePython @("-m", "pytest", "tests_engine", "-q")
        Invoke-Checked $EnginePython @("-m", "icarus_engine.cli", "doctor", "--json")

        $env:ICARUS_HOME = $DataPath
        Invoke-Checked $EnginePython @("-m", "icarus_plant", "--root", $DataPath, "init")

        if (-not $NoStartPlant) {
            $running = Test-PlantHealth
            if ($running) {
                if (-not (Test-Path $ownerTokenPath)) {
                    throw "An ICARUS engine is already healthy but has no bootstrap-managed owner token. Stop that plant before running this bootstrap."
                }
                $ownerToken = (Get-Content -Raw -Path $ownerTokenPath).Trim()
                if ($ownerToken.Length -lt 32 -or -not (Test-OwnerToken $ownerToken)) {
                    throw "The running ICARUS plant does not accept the owner token saved at $ownerTokenPath. Stop that plant before running this bootstrap."
                }
                $plantHealthy = $true
            } else {
                $ownerToken = Get-OwnerToken $ownerTokenPath
                $logsPath = Join-Path $DataPath "logs"
                New-Item -ItemType Directory -Force -Path $logsPath | Out-Null
                $logStamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")
                $stderrPath = Join-Path $logsPath "bootstrap-plant.$logStamp.stderr.log"
                $argumentLine = "-m icarus_plant --root `"$DataPath`" start --assets NQ --feed $Feed --token $ownerToken --no-browser"
                $plantProcess = Start-Process -FilePath $EnginePython -ArgumentList $argumentLine `
                    -WorkingDirectory $EnginePath -RedirectStandardOutput "NUL" `
                    -RedirectStandardError $stderrPath -WindowStyle Hidden -PassThru
                $startedByBootstrap = $true
            }
            for ($attempt = 0; $attempt -lt 30; $attempt++) {
                if ((Test-PlantHealth) -and (Test-OwnerToken $ownerToken)) { $plantHealthy = $true; break }
                if ($startedByBootstrap -and $plantProcess.HasExited) { break }
                Start-Sleep -Seconds 2
            }
            Protect-OwnerTokenInLogs @($stderrPath) $ownerToken
            if (-not $plantHealthy) {
                $tail = if (Test-Path $stderrPath) { (Get-Content -Tail 30 $stderrPath) -join "`n" } else { "" }
                throw "ICARUS plant did not become healthy with its owner token at http://127.0.0.1:8791/api/access. $tail"
            }
            if ($StopPlantAfterVerification -and $startedByBootstrap) {
                Invoke-Checked $EnginePython @("-m", "icarus_plant", "--root", $DataPath, "stop")
                $startedByBootstrap = $false
                for ($attempt = 0; $attempt -lt 20; $attempt++) {
                    if (-not (Test-PlantHealth)) { break }
                    Start-Sleep -Milliseconds 500
                }
                if (Test-PlantHealth) { throw "ICARUS plant stayed healthy after the verification stop request" }
                if ($plantProcess -and -not $plantProcess.HasExited) {
                    $null = $plantProcess.WaitForExit(10000)
                }
            }
        }
    } finally {
        if ($startedByBootstrap -and ($StopPlantAfterVerification -or -not $plantHealthy)) {
            try { Invoke-Checked $EnginePython @("-m", "icarus_plant", "--root", $DataPath, "stop") } catch { }
            if ($plantProcess -and -not $plantProcess.HasExited) {
                $null = $plantProcess.WaitForExit(10000)
            }
        }
        Protect-OwnerTokenInLogs @($stderrPath) $ownerToken
        Pop-Location
    }

    $EngineCommit = (& git -C $EnginePath rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $EngineCommit) { throw "Cannot identify the validated engine revision: $EnginePath" }
    Write-Host "Full ICARUS install and validation completed."
    Write-Host "Divine Providence: $Root"
    Write-Host "Trading engine:    $EnginePath"
    Write-Host "Engine revision:  $EngineCommit"
    Write-Host "Engine data:       $DataPath"
    Write-Host "Phone UI:          https://icarus-command-center-mobile.cloudyrook1.chatgpt.site"
    if ($NoStartPlant) {
        Write-Host "Plant: installed and initialized; not started (-NoStartPlant)."
    } else {
        Write-Host "Plant: healthy on loopback using $Feed NQ data."
        Write-Host "Owner token saved at: $ownerTokenPath"
        if ($StopPlantAfterVerification) { Write-Host "Plant: stopped after lifecycle verification." }
    }
    Write-Host "TradingView alerts, broker credentials, and paid market-data entitlements require their own configuration."
    Write-Host "Phone UI pairing additionally needs the local phone relay and a Cloudflare Quick Tunnel; see the runtime docs/PHONE_ACCESS.md."
} finally {
    Pop-Location
}
