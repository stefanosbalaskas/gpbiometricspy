param(
    [string]$Python = "python",
    [int]$Port = 8935,
    [string]$ArtifactsDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path ([System.IO.Path]::GetTempPath()) ("gpbiometricspy-nuitka-" + [guid]::NewGuid().ToString("N"))
}
$ArtifactsDir = [System.IO.Path]::GetFullPath($ArtifactsDir)
$DistRoot = Join-Path $ArtifactsDir "dist"
$VenvRoot = Join-Path $ArtifactsDir "venv"
$VenvPython = Join-Path $VenvRoot "Scripts/python.exe"
$StdoutLog = Join-Path $ArtifactsDir "nuitka-stdout.log"
$StderrLog = Join-Path $ArtifactsDir "nuitka-stderr.log"
$MetricsPath = Join-Path $ArtifactsDir "nuitka-metrics.json"
$ReportPath = Join-Path $ArtifactsDir "nuitka-compilation-report.xml"
$RequirementsPath = Join-Path $RepoRoot "tools/nuitka/requirements.txt"
$EntryPath = Join-Path $RepoRoot "studio/frozen.py"

New-Item -ItemType Directory -Force -Path $ArtifactsDir | Out-Null
New-Item -ItemType Directory -Force -Path $DistRoot | Out-Null

Write-Host "Creating isolated Nuitka build environment..."
& $Python -m venv $VenvRoot
if ($LASTEXITCODE -ne 0) { throw "Failed to create Nuitka build environment." }

& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip in Nuitka build environment." }

& $VenvPython -m pip install -e ("{0}[studio]" -f $RepoRoot)
if ($LASTEXITCODE -ne 0) { throw "Failed to install gpbiometricspy Studio into Nuitka build environment." }

& $VenvPython -m pip install -r $RequirementsPath
if ($LASTEXITCODE -ne 0) { throw "Failed to install pinned Nuitka build tools." }

$env:NUITKA_UPDATE_CHECK = "never"
$BuildStarted = Get-Date
Write-Host "Building diagnosable Nuitka standalone Studio bundle with MSVC..."

$NuitkaArgs = @(
    "-m", "nuitka",
    "--mode=standalone",
    "--assume-yes-for-downloads",
    "--msvc=latest",
    "--windows-console-mode=force",
    "--output-dir=$DistRoot",
    "--output-filename=gpbiometricspy-studio.exe",
    "--report=$ReportPath",
    "--include-module=studio.app",
    "--include-module=studio.public_demo",
    "--include-package=shiny",
    "--include-package=uvicorn",
    "--include-package-data=studio",
    "--include-package-data=gpbiometricspy",
    "--include-package-data=shiny",
    "--include-package-data=htmltools",
    "--include-package-data=shinychat",
    "--nofollow-import-to=pytest",
    "--nofollow-import-to=playwright",
    "--nofollow-import-to=ruff",
    "--nofollow-import-to=twine",
    $EntryPath
)

Push-Location $RepoRoot
try {
    & $VenvPython @NuitkaArgs
    if ($LASTEXITCODE -ne 0) { throw "Nuitka standalone build failed." }
}
finally {
    Pop-Location
}
$BuildSeconds = ((Get-Date) - $BuildStarted).TotalSeconds

$ExecutableItem = Get-ChildItem -LiteralPath $DistRoot -Recurse -File -Filter "gpbiometricspy-studio.exe" | Select-Object -First 1
if ($null -eq $ExecutableItem) {
    throw "Nuitka standalone executable gpbiometricspy-studio.exe was not created below $DistRoot"
}
$Executable = $ExecutableItem.FullName
$BundleRoot = $ExecutableItem.Directory.FullName
$BundleFiles = @(Get-ChildItem -LiteralPath $BundleRoot -Recurse -File)
$BundleBytes = [int64](($BundleFiles | Measure-Object -Property Length -Sum).Sum)
$FileCount = $BundleFiles.Count
Write-Host ("Nuitka bundle: {0:N1} MiB across {1} files; build {2:N1} s." -f ($BundleBytes / 1MB), $FileCount, $BuildSeconds)

$OriginalPath = $env:PATH
$OriginalPythonHome = $env:PYTHONHOME
$OriginalPythonPath = $env:PYTHONPATH
$Process = $null
$Started = Get-Date
$Ready = $false
$Failure = $null

try {
    # Prove the compiled launcher does not depend on an externally discoverable Python.
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

    if (Get-Command python -CommandType Application -ErrorAction SilentlyContinue) {
        throw "PATH isolation failed: an external python executable is still discoverable."
    }

    Write-Host "Launching Nuitka Studio with external Python removed from PATH..."
    $StartProcessArgs = @{
        FilePath = $Executable
        ArgumentList = @("--host", "127.0.0.1", "--port", "$Port", "--no-browser")
        WorkingDirectory = $ArtifactsDir
        RedirectStandardOutput = $StdoutLog
        RedirectStandardError = $StderrLog
        PassThru = $true
    }
    $Process = Start-Process @StartProcessArgs

    $Deadline = (Get-Date).AddSeconds(120)
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
        throw "Nuitka Studio did not become reachable on loopback within 120 seconds.$ExitDetail"
    }

    $StartupSeconds = ((Get-Date) - $Started).TotalSeconds
    Write-Host ("Nuitka Studio became reachable in {0:N2} seconds without external Python." -f $StartupSeconds)

    $Metrics = [ordered]@{
        schema = "gpbiometricspy-studio-nuitka-smoke"
        schema_version = 1
        bundle_mode = "standalone"
        compiler = "msvc-latest"
        console = $true
        external_python_required = $false
        host = "127.0.0.1"
        port = $Port
        file_count = $FileCount
        bundle_bytes = $BundleBytes
        build_seconds = [Math]::Round($BuildSeconds, 3)
        startup_seconds = [Math]::Round($StartupSeconds, 3)
        python_version = ((& $VenvPython --version 2>&1) | Out-String).Trim()
        nuitka_version = ((& $VenvPython -m nuitka --version 2>&1 | Select-Object -First 1) | Out-String).Trim()
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
        Write-Host "---- Nuitka Studio stdout ----"
        Get-Content -LiteralPath $StdoutLog
    }
    if (Test-Path -LiteralPath $StderrLog) {
        Write-Host "---- Nuitka Studio stderr ----"
        Get-Content -LiteralPath $StderrLog
    }
    throw $Failure
}

if (-not $Ready) {
    throw "Nuitka standalone Studio smoke did not complete successfully."
}

Write-Host "Nuitka standalone Studio smoke passed."
