param(
    [string]$Python = "python",
    [int]$Port = 8875,
    [string]$ArtifactsDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path ([System.IO.Path]::GetTempPath()) ("gpbiometricspy-pyinstaller-" + [guid]::NewGuid().ToString("N"))
}
$ArtifactsDir = [System.IO.Path]::GetFullPath($ArtifactsDir)
$BuildRoot = Join-Path $ArtifactsDir "build"
$DistRoot = Join-Path $ArtifactsDir "dist"
$VenvRoot = Join-Path $ArtifactsDir "venv"
$VenvPython = Join-Path $VenvRoot "Scripts/python.exe"
$StdoutLog = Join-Path $ArtifactsDir "frozen-stdout.log"
$StderrLog = Join-Path $ArtifactsDir "frozen-stderr.log"
$MetricsPath = Join-Path $ArtifactsDir "metrics.json"
$SpecPath = Join-Path $RepoRoot "tools/pyinstaller/gpbiometricspy_studio.spec"
$RequirementsPath = Join-Path $RepoRoot "tools/pyinstaller/requirements.txt"

New-Item -ItemType Directory -Force -Path $ArtifactsDir | Out-Null

Write-Host "Creating isolated PyInstaller build environment..."
& $Python -m venv $VenvRoot
if ($LASTEXITCODE -ne 0) { throw "Failed to create PyInstaller build environment." }

& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip in PyInstaller build environment." }

& $VenvPython -m pip install -e ("{0}[studio]" -f $RepoRoot)
if ($LASTEXITCODE -ne 0) { throw "Failed to install gpbiometricspy Studio into PyInstaller build environment." }

& $VenvPython -m pip install -r $RequirementsPath
if ($LASTEXITCODE -ne 0) { throw "Failed to install pinned PyInstaller build tools." }

Write-Host "Building diagnosable onedir Studio bundle..."
Push-Location $RepoRoot
try {
    & $VenvPython -m PyInstaller --noconfirm --clean --distpath $DistRoot --workpath $BuildRoot $SpecPath
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
}
finally {
    Pop-Location
}

$BundleRoot = Join-Path $DistRoot "gpbiometricspy-studio"
$Executable = Join-Path $BundleRoot "gpbiometricspy-studio.exe"
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "Frozen Studio executable was not created at $Executable"
}

$BundleFiles = @(Get-ChildItem -LiteralPath $BundleRoot -Recurse -File)
$BundleBytes = [int64](($BundleFiles | Measure-Object -Property Length -Sum).Sum)
$FileCount = $BundleFiles.Count
Write-Host ("Frozen bundle: {0:N1} MiB across {1} files." -f ($BundleBytes / 1MB), $FileCount)

$OriginalPath = $env:PATH
$OriginalPythonHome = $env:PYTHONHOME
$OriginalPythonPath = $env:PYTHONPATH
$Process = $null
$Started = Get-Date
$Ready = $false
$Failure = $null

try {
    # Prove the frozen launcher does not depend on an externally discoverable Python.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

    if (Get-Command python -CommandType Application -ErrorAction SilentlyContinue) {
        throw "PATH isolation failed: an external python executable is still discoverable."
    }

    Write-Host "Launching frozen Studio with external Python removed from PATH..."
    $StartProcessArgs = @{
        FilePath = $Executable
        ArgumentList = @("--host", "127.0.0.1", "--port", "$Port", "--no-browser")
        WorkingDirectory = $ArtifactsDir
        RedirectStandardOutput = $StdoutLog
        RedirectStandardError = $StderrLog
        PassThru = $true
    }
    $Process = Start-Process @StartProcessArgs

    $Deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $Deadline) {
        if ($Process.HasExited) {
            break
        }
        try {
            $Response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -TimeoutSec 2
            if ($Response.StatusCode -eq 200 -and $Response.Content -match "gpbiometricspy Studio") {
                $Ready = $true
                break
            }
        }
        catch {
            # Startup polling is expected to fail until the embedded server binds.
        }
        Start-Sleep -Milliseconds 500
    }

    if (-not $Ready) {
        $ExitDetail = if ($Process.HasExited) { " Process exited with code $($Process.ExitCode)." } else { "" }
        throw "Frozen Studio did not become reachable on loopback within 90 seconds.$ExitDetail"
    }

    $StartupSeconds = ((Get-Date) - $Started).TotalSeconds
    Write-Host ("Frozen Studio became reachable in {0:N2} seconds without external Python." -f $StartupSeconds)

    $Metrics = [ordered]@{
        schema = "gpbiometricspy-studio-pyinstaller-smoke"
        schema_version = 1
        bundle_mode = "onedir"
        console = $true
        external_python_required = $false
        host = "127.0.0.1"
        port = $Port
        file_count = $FileCount
        bundle_bytes = $BundleBytes
        startup_seconds = [Math]::Round($StartupSeconds, 3)
        python_version = ((& $VenvPython --version 2>&1) | Out-String).Trim()
        pyinstaller_version = ((& $VenvPython -m PyInstaller --version 2>&1) | Out-String).Trim()
    }
    $Metrics | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $MetricsPath -Encoding UTF8
}
catch {
    $Failure = $_
}
finally {
    if ($null -ne $Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
        try { $Process.WaitForExit(5000) | Out-Null } catch { }
    }

    $env:PATH = $OriginalPath
    if ($null -eq $OriginalPythonHome) { Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue } else { $env:PYTHONHOME = $OriginalPythonHome }
    if ($null -eq $OriginalPythonPath) { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue } else { $env:PYTHONPATH = $OriginalPythonPath }
}

if ($null -ne $Failure) {
    if (Test-Path -LiteralPath $StdoutLog) {
        Write-Host "---- frozen Studio stdout ----"
        Get-Content -LiteralPath $StdoutLog
    }
    if (Test-Path -LiteralPath $StderrLog) {
        Write-Host "---- frozen Studio stderr ----"
        Get-Content -LiteralPath $StderrLog
    }
    throw $Failure
}

if (-not $Ready) {
    throw "Frozen Studio smoke did not complete successfully."
}

Write-Host "PyInstaller standalone Studio smoke passed."
