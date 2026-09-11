param(
    [string]$Python = "python",
    [int]$Port = 8995,
    [string]$ArtifactsDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path ([System.IO.Path]::GetTempPath()) ("gpbiometricspy-windowed-" + [guid]::NewGuid().ToString("N"))
}
$ArtifactsDir = [System.IO.Path]::GetFullPath($ArtifactsDir)
$BuildRoot = Join-Path $ArtifactsDir "build"
$DistRoot = Join-Path $ArtifactsDir "dist"
$VenvRoot = Join-Path $ArtifactsDir "venv"
$VenvPython = Join-Path $VenvRoot "Scripts/python.exe"
$EvidenceDir = Join-Path $ArtifactsDir "evidence"
$IdentityDir = Join-Path $EvidenceDir "identity"
$IdentityJson = Join-Path $IdentityDir "windows-identity.json"
$IconPath = Join-Path $IdentityDir "gpbiometricspy-studio.ico"
$MetricsPath = Join-Path $EvidenceDir "windowed-metrics.json"
$SpecPath = Join-Path $RepoRoot "tools/pyinstaller/gpbiometricspy_studio_native_windowed.spec"
$RequirementsPath = Join-Path $RepoRoot "tools/pyinstaller/requirements.txt"
$IdentityGenerator = Join-Path $RepoRoot "tools/pyinstaller/generate_windows_identity.py"
$IdentityVerifier = Join-Path $RepoRoot ".github/scripts/assert_studio_windows_identity.ps1"

New-Item -ItemType Directory -Force -Path $ArtifactsDir, $EvidenceDir | Out-Null

