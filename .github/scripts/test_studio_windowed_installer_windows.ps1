param(
    [string]$Python = "python",
    [int]$Port = 9015,
    [string]$ArtifactsDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path ([System.IO.Path]::GetTempPath()) ("gpbiometricspy-windowed-installer-" + [guid]::NewGuid().ToString("N"))
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
$InstallerOutput = Join-Path $ArtifactsDir "installer-output"
$InstallRoot = Join-Path $ArtifactsDir "installed\gpbiometricspy Studio"
$MissingRuntimeInstallRoot = Join-Path $ArtifactsDir "missing-runtime-install"
$MetricsPath = Join-Path $EvidenceDir "windowed-installer-metrics.json"
$CompileLog = Join-Path $EvidenceDir "iscc.log"
$InstallLog = Join-Path $EvidenceDir "install.log"
$MissingRuntimeInstallLog = Join-Path $EvidenceDir "install-missing-webview2.log"
$UninstallLog = Join-Path $EvidenceDir "uninstall.log"
$SpecPath = Join-Path $RepoRoot "tools/pyinstaller/gpbiometricspy_studio_native_windowed.spec"
$RequirementsPath = Join-Path $RepoRoot "tools/pyinstaller/requirements.txt"
$IdentityGenerator = Join-Path $RepoRoot "tools/pyinstaller/generate_windows_identity.py"
$IdentityVerifier = Join-Path $RepoRoot ".github/scripts/assert_studio_windows_identity.ps1"
$IssPath = Join-Path $RepoRoot "tools/installer/gpbiometricspy_studio.iss"
$AppId = "fd3ca1af-0ebb-5061-9c59-f7ab1079252e"
$UninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\${AppId}_is1"
$StartMenuShortcut = Join-Path ([Environment]::GetFolderPath("Programs")) "gpbiometricspy Studio.lnk"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "gpbiometricspy Studio.lnk"
$WebView2ProductId = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
$WebView2MachineKey = "Registry::HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$WebView2ProductId"
$WebView2UserKey = "Registry::HKEY_CURRENT_USER\Software\Microsoft\EdgeUpdate\Clients\$WebView2ProductId"

New-Item -ItemType Directory -Force -Path $ArtifactsDir, $EvidenceDir, $InstallerOutput | Out-Null

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-PeSubsystem {
    param([Parameter(Mandatory = $true)][string]$Executable)

    $Stream = [System.IO.File]::Open($Executable, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    $Reader = [System.IO.BinaryReader]::new($Stream)
    try {
        $Reader.BaseStream.Seek(0x3C, [System.IO.SeekOrigin]::Begin) | Out-Null
        $PeOffset = $Reader.ReadInt32()
        if ($PeOffset -lt 0) { throw "Invalid PE header offset." }
        $Reader.BaseStream.Seek($PeOffset, [System.IO.SeekOrigin]::Begin) | Out-Null
        if ($Reader.ReadUInt32() -ne 0x00004550) { throw "Invalid PE signature." }
        $Reader.BaseStream.Seek($PeOffset + 92, [System.IO.SeekOrigin]::Begin) | Out-Null
        return [int]$Reader.ReadUInt16()
    }
    finally {
        $Reader.Dispose()
        $Stream.Dispose()
    }
}

function Find-InnoCompiler {
    $Command = Get-Command ISCC.exe -CommandType Application -ErrorAction SilentlyContinue
    if ($null -ne $Command) { return $Command.Source }
    foreach ($Candidate in @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )) {
        if (Test-Path -LiteralPath $Candidate -PathType Leaf) { return $Candidate }
    }
    return $null
}

function Get-WebView2RuntimeEvidence {
    foreach ($Candidate in @(
        [pscustomobject]@{ Scope = "machine"; Path = $WebView2MachineKey },
        [pscustomobject]@{ Scope = "user"; Path = $WebView2UserKey }
    )) {
        if (-not (Test-Path -LiteralPath $Candidate.Path)) { continue }
        $Version = [string](Get-ItemPropertyValue -LiteralPath $Candidate.Path -Name "pv" -ErrorAction SilentlyContinue)
        if ($Version -and $Version.Trim() -and $Version.Trim() -ne "0.0.0.0") {
            return [pscustomobject]@{ Version = $Version.Trim(); Scope = $Candidate.Scope; RegistryPath = $Candidate.Path }
        }
    }
    throw "Microsoft Edge WebView2 Runtime was not detected in the documented machine/user registry locations."
}

function Invoke-InstalledWindowedBoundarySmoke {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][int]$BoundaryPort,
        [switch]$PublicDemo
    )

    $WindowedLog = Join-Path $EvidenceDir ("installed-windowed-{0}.log" -f $Name)
    Remove-Item -LiteralPath $WindowedLog -Force -ErrorAction SilentlyContinue
    $Arguments = @("--host", "127.0.0.1", "--port", "$BoundaryPort", "--automation-close-seconds", "30")
    if ($PublicDemo) { $Arguments += "--public-demo" }

    $OldWindowedLog = $env:GPBIOMETRICSPY_WINDOWED_LOG_PATH
    try {
        $env:GPBIOMETRICSPY_WINDOWED_LOG_PATH = $WindowedLog
        $Started = Get-Date
        $Process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $InstallRoot -PassThru

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
            throw "Installed windowed Studio ($Name) did not become reachable."
        }

        $Startup = ((Get-Date) - $Started).TotalSeconds
        if (-not $Process.WaitForExit(60000)) {
            Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
            throw "Installed windowed Studio ($Name) did not close after DOM-readiness automation."
        }
        if ($Process.ExitCode -ne 0) {
            if (Test-Path -LiteralPath $WindowedLog) { Get-Content -LiteralPath $WindowedLog }
            throw "Installed windowed Studio ($Name) exited with code $($Process.ExitCode)."
        }
        if (-not (Test-Path -LiteralPath $WindowedLog -PathType Leaf)) {
            throw "Installed windowed Studio ($Name) did not create its diagnostic log."
        }

        $Output = Get-Content -LiteralPath $WindowedLog -Raw
        if ($Output -notmatch "Windowed release bootstrap: console_attached=false") {
            throw "Installed windowed Studio ($Name) missed the console-free bootstrap invariant."
        }
        if ($Output -notmatch "Native renderer requested: edgechromium") {
            throw "Installed windowed Studio ($Name) did not request edgechromium."
        }
        if ($Output -notmatch "Native DOM loaded\.") {
            throw "Installed windowed Studio ($Name) did not reach DOM loaded."
        }
        if ($Output -notmatch "window closed cleanly") {
            throw "Installed windowed Studio ($Name) did not close cleanly."
        }

        return [Math]::Round($Startup, 3)
    }
    finally {
        if ($null -eq $OldWindowedLog) { Remove-Item Env:GPBIOMETRICSPY_WINDOWED_LOG_PATH -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_WINDOWED_LOG_PATH = $OldWindowedLog }
    }
}

