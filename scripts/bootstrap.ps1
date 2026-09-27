# Divine Providence bootstrap (Windows PowerShell 5.1+).
#   .\scripts\bootstrap.ps1                 # venv + install + hub tests
#   .\scripts\bootstrap.ps1 -Validate       # + full-build validation (all 12 suites + connections)
#   .\scripts\bootstrap.ps1 -RegisterMcp    # + register the icarus-engine MCP server with Claude Code (user scope)
#   .\scripts\bootstrap.ps1 -Python "C:\Program Files\Python311\python.exe"   # explicit interpreter
param([switch]$Validate, [switch]$RegisterMcp, [string]$Python = "")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Find-Python {
    # Most subsystems declare requires-python >=3.11; prefer the newest 3.11+ the py launcher knows.
    $ErrorActionPreference = "Continue"   # PS 5.1 turns native stderr into terminating errors under Stop
    $listing = @()
    try { $listing = @(& py -0 2>$null) } catch { $listing = @() }
    $tags = @($listing | ForEach-Object { if ($_ -match '-V:(\S+)') { $Matches[1] } })
    foreach ($want in @("3.13", "3.12", "3.11")) {
        $tag = $tags | Where-Object { $_ -match [regex]::Escape($want) } | Select-Object -First 1
        if ($tag) { return @("py", "-V:$tag") }
    }
    Write-Warning "no Python 3.11+ found via the py launcher; falling back to 'py -3' (subsystems declare >=3.11)"
    return @("py", "-3")
}

Push-Location $Root
try {
    if (-not (Test-Path ".venv")) {
        $cmd = if ($Python) { @($Python) } else { Find-Python }
        $exe = $cmd[0]
        $exeArgs = @($cmd | Select-Object -Skip 1)
        Write-Host "creating .venv with $($cmd -join ' ')"
        & $exe @exeArgs -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
    }
    $Py = Join-Path $Root ".venv\Scripts\python.exe"
    & $Py -m pip install --quiet --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
    & $Py -m pip install --quiet -e .
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

    & $Py -m pytest tests
    if ($LASTEXITCODE -ne 0) { throw "hub tests failed" }

    if ($Validate) {
        & $Py -m divine_providence.validate
        if ($LASTEXITCODE -ne 0) { throw "full-build validation failed; see provenance\validation_report.json" }
    }

    if ($RegisterMcp) {
        $token = $env:ICARUS_ENGINE_TOKEN
        $envArgs = @("-e", "PYTHONIOENCODING=utf-8")
        # Note: 'claude mcp add -e' puts the value on a command line (briefly visible in the process list)
        # and stores it in the user-scope Claude config, never in this repository.
        if ($token) { $envArgs += @("-e", "ICARUS_ENGINE_TOKEN=$token") }
        # Not registered yet is fine; PS 5.1 would turn its stderr into a terminating error under "Stop".
        $ErrorActionPreference = "Continue"
        claude mcp remove icarus-engine --scope user *> $null
        $ErrorActionPreference = "Stop"
        # '--' must be quoted: PowerShell consumes a bare -- before it reaches the claude.ps1 shim.
        claude mcp add icarus-engine --scope user @envArgs '--' $Py -m divine_providence.mcp_server
        if ($LASTEXITCODE -ne 0) { throw "claude mcp add failed" }
        # 'claude mcp list' health-checks without printing the server's environment (unlike 'mcp get').
        claude mcp list | Select-String -SimpleMatch "icarus-engine"
    }
    Write-Host "done."
}
finally {
    Pop-Location
}
