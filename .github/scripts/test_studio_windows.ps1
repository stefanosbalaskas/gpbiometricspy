param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$tempRoot = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [System.IO.Path]::GetTempPath() }
$token = [Guid]::NewGuid().ToString("N")
$venv = Join-Path $tempRoot "gpbiometricspy-studio-windows-$token"
$outsideRepo = Join-Path $tempRoot "gpbiometricspy-studio-cwd-$token"
$stdoutLog = Join-Path $tempRoot "gpbiometricspy-studio-windows-$token.out.log"
$stderrLog = Join-Path $tempRoot "gpbiometricspy-studio-windows-$token.err.log"

function Get-FreeLoopbackPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    try {
        return [int]$listener.LocalEndpoint.Port
    }
    finally {
        $listener.Stop()
    }
}

function Stop-ProcessTree {
    param([System.Diagnostics.Process]$Process)

    if ($null -eq $Process -or $Process.HasExited) {
        return
    }
    & taskkill.exe /PID $($Process.Id) /T /F 2>$null | Out-Null
}

function Wait-StudioReady {
    param(
        [System.Diagnostics.Process]$Process,
        [int]$Port,
        [string]$Label
    )

    $url = "http://127.0.0.1:$Port/"
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ($Process.HasExited) {
            $stdout = if (Test-Path $stdoutLog) { Get-Content $stdoutLog -Raw } else { "" }
            $stderr = if (Test-Path $stderrLog) { Get-Content $stderrLog -Raw } else { "" }
            throw "$Label exited before becoming ready.`nSTDOUT:`n$stdout`nSTDERR:`n$stderr"
        }

        $response = $null
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
        }
        catch {
            Start-Sleep -Milliseconds 500
            continue
        }

        if ($response.StatusCode -eq 200) {
            if ($response.Content -notmatch "gpbiometricspy Studio") {
                throw "$Label returned HTTP 200 but did not expose the Studio application shell."
            }
            return
        }
        Start-Sleep -Milliseconds 500
    }

    $stdout = if (Test-Path $stdoutLog) { Get-Content $stdoutLog -Raw } else { "" }
    $stderr = if (Test-Path $stderrLog) { Get-Content $stderrLog -Raw } else { "" }
    throw "$Label did not become ready on $url.`nSTDOUT:`n$stdout`nSTDERR:`n$stderr"
}

function Test-StudioLaunch {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$Label
    )

    $port = Get-FreeLoopbackPort
    $launchArgs = @($ArgumentList + @("--host", "127.0.0.1", "--port", "$port"))
    Remove-Item $stdoutLog, $stderrLog -Force -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $FilePath -ArgumentList $launchArgs -WorkingDirectory $outsideRepo -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
    try {
        Wait-StudioReady -Process $process -Port $port -Label $Label
        Write-Host "PASS: $Label launched on loopback port $port"
    }
    finally {
        Stop-ProcessTree -Process $process
    }
}

try {
    New-Item -ItemType Directory -Path $outsideRepo -Force | Out-Null

    & $Python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Windows validation virtual environment." }

    $venvPython = Join-Path $venv "Scripts\python.exe"
    $studioLauncher = Join-Path $venv "Scripts\gpbiometricspy-studio.exe"
    $doctorLauncher = Join-Path $venv "Scripts\gpbiometricspy-studio-doctor.exe"

    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip in the Windows validation environment." }

    Push-Location $repoRoot
    try {
        & $venvPython -m pip install ".[studio]"
        if ($LASTEXITCODE -ne 0) { throw "Failed to install gpbiometricspy Studio into the Windows validation environment." }
    }
    finally {
        Pop-Location
    }

    if (-not (Test-Path $studioLauncher)) {
        throw "Installed gpbiometricspy-studio.exe launcher is missing."
    }
    if (-not (Test-Path $doctorLauncher)) {
        throw "Installed gpbiometricspy-studio-doctor.exe launcher is missing."
    }

    Push-Location $outsideRepo
    try {
        $studioPath = (& $venvPython -c "from pathlib import Path; import studio; print(Path(studio.__file__).resolve())" | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) { throw "Could not import installed Studio outside the repository." }
        if (-not $studioPath.StartsWith($venv, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Studio resolved outside the isolated Windows environment: $studioPath"
        }

        $doctorJson = (& $venvPython -m studio.doctor --json | Out-String)
        if ($LASTEXITCODE -ne 0) { throw "PATH-independent Studio Doctor invocation failed." }
        $doctor = $doctorJson | ConvertFrom-Json
        if (-not $doctor.ok) { throw "Studio Doctor reported ACTION REQUIRED in the clean Windows environment." }
        if ($doctor.platform -notmatch "Windows") { throw "Studio Doctor did not report a Windows platform." }

        $launcherDoctorJson = (& $doctorLauncher --json | Out-String)
        if ($LASTEXITCODE -ne 0) { throw "Installed Studio Doctor launcher failed." }
        $launcherDoctor = $launcherDoctorJson | ConvertFrom-Json
        if (-not $launcherDoctor.ok) { throw "Installed Studio Doctor launcher reported ACTION REQUIRED." }
    }
    finally {
        Pop-Location
    }

    Test-StudioLaunch -FilePath $studioLauncher -ArgumentList @() -Label "installed gpbiometricspy-studio.exe"
    Test-StudioLaunch -FilePath $venvPython -ArgumentList @("-m", "studio.cli") -Label "PATH-independent python -m studio.cli"

    Write-Host "Windows Studio clean-install smoke passed."
}
finally {
    Remove-Item $outsideRepo -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $venv -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $stdoutLog, $stderrLog -Force -ErrorAction SilentlyContinue
}