if (Test-Path -LiteralPath $UninstallKey) { throw "Runner is contaminated by an existing gpbiometricspy Studio uninstall registration." }
foreach ($Path in @($InstallRoot, $MissingRuntimeInstallRoot)) {
    if (Test-Path -LiteralPath $Path) { Remove-Item -LiteralPath $Path -Recurse -Force }
}
foreach ($Shortcut in @($StartMenuShortcut, $DesktopShortcut)) {
    if (Test-Path -LiteralPath $Shortcut) { Remove-Item -LiteralPath $Shortcut -Force }
}

$WebView2Evidence = Get-WebView2RuntimeEvidence
$Iscc = Find-InnoCompiler
if ($null -eq $Iscc) { throw "Inno Setup ISCC.exe was not found on the Windows runner." }
$InnoVersion = (Get-Item -LiteralPath $Iscc).VersionInfo.FileVersion

Write-Host "Creating isolated windowed installer build environment..."
& $Python -m venv $VenvRoot
if ($LASTEXITCODE -ne 0) { throw "Failed to create windowed installer build environment." }
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }
& $VenvPython -m pip install -e ("{0}[studio-native]" -f $RepoRoot)
if ($LASTEXITCODE -ne 0) { throw "Failed to install native Studio dependencies." }
& $VenvPython -m pip install -r $RequirementsPath
if ($LASTEXITCODE -ne 0) { throw "Failed to install pinned PyInstaller tools." }
& $VenvPython -m pip install pytest
if ($LASTEXITCODE -ne 0) { throw "Failed to install pytest." }
& $VenvPython -m pytest -q `
    (Join-Path $RepoRoot "studio/tests/test_native.py") `
    (Join-Path $RepoRoot "studio/tests/test_native_frozen.py") `
    (Join-Path $RepoRoot "studio/tests/test_native_windowed.py")
if ($LASTEXITCODE -ne 0) { throw "Windowed launcher unit contracts failed." }

Write-Host "Generating Windows identity and building GUI-subsystem native bundle..."
& $VenvPython $IdentityGenerator --repo-root $RepoRoot --output-dir $IdentityDir --target native
if ($LASTEXITCODE -ne 0) { throw "Failed to generate Windows identity." }
$env:GPBIOMETRICSPY_WINDOWS_IDENTITY_DIR = $IdentityDir
$BuildStarted = Get-Date
Push-Location $RepoRoot
try {
    & $VenvPython -m PyInstaller --noconfirm --clean --distpath $DistRoot --workpath $BuildRoot $SpecPath
    if ($LASTEXITCODE -ne 0) { throw "Windowed PyInstaller build failed." }
}
finally { Pop-Location }
$BuildSeconds = ((Get-Date) - $BuildStarted).TotalSeconds

$BundleRoot = Join-Path $DistRoot "gpbiometricspy-studio-native"
$SourceExecutable = Join-Path $BundleRoot "gpbiometricspy-studio-native.exe"
if (-not (Test-Path -LiteralPath $SourceExecutable -PathType Leaf)) { throw "Windowed source executable is missing." }
& $IdentityVerifier -Executable $SourceExecutable -IdentityJson $IdentityJson -IconPath $IconPath
if ($LASTEXITCODE -ne 0) { throw "Windowed source executable failed Windows identity verification." }
$Identity = Get-Content -LiteralPath $IdentityJson -Raw | ConvertFrom-Json
$SourcePeSubsystem = Get-PeSubsystem -Executable $SourceExecutable
if ($SourcePeSubsystem -ne 2) { throw "Windowed source executable is not IMAGE_SUBSYSTEM_WINDOWS_GUI (2)." }
$SourceExecutableSha256 = Get-Sha256 $SourceExecutable
$BundleFiles = @(Get-ChildItem -LiteralPath $BundleRoot -Recurse -File)
$BundleBytes = [int64](($BundleFiles | Measure-Object -Property Length -Sum).Sum)

$OldBundleEnv = $env:GPBIOMETRICSPY_INSTALLER_BUNDLE
$OldIconEnv = $env:GPBIOMETRICSPY_INSTALLER_ICON
$OldAppVersionEnv = $env:GPBIOMETRICSPY_INSTALLER_APP_VERSION
$OldFileVersionEnv = $env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION
try {
    $env:GPBIOMETRICSPY_INSTALLER_BUNDLE = $BundleRoot
    $env:GPBIOMETRICSPY_INSTALLER_ICON = $IconPath
    $env:GPBIOMETRICSPY_INSTALLER_APP_VERSION = [string]$Identity.product_version
    $env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION = [string]$Identity.file_version
    $CompileOutput = & $Iscc "/Qp" ("/O{0}" -f $InstallerOutput) $IssPath 2>&1
    $CompileExit = $LASTEXITCODE
    $CompileOutput | Set-Content -LiteralPath $CompileLog -Encoding UTF8
    if ($CompileExit -ne 0) { throw "Inno Setup compilation failed with exit code $CompileExit." }
}
finally {
    if ($null -eq $OldBundleEnv) { Remove-Item Env:GPBIOMETRICSPY_INSTALLER_BUNDLE -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_INSTALLER_BUNDLE = $OldBundleEnv }
    if ($null -eq $OldIconEnv) { Remove-Item Env:GPBIOMETRICSPY_INSTALLER_ICON -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_INSTALLER_ICON = $OldIconEnv }
    if ($null -eq $OldAppVersionEnv) { Remove-Item Env:GPBIOMETRICSPY_INSTALLER_APP_VERSION -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_INSTALLER_APP_VERSION = $OldAppVersionEnv }
    if ($null -eq $OldFileVersionEnv) { Remove-Item Env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION = $OldFileVersionEnv }
}

$Installer = Join-Path $InstallerOutput "gpbiometricspy-studio-setup.exe"
if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) { throw "Installer executable was not created." }
if ([string](Get-AuthenticodeSignature -LiteralPath $Installer).Status -ne "NotSigned") { throw "Integration proof installer must remain unsigned." }
$InstallerSha256 = Get-Sha256 $Installer
$InstallerBytes = [int64](Get-Item -LiteralPath $Installer).Length

$OldForceMissing = $env:GPBIOMETRICSPY_CI_FORCE_WEBVIEW2_MISSING
try {
    $env:GPBIOMETRICSPY_CI_FORCE_WEBVIEW2_MISSING = "1"
    $MissingArgs = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOCANCEL", "/SP-", "/DIR=`"$MissingRuntimeInstallRoot`"", "/LOG=`"$MissingRuntimeInstallLog`"")
    $MissingProcess = Start-Process -FilePath $Installer -ArgumentList $MissingArgs -Wait -PassThru
}
finally {
    if ($null -eq $OldForceMissing) { Remove-Item Env:GPBIOMETRICSPY_CI_FORCE_WEBVIEW2_MISSING -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_CI_FORCE_WEBVIEW2_MISSING = $OldForceMissing }
}
if ($MissingProcess.ExitCode -ne 7) { throw "Missing-WebView2 setup must fail with exit code 7; got $($MissingProcess.ExitCode)." }
$MissingText = if (Test-Path -LiteralPath $MissingRuntimeInstallLog) { Get-Content -LiteralPath $MissingRuntimeInstallLog -Raw } else { "" }
if ($MissingText -notmatch "WebView2 Runtime missing") { throw "Missing-WebView2 setup log did not record prerequisite failure." }
if (Test-Path -LiteralPath (Join-Path $MissingRuntimeInstallRoot "gpbiometricspy-studio-native.exe")) { throw "Missing-WebView2 path installed the application payload." }
if (Test-Path -LiteralPath $UninstallKey) { throw "Missing-WebView2 path created uninstall registration." }
if (Test-Path -LiteralPath $StartMenuShortcut) { throw "Missing-WebView2 path created Start Menu shortcut." }
Remove-Item -LiteralPath $MissingRuntimeInstallRoot -Recurse -Force -ErrorAction SilentlyContinue