function Get-PeSubsystem {
    param([Parameter(Mandatory = $true)][string]$Executable)

    $Stream = [System.IO.File]::Open($Executable, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    $Reader = [System.IO.BinaryReader]::new($Stream)
    try {
        $Reader.BaseStream.Seek(0x3C, [System.IO.SeekOrigin]::Begin) | Out-Null
        $PeOffset = $Reader.ReadInt32()
        if ($PeOffset -lt 0) { throw "Invalid PE header offset." }

        $Reader.BaseStream.Seek($PeOffset, [System.IO.SeekOrigin]::Begin) | Out-Null
        $Signature = $Reader.ReadUInt32()
        if ($Signature -ne 0x00004550) { throw "Invalid PE signature." }

        # PE signature (4) + COFF header (20) + Subsystem offset (68).
        $Reader.BaseStream.Seek($PeOffset + 92, [System.IO.SeekOrigin]::Begin) | Out-Null
        return [int]$Reader.ReadUInt16()
    }
    finally {
        $Reader.Dispose()
        $Stream.Dispose()
    }
}

Write-Host "Creating isolated windowed native Studio build environment..."
& $Python -m venv $VenvRoot
if ($LASTEXITCODE -ne 0) { throw "Failed to create windowed Studio build environment." }

& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip in windowed Studio build environment." }

& $VenvPython -m pip install -e ("{0}[studio-native]" -f $RepoRoot)
if ($LASTEXITCODE -ne 0) { throw "Failed to install gpbiometricspy native Studio dependencies." }

& $VenvPython -m pip install -r $RequirementsPath
if ($LASTEXITCODE -ne 0) { throw "Failed to install pinned PyInstaller build tools." }

Write-Host "Validating native and windowed bootstrap unit contracts..."
& $VenvPython -m pip install pytest
if ($LASTEXITCODE -ne 0) { throw "Failed to install pytest." }
& $VenvPython -m pytest -q `
    (Join-Path $RepoRoot "studio/tests/test_native.py") `
    (Join-Path $RepoRoot "studio/tests/test_native_frozen.py") `
    (Join-Path $RepoRoot "studio/tests/test_native_windowed.py")
if ($LASTEXITCODE -ne 0) { throw "Windowed native launcher unit contract failed." }

Write-Host "Generating Windows application identity from repository metadata..."
& $VenvPython $IdentityGenerator --repo-root $RepoRoot --output-dir $IdentityDir --target native
if ($LASTEXITCODE -ne 0) { throw "Failed to generate Windows application identity." }
$env:GPBIOMETRICSPY_WINDOWS_IDENTITY_DIR = $IdentityDir

$BuildStarted = Get-Date
Write-Host "Building console-free native WebView2 Studio bundle..."
Push-Location $RepoRoot
try {
    & $VenvPython -m PyInstaller --noconfirm --clean --distpath $DistRoot --workpath $BuildRoot $SpecPath
    if ($LASTEXITCODE -ne 0) { throw "Windowed native PyInstaller build failed." }
}
finally {
    Pop-Location
}
$BuildSeconds = ((Get-Date) - $BuildStarted).TotalSeconds

$BundleRoot = Join-Path $DistRoot "gpbiometricspy-studio-native"
$Executable = Join-Path $BundleRoot "gpbiometricspy-studio-native.exe"
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw "Windowed native Studio executable was not created at $Executable"
}

& $IdentityVerifier -Executable $Executable -IdentityJson $IdentityJson -IconPath $IconPath
if ($LASTEXITCODE -ne 0) { throw "Windowed native Studio Windows identity verification failed." }
$Identity = Get-Content -LiteralPath $IdentityJson -Raw | ConvertFrom-Json

$PeSubsystem = Get-PeSubsystem -Executable $Executable
if ($PeSubsystem -ne 2) {
    throw "Windowed native Studio PE subsystem must be IMAGE_SUBSYSTEM_WINDOWS_GUI (2); got $PeSubsystem."
}
Write-Host "PE subsystem verified: IMAGE_SUBSYSTEM_WINDOWS_GUI (2)."

$BundleFiles = @(Get-ChildItem -LiteralPath $BundleRoot -Recurse -File)
$BundleBytes = [int64](($BundleFiles | Measure-Object -Property Length -Sum).Sum)
$FileCount = $BundleFiles.Count
Write-Host ("Windowed native bundle: {0:N1} MiB across {1} files; build {2:N1} s." -f ($BundleBytes / 1MB), $FileCount, $BuildSeconds)

$OriginalPath = $env:PATH
$OriginalPythonHome = $env:PYTHONHOME
$OriginalPythonPath = $env:PYTHONPATH
$OriginalWindowedLog = $env:GPBIOMETRICSPY_WINDOWED_LOG_PATH
$StartupSamples = @{}
$Failure = $null

function Invoke-WindowedBoundarySmoke {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][int]$BoundaryPort,
        [switch]$PublicDemo
    )

    $WindowedLog = Join-Path $EvidenceDir ("windowed-{0}.log" -f $Name)
    Remove-Item -LiteralPath $WindowedLog -Force -ErrorAction SilentlyContinue
    $Arguments = @("--host", "127.0.0.1", "--port", "$BoundaryPort", "--automation-close-seconds", "30")
    if ($PublicDemo) { $Arguments += "--public-demo" }

    $env:GPBIOMETRICSPY_WINDOWED_LOG_PATH = $WindowedLog
    Write-Host "Launching console-free native Studio ($Name) with external Python removed from PATH..."
    $Started = Get-Date
    $Process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $ArtifactsDir -PassThru

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
        if (Test-Path -LiteralPath $WindowedLog) { Get-Content -LiteralPath $WindowedLog }
        throw "Console-free native Studio ($Name) did not become reachable."
    }

    $Startup = ((Get-Date) - $Started).TotalSeconds
    $StartupSamples[$Name] = [Math]::Round($Startup, 3)

    if (-not $Process.WaitForExit(60000)) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
        throw "Console-free native Studio ($Name) did not close after DOM-readiness automation."
    }
    if ($Process.ExitCode -ne 0) {
        if (Test-Path -LiteralPath $WindowedLog) { Get-Content -LiteralPath $WindowedLog }
        throw "Console-free native Studio ($Name) exited with code $($Process.ExitCode)."
    }
    if (-not (Test-Path -LiteralPath $WindowedLog -PathType Leaf)) {
        throw "Console-free native Studio ($Name) did not create its diagnostic log."
    }

    $Output = Get-Content -LiteralPath $WindowedLog -Raw
    if ($Output -notmatch "Windowed release bootstrap: console_attached=false") {
        throw "Console-free native Studio ($Name) reported an attached console or missed the windowed bootstrap."
    }
    if ($Output -notmatch "Native renderer requested: edgechromium") {
        throw "Console-free native Studio ($Name) did not request the WebView2/edgechromium renderer."
    }
    if ($Output -notmatch "Native DOM loaded\.") {
        throw "Console-free native Studio ($Name) did not reach the pywebview DOM loaded event."
    }
    if ($Output -notmatch "window closed cleanly") {
        throw "Console-free native Studio ($Name) did not report a clean native-window close."
    }

    Write-Host ("Console-free native Studio ({0}) reached HTTP 200 in {1:N2} s, loaded its DOM, had no attached console, and closed cleanly." -f $Name, $Startup)
}

try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

    if (Get-Command python -CommandType Application -ErrorAction SilentlyContinue) {
        throw "PATH isolation failed: an external python executable is still discoverable."
    }

    Invoke-WindowedBoundarySmoke -Name "local" -BoundaryPort $Port
    Invoke-WindowedBoundarySmoke -Name "public" -BoundaryPort ($Port + 1) -PublicDemo

    $Metrics = [ordered]@{
        schema = "gpbiometricspy-studio-native-windowed-smoke"
        schema_version = 1
        release_artifact = $false
        bundle_mode = "onedir-native-windowed-webview2"
        renderer = "edgechromium"
        console = $false
        pe_subsystem = $PeSubsystem
        pe_subsystem_name = "IMAGE_SUBSYSTEM_WINDOWS_GUI"
        console_attached = $false
        external_python_required = $false
        dom_loaded_required = $true
        windows_identity_verified = $true
        engineering_console_build_preserved = $true
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
    if ($null -eq $OriginalWindowedLog) { Remove-Item Env:GPBIOMETRICSPY_WINDOWED_LOG_PATH -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_WINDOWED_LOG_PATH = $OriginalWindowedLog }
}

# Diagnostics-only proof: do not retain the redistributable bundle in CI evidence.
Remove-Item -LiteralPath $DistRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $BuildRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $VenvRoot -Recurse -Force -ErrorAction SilentlyContinue

if (Get-ChildItem -LiteralPath $EvidenceDir -Recurse -File -Include "*.exe", "*.pfx", "*.p12" -ErrorAction SilentlyContinue) {
    throw "Windowed-release evidence must not retain executable or signing-key material."
}

if ($null -ne $Failure) { throw $Failure }
Write-Host "PyInstaller console-free native WebView2 Studio proof passed with GUI PE subsystem, no attached console, verified identity, and local/public DOM readiness."
