param(
    [string]$Python = "python",
    [Parameter(Mandatory = $true)]
    [string]$Executable,
    [Parameter(Mandatory = $true)]
    [string]$ArtifactsDir,
    [int]$LocalPort = 8895,
    [int]$PublicPort = 8896
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$Executable = [System.IO.Path]::GetFullPath($Executable)
$ArtifactsDir = [System.IO.Path]::GetFullPath($ArtifactsDir)

if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "Frozen Studio executable was not found at $Executable"
}

New-Item -ItemType Directory -Force -Path $ArtifactsDir | Out-Null

function Wait-FrozenStudio {
    param(
        [System.Diagnostics.Process]$Process,
        [int]$Port,
        [int]$TimeoutSeconds = 90
    )

    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $Deadline) {
        if ($Process.HasExited) {
            return $false
        }
        try {
            $Response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -TimeoutSec 2
            if ($Response.StatusCode -eq 200 -and $Response.Content -match "gpbiometricspy Studio") {
                return $true
            }
        }
        catch {
            # Expected while the embedded server starts.
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Invoke-FrozenBrowserMode {
    param(
        [string]$Mode,
        [int]$Port,
        [string]$TestFile,
        [string]$UrlEnvironmentVariable,
        [switch]$PublicDemo
    )

    $StdoutLog = Join-Path $ArtifactsDir "$Mode-browser-stdout.log"
    $StderrLog = Join-Path $ArtifactsDir "$Mode-browser-stderr.log"
    $JunitPath = Join-Path $ArtifactsDir "$Mode-browser-pytest.xml"
    $Arguments = @("--host", "127.0.0.1", "--port", "$Port", "--no-browser")
    if ($PublicDemo) {
        $Arguments += "--public-demo"
    }

    $StartProcessArgs = @{
        FilePath = $Executable
        ArgumentList = $Arguments
        WorkingDirectory = $ArtifactsDir
        RedirectStandardOutput = $StdoutLog
        RedirectStandardError = $StderrLog
        PassThru = $true
    }

    Write-Host "Launching frozen Studio $Mode browser contract on port $Port..."
    $Process = Start-Process @StartProcessArgs
    $PreviousUrl = [Environment]::GetEnvironmentVariable($UrlEnvironmentVariable, "Process")
    try {
        if (-not (Wait-FrozenStudio -Process $Process -Port $Port)) {
            $ExitDetail = if ($Process.HasExited) { " Process exited with code $($Process.ExitCode)." } else { "" }
            throw "Frozen Studio $Mode mode did not become ready.$ExitDetail"
        }

        [Environment]::SetEnvironmentVariable(
            $UrlEnvironmentVariable,
            "http://127.0.0.1:$Port/",
            "Process"
        )
        Push-Location $RepoRoot
        try {
            & $Python -m pytest -q $TestFile --browser chromium --junitxml=$JunitPath
            if ($LASTEXITCODE -ne 0) {
                throw "Frozen Studio $Mode Chromium contract failed."
            }
        }
        finally {
            Pop-Location
        }
    }
    catch {
        if (Test-Path -LiteralPath $StdoutLog) {
            Write-Host "---- frozen Studio $Mode stdout ----"
            Get-Content -LiteralPath $StdoutLog
        }
        if (Test-Path -LiteralPath $StderrLog) {
            Write-Host "---- frozen Studio $Mode stderr ----"
            Get-Content -LiteralPath $StderrLog
        }
        throw
    }
    finally {
        [Environment]::SetEnvironmentVariable($UrlEnvironmentVariable, $PreviousUrl, "Process")
        if ($null -ne $Process -and -not $Process.HasExited) {
            Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
            try { $Process.WaitForExit(5000) | Out-Null } catch { }
        }
    }
}

Invoke-FrozenBrowserMode `
    -Mode "local" `
    -Port $LocalPort `
    -TestFile "studio/e2e/test_frozen_local_e2e.py" `
    -UrlEnvironmentVariable "GPBIOMETRICSPY_FROZEN_LOCAL_URL"

Invoke-FrozenBrowserMode `
    -Mode "public" `
    -Port $PublicPort `
    -TestFile "studio/e2e/test_frozen_public_e2e.py" `
    -UrlEnvironmentVariable "GPBIOMETRICSPY_FROZEN_PUBLIC_URL" `
    -PublicDemo

Write-Host "Frozen local and public Chromium contracts passed."
