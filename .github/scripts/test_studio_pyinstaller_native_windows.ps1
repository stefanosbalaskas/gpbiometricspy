param(
    [string]$Python = "python",
    [int]$Port = 8955,
    [string]$ArtifactsDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path ([System.IO.Path]::GetTempPath()) ("gpbiometricspy-native-" + [guid]::NewGuid().ToString("N"))
}
$ArtifactsDir = [System.IO.Path]::GetFullPath($ArtifactsDir)
$BuildRoot = Join-Path $ArtifactsDir "build"
$DistRoot = Join-Path $ArtifactsDir "dist"
$VenvRoot = Join-Path $ArtifactsDir "venv"
$VenvPython = Join-Path $VenvRoot "Scripts/python.exe"
$IdentityDir = Join-Path $ArtifactsDir "identity"
$IdentityJson = Join-Path $IdentityDir "windows-identity.json"
$IconPath = Join-Path $IdentityDir "gpbiometricspy-studio.ico"
$MetricsPath = Join-Path $ArtifactsDir "native-metrics.json"
$SpecPath = Join-Path $RepoRoot "tools/pyinstaller/gpbiometricspy_studio_native.spec"
$RequirementsPath = Join-Path $RepoRoot "tools/pyinstaller/requirements.txt"
$IdentityGenerator = Join-Path $RepoRoot "tools/pyinstaller/generate_windows_identity.py"
$IdentityVerifier = Join-Path $RepoRoot ".github/scripts/assert_studio_windows_identity.ps1"

New-Item -ItemType Directory -Force -Path $ArtifactsDir | Out-Null

Write-Host "Creating isolated native Studio build environment..."
& $Python -m venv $VenvRoot
if ($LASTEXITCODE -ne 0) { throw "Failed to create native Studio build environment." }

& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip in native Studio build environment." }

& $VenvPython -m pip install -e ("{0}[studio-native]" -f $RepoRoot)
if ($LASTEXITCODE -ne 0) { throw "Failed to install gpbiometricspy native Studio dependencies." }

& $VenvPython -m pip install -r $RequirementsPath
if ($LASTEXITCODE -ne 0) { throw "Failed to install pinned PyInstaller build tools." }

Write-Host "Validating native launcher and frozen-adapter unit contracts..."
& $VenvPython -m pip install pytest
if ($LASTEXITCODE -ne 0) { throw "Failed to install pytest." }
& $VenvPython -m pytest -q `
    (Join-Path $RepoRoot "studio/tests/test_native.py") `
    (Join-Path $RepoRoot "studio/tests/test_native_frozen.py")
if ($LASTEXITCODE -ne 0) { throw "Native launcher unit contract failed." }

Write-Host "Generating Windows application identity from repository metadata..."
& $VenvPython $IdentityGenerator --repo-root $RepoRoot --output-dir $IdentityDir --target native
if ($LASTEXITCODE -ne 0) { throw "Failed to generate Windows application identity." }
$env:GPBIOMETRICSPY_WINDOWS_IDENTITY_DIR = $IdentityDir

$BuildStarted = Get-Date
Write-Host "Building diagnosable native WebView2 Studio bundle..."
Push-Location $RepoRoot
try {
    & $VenvPython -m PyInstaller --noconfirm --clean --distpath $DistRoot --workpath $BuildRoot $SpecPath
    if ($LASTEXITCODE -ne 0) { throw "Native PyInstaller build failed." }
}
finally {
    Pop-Location
}
$BuildSeconds = ((Get-Date) - $BuildStarted).TotalSeconds

$BundleRoot = Join-Path $DistRoot "gpbiometricspy-studio-native"
$Executable = Join-Path $BundleRoot "gpbiometricspy-studio-native.exe"
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "Frozen native Studio executable was not created at $Executable"
}

& $IdentityVerifier -Executable $Executable -IdentityJson $IdentityJson -IconPath $IconPath
if ($LASTEXITCODE -ne 0) { throw "Native Studio Windows identity verification failed." }
$Identity = Get-Content -LiteralPath $IdentityJson -Raw | ConvertFrom-Json

$BundleFiles = @(Get-ChildItem -LiteralPath $BundleRoot -Recurse -File)
$BundleBytes = [int64](($BundleFiles | Measure-Object -Property Length -Sum).Sum)
$FileCount = $BundleFiles.Count
Write-Host ("Native bundle: {0:N1} MiB across {1} files; build {2:N1} s." -f ($BundleBytes / 1MB), $FileCount, $BuildSeconds)

$OriginalPath = $env:PATH
$OriginalPythonHome = $env:PYTHONHOME
$OriginalPythonPath = $env:PYTHONPATH
$StartupSamples = @{}
$Failure = $null