$InstallArgs = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOCANCEL", "/SP-", "/DIR=`"$InstallRoot`"", "/LOG=`"$InstallLog`"")
$InstallProcess = Start-Process -FilePath $Installer -ArgumentList $InstallArgs -Wait -PassThru
if ($InstallProcess.ExitCode -ne 0) { throw "Installer exited with code $($InstallProcess.ExitCode)." }
$InstallText = if (Test-Path -LiteralPath $InstallLog) { Get-Content -LiteralPath $InstallLog -Raw } else { "" }
if ($InstallText -notmatch "WebView2 Runtime detected") { throw "Successful install log did not record WebView2 detection." }

$InstalledExecutable = Join-Path $InstallRoot "gpbiometricspy-studio-native.exe"
$Uninstaller = Join-Path $InstallRoot "unins000.exe"
if (-not (Test-Path -LiteralPath $InstalledExecutable -PathType Leaf)) { throw "Installed windowed executable is missing." }
if (-not (Test-Path -LiteralPath $Uninstaller -PathType Leaf)) { throw "Uninstaller is missing." }
if (-not (Test-Path -LiteralPath $UninstallKey)) { throw "Uninstall registration is missing." }
if (-not (Test-Path -LiteralPath $StartMenuShortcut -PathType Leaf)) { throw "Start Menu shortcut is missing." }
if (Test-Path -LiteralPath $DesktopShortcut -PathType Leaf) { throw "Desktop shortcut was created despite being opt-in." }

$InstalledSha256 = Get-Sha256 $InstalledExecutable
if ($InstalledSha256 -ne $SourceExecutableSha256) { throw "Installed windowed executable bytes differ from source bundle input." }
$InstalledPeSubsystem = Get-PeSubsystem -Executable $InstalledExecutable
if ($InstalledPeSubsystem -ne 2) { throw "Installed executable lost IMAGE_SUBSYSTEM_WINDOWS_GUI (2)." }
& $IdentityVerifier -Executable $InstalledExecutable -IdentityJson $IdentityJson -IconPath $IconPath
if ($LASTEXITCODE -ne 0) { throw "Installed windowed executable failed Windows identity verification." }

$OriginalPath = $env:PATH
$OriginalPythonHome = $env:PYTHONHOME
$OriginalPythonPath = $env:PYTHONPATH
try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    if (Get-Command python -CommandType Application -ErrorAction SilentlyContinue) { throw "PATH isolation failed: external Python remains discoverable." }
    $LocalStartup = Invoke-InstalledWindowedBoundarySmoke -Executable $InstalledExecutable -Name "local" -BoundaryPort ($Port + 10)
    $PublicStartup = Invoke-InstalledWindowedBoundarySmoke -Executable $InstalledExecutable -Name "public" -BoundaryPort ($Port + 11) -PublicDemo
}
finally {
    $env:PATH = $OriginalPath
    if ($null -eq $OriginalPythonHome) { Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue } else { $env:PYTHONHOME = $OriginalPythonHome }
    if ($null -eq $OriginalPythonPath) { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue } else { $env:PYTHONPATH = $OriginalPythonPath }
}

$UninstallArgs = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=`"$UninstallLog`"")
$UninstallProcess = Start-Process -FilePath $Uninstaller -ArgumentList $UninstallArgs -Wait -PassThru
if ($UninstallProcess.ExitCode -ne 0) { throw "Uninstaller exited with code $($UninstallProcess.ExitCode)." }
Start-Sleep -Seconds 2
if (Test-Path -LiteralPath $InstalledExecutable) { throw "Installed executable survived uninstall." }
if (Test-Path -LiteralPath $Uninstaller) { throw "Uninstaller survived uninstall." }
if (Test-Path -LiteralPath $UninstallKey) { throw "Uninstall registration survived uninstall." }
if (Test-Path -LiteralPath $StartMenuShortcut) { throw "Start Menu shortcut survived uninstall." }
if (Test-Path -LiteralPath $DesktopShortcut) { throw "Desktop shortcut exists after uninstall." }
$ResidualPayload = @()
if (Test-Path -LiteralPath $InstallRoot) {
    $ResidualPayload = @(Get-ChildItem -LiteralPath $InstallRoot -Recurse -Force -File -ErrorAction SilentlyContinue)
}
if ($ResidualPayload.Count -ne 0) { throw "Installer payload files survived uninstall: $($ResidualPayload.Count)." }
Remove-Item -LiteralPath $InstallRoot -Recurse -Force -ErrorAction SilentlyContinue