function Invoke-NativeBoundarySmoke {
    param(
        [string]$Name,
        [int]$BoundaryPort,
        [switch]$PublicDemo
    )

    $StdoutLog = Join-Path $ArtifactsDir ("native-{0}-stdout.log" -f $Name)
    $StderrLog = Join-Path $ArtifactsDir ("native-{0}-stderr.log" -f $Name)
    $Arguments = @("--host", "127.0.0.1", "--port", "$BoundaryPort", "--automation-close-seconds", "30")
    if ($PublicDemo) { $Arguments += "--public-demo" }

    Write-Host "Launching frozen native Studio ($Name) with external Python removed from PATH..."
    $Started = Get-Date
    $Process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $ArtifactsDir `
        -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog -PassThru

    $Ready = $false
    $Deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $Deadline) {
        if ($Process.HasExited) { break }
        try {
            $Response = Invoke-WebRequest -Uri "http://127.0.0.1:$BoundaryPort/" -TimeoutSec 2
            if ($Response.StatusCode -eq 200 -and $Response.Content -match "gpbiometricspy Studio") {
                $Ready = $true
                break
            }
        }
        catch { }
        Start-Sleep -Milliseconds 400
    }

    if (-not $Ready) {
        if (-not $Process.HasExited) { Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue }
        Write-Host "---- native $Name stdout ----"
        if (Test-Path $StdoutLog) { Get-Content $StdoutLog }
        Write-Host "---- native $Name stderr ----"
        if (Test-Path $StderrLog) { Get-Content $StderrLog }
        throw "Frozen native Studio ($Name) did not become reachable before the window process exited or timed out."
    }

    $Startup = ((Get-Date) - $Started).TotalSeconds
    $StartupSamples[$Name] = [Math]::Round($Startup, 3)

    if (-not $Process.WaitForExit(60000)) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
        throw "Frozen native Studio ($Name) did not close after its DOM-readiness automation window."
    }
    if ($Process.ExitCode -ne 0) {
        Write-Host "---- native $Name stdout ----"
        if (Test-Path $StdoutLog) { Get-Content $StdoutLog }
        Write-Host "---- native $Name stderr ----"
        if (Test-Path $StderrLog) { Get-Content $StderrLog }
        throw "Frozen native Studio ($Name) exited with code $($Process.ExitCode)."
    }

    $Output = if (Test-Path $StdoutLog) { Get-Content $StdoutLog -Raw } else { "" }
    if ($Output -notmatch "Native renderer requested: edgechromium") {
        throw "Frozen native Studio ($Name) did not request the WebView2/edgechromium renderer."
    }
    if ($Output -notmatch "Native DOM loaded\.") {
        throw "Frozen native Studio ($Name) did not reach the pywebview DOM loaded event."
    }
    if ($Output -notmatch "window closed cleanly") {
        throw "Frozen native Studio ($Name) did not report a clean native-window close."
    }

    Write-Host ("Frozen native Studio ({0}) reached HTTP 200 in {1:N2} s, loaded its DOM, and closed cleanly." -f $Name, $Startup)
}

try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

    if (Get-Command python -CommandType Application -ErrorAction SilentlyContinue) {
        throw "PATH isolation failed: an external python executable is still discoverable."
    }

    Invoke-NativeBoundarySmoke -Name "local" -BoundaryPort $Port
    Invoke-NativeBoundarySmoke -Name "public" -BoundaryPort ($Port + 1) -PublicDemo

    $Metrics = [ordered]@{
        schema = "gpbiometricspy-studio-native-pyinstaller-smoke"
        schema_version = 3
        bundle_mode = "onedir-native-webview2"
        renderer = "edgechromium"
        console = $true
        external_python_required = $false
        dom_loaded_required = $true
        windows_identity_verified = $true
        product_name = $Identity.product_name
        product_version = $Identity.product_version
        file_version = $Identity.file_version
        local_http_startup_seconds = $StartupSamples["local"]
        public_http_startup_seconds = $StartupSamples["public"]
        file_count = $FileCount
        bundle_bytes = $BundleBytes
        build_seconds = [Math]::Round($BuildSeconds, 3)
        python_version = ((& $VenvPython --version 2>&1) | Out-String).Trim()
        pyinstaller_version = ((& $VenvPython -m PyInstaller --version 2>&1) | Out-String).Trim()
        pywebview_version = ((& $VenvPython -c "import importlib.metadata as m; print(m.version('pywebview'))" 2>&1) | Out-String).Trim()
    }
    $Metrics | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $MetricsPath -Encoding UTF8
}
catch {
    $Failure = $_
}
finally {
    $env:PATH = $OriginalPath
    if ($null -eq $OriginalPythonHome) { Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue } else { $env:PYTHONHOME = $OriginalPythonHome }
    if ($null -eq $OriginalPythonPath) { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue } else { $env:PYTHONPATH = $OriginalPythonPath }
}

if ($null -ne $Failure) { throw $Failure }
Write-Host "PyInstaller native WebView2 Studio smoke passed with verified Windows identity."