$Metrics = [ordered]@{
    schema = "gpbiometricspy-studio-windowed-installer-readiness"
    schema_version = 1
    release_artifact = $false
    installer_published = $false
    installer_signed = $false
    installer_tool = "Inno Setup"
    installer_tool_version = $InnoVersion
    install_scope = "current-user"
    elevation_required = $false
    app_id = $AppId
    product_name = $Identity.product_name
    product_version = $Identity.product_version
    file_version = $Identity.file_version
    source_bundle_mode = "onedir-native-windowed-webview2"
    source_pe_subsystem = $SourcePeSubsystem
    installed_pe_subsystem = $InstalledPeSubsystem
    pe_subsystem_name = "IMAGE_SUBSYSTEM_WINDOWS_GUI"
    console = $false
    console_attached = $false
    engineering_console_build_preserved = $true
    source_executable_sha256 = $SourceExecutableSha256
    installed_executable_sha256 = $InstalledSha256
    installed_executable_identity_match = $true
    installer_sha256 = $InstallerSha256
    installer_bytes = $InstallerBytes
    source_bundle_files = $BundleFiles.Count
    source_bundle_bytes = $BundleBytes
    source_build_seconds = [Math]::Round($BuildSeconds, 3)
    local_dom_smoke = $true
    public_demo_dom_smoke = $true
    local_http_startup_seconds = $LocalStartup
    public_http_startup_seconds = $PublicStartup
    external_python_required = $false
    uninstall_exit_code = $UninstallProcess.ExitCode
    uninstall_registration_removed = $true
    shortcuts_removed = $true
    payload_files_removed = $true
    webview2_runtime_strategy = "evergreen-prerequisite-detect-and-remediate"
    webview2_runtime_required = $true
    webview2_runtime_version = $WebView2Evidence.Version
    webview2_runtime_scope = $WebView2Evidence.Scope
    webview2_missing_install_exit_code = $MissingProcess.ExitCode
    webview2_missing_install_blocked = $true
    webview2_runtime_payload_bundled = $false
    webview2_runtime_downloaded_in_ci = $false
    production_signing_required = $true
    production_timestamp_required = $true
    python_version = ((& $VenvPython --version 2>&1) | Out-String).Trim()
    pyinstaller_version = ((& $VenvPython -m PyInstaller --version 2>&1) | Out-String).Trim()
    pywebview_version = ((& $VenvPython -c "import importlib.metadata as m; print(m.version('pywebview'))" 2>&1) | Out-String).Trim()
}
$Metrics | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $MetricsPath -Encoding UTF8

Remove-Item -LiteralPath $InstallerOutput -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $DistRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $BuildRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $VenvRoot -Recurse -Force -ErrorAction SilentlyContinue
if (Get-ChildItem -LiteralPath $EvidenceDir -Recurse -File -Include "*.exe", "*.pfx", "*.p12" -ErrorAction SilentlyContinue) {
    throw "Windowed-installer evidence must not retain executables or signing-key material."
}

Write-Host "Windowed installer integration proof passed: GUI PE subsystem, no attached console, WebView2 prerequisite, exact installed bytes, local/public DOM readiness, and clean uninstall verified."
