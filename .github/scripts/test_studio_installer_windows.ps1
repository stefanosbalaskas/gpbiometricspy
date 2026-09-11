param(
    [string]$Python = "python",
    [int]$Port = 8975,
    [string]$ArtifactsDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path ([System.IO.Path]::GetTempPath()) ("gpbiometricspy-installer-readiness-" + [guid]::NewGuid().ToString("N"))
}
$ArtifactsDir = [System.IO.Path]::GetFullPath($ArtifactsDir)
$BuildArtifacts = Join-Path $ArtifactsDir "native-build"
$InstallerOutput = Join-Path $ArtifactsDir "installer-output"
$InstallRoot = Join-Path $ArtifactsDir "installed\gpbiometricspy Studio"
$EvidenceDir = Join-Path $ArtifactsDir "evidence"
$MetricsPath = Join-Path $EvidenceDir "installer-metrics.json"
$CompileLog = Join-Path $EvidenceDir "iscc.log"
$InstallLog = Join-Path $EvidenceDir "install.log"
$UninstallLog = Join-Path $EvidenceDir "uninstall.log"
$IssPath = Join-Path $RepoRoot "tools/installer/gpbiometricspy_studio.iss"
$IdentityVerifier = Join-Path $RepoRoot ".github/scripts/assert_studio_windows_identity.ps1"
$NativeHarness = Join-Path $RepoRoot ".github/scripts/test_studio_pyinstaller_native_windows.ps1"
$AppId = "fd3ca1af-0ebb-5061-9c59-f7ab1079252e"
$UninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\${AppId}_is1"
$StartMenuShortcut = Join-Path ([Environment]::GetFolderPath("Programs")) "gpbiometricspy Studio.lnk"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "gpbiometricspy Studio.lnk"

New-Item -ItemType Directory -Force -Path $ArtifactsDir, $InstallerOutput, $EvidenceDir | Out-Null

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Find-InnoCompiler {
    $Command = Get-Command ISCC.exe -CommandType Application -ErrorAction SilentlyContinue
    if ($null -ne $Command) { return $Command.Source }

    $Candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )
    foreach ($Candidate in $Candidates) {
        if (Test-Path -LiteralPath $Candidate -PathType Leaf) { return $Candidate }
    }
    return $null
}

function Invoke-InstalledBoundarySmoke {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][int]$BoundaryPort,
        [switch]$PublicDemo
    )

    $StdoutLog = Join-Path $EvidenceDir ("installed-{0}-stdout.log" -f $Name)
    $StderrLog = Join-Path $EvidenceDir ("installed-{0}-stderr.log" -f $Name)
    $Arguments = @("--host", "127.0.0.1", "--port", "$BoundaryPort", "--automation-close-seconds", "30")
    if ($PublicDemo) { $Arguments += "--public-demo" }

    $Started = Get-Date
    $Process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $InstallRoot `
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
        if (Test-Path -LiteralPath $StdoutLog) { Get-Content -LiteralPath $StdoutLog }
        if (Test-Path -LiteralPath $StderrLog) { Get-Content -LiteralPath $StderrLog }
        throw "Installed Studio ($Name) did not become reachable."
    }

    $Startup = ((Get-Date) - $Started).TotalSeconds
    if (-not $Process.WaitForExit(60000)) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
        throw "Installed Studio ($Name) did not close after DOM-readiness automation."
    }
    if ($Process.ExitCode -ne 0) {
        if (Test-Path -LiteralPath $StdoutLog) { Get-Content -LiteralPath $StdoutLog }
        if (Test-Path -LiteralPath $StderrLog) { Get-Content -LiteralPath $StderrLog }
        throw "Installed Studio ($Name) exited with code $($Process.ExitCode)."
    }

    $Output = if (Test-Path -LiteralPath $StdoutLog) { Get-Content -LiteralPath $StdoutLog -Raw } else { "" }
    if ($Output -notmatch "Native renderer requested: edgechromium") {
        throw "Installed Studio ($Name) did not request edgechromium."
    }
    if ($Output -notmatch "Native DOM loaded\.") {
        throw "Installed Studio ($Name) did not reach DOM loaded."
    }
    if ($Output -notmatch "window closed cleanly") {
        throw "Installed Studio ($Name) did not close cleanly."
    }

    return [Math]::Round($Startup, 3)
}

if (Test-Path -LiteralPath $UninstallKey) {
    throw "Installer-readiness runner is contaminated by an existing gpbiometricspy Studio uninstall registration."
}
if (Test-Path -LiteralPath $InstallRoot) {
    Remove-Item -LiteralPath $InstallRoot -Recurse -Force
}
if (Test-Path -LiteralPath $StartMenuShortcut) {
    Remove-Item -LiteralPath $StartMenuShortcut -Force
}
if (Test-Path -LiteralPath $DesktopShortcut) {
    Remove-Item -LiteralPath $DesktopShortcut -Force
}

$Iscc = Find-InnoCompiler
if ($null -eq $Iscc) { throw "Inno Setup ISCC.exe was not found on the Windows runner." }
$InnoVersion = (Get-Item -LiteralPath $Iscc).VersionInfo.FileVersion
Write-Host "Using Inno Setup compiler: $Iscc ($InnoVersion)"

Write-Host "Building and exercising the certified native Studio bundle before installer compilation..."
& $NativeHarness -Python $Python -Port $Port -ArtifactsDir $BuildArtifacts
if ($LASTEXITCODE -ne 0) { throw "Native Studio prerequisite proof failed." }

$BundleRoot = Join-Path $BuildArtifacts "dist/gpbiometricspy-studio-native"
$SourceExecutable = Join-Path $BundleRoot "gpbiometricspy-studio-native.exe"
$IdentityJson = Join-Path $BuildArtifacts "identity/windows-identity.json"
$IconPath = Join-Path $BuildArtifacts "identity/gpbiometricspy-studio.ico"
$NativeMetrics = Join-Path $BuildArtifacts "native-metrics.json"
if (-not (Test-Path -LiteralPath $SourceExecutable -PathType Leaf)) { throw "Native source executable is missing." }

$Identity = Get-Content -LiteralPath $IdentityJson -Raw | ConvertFrom-Json
$SourceExecutableSha256 = Get-Sha256 $SourceExecutable

$OldBundleEnv = $env:GPBIOMETRICSPY_INSTALLER_BUNDLE
$OldIconEnv = $env:GPBIOMETRICSPY_INSTALLER_ICON
$OldAppVersionEnv = $env:GPBIOMETRICSPY_INSTALLER_APP_VERSION
$OldFileVersionEnv = $env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION
try {
    $env:GPBIOMETRICSPY_INSTALLER_BUNDLE = $BundleRoot
    $env:GPBIOMETRICSPY_INSTALLER_ICON = $IconPath
    $env:GPBIOMETRICSPY_INSTALLER_APP_VERSION = [string]$Identity.product_version
    $env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION = [string]$Identity.file_version

    Write-Host "Compiling unsigned per-user installer..."
    $CompileOutput = & $Iscc "/Qp" ("/O{0}" -f $InstallerOutput) $IssPath 2>&1
    $CompileExit = $LASTEXITCODE
    $CompileOutput | Set-Content -LiteralPath $CompileLog -Encoding UTF8
    $CompileOutput | ForEach-Object { Write-Host $_ }
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
$InstallerSignature = Get-AuthenticodeSignature -LiteralPath $Installer
if ([string]$InstallerSignature.Status -ne "NotSigned") {
    throw "Installer-readiness output must remain unsigned; got $($InstallerSignature.Status)."
}

$InstallerSha256 = Get-Sha256 $Installer
$InstallerBytes = [int64](Get-Item -LiteralPath $Installer).Length
Write-Host "Unsigned installer SHA-256: $InstallerSha256"

$InstallArgs = @(
    "/VERYSILENT",
    "/SUPPRESSMSGBOXES",
    "/NORESTART",
    "/NOCANCEL",
    "/SP-",
    "/DIR=`"$InstallRoot`"",
    "/LOG=`"$InstallLog`""
)
$InstallProcess = Start-Process -FilePath $Installer -ArgumentList $InstallArgs -Wait -PassThru
if ($InstallProcess.ExitCode -ne 0) { throw "Installer exited with code $($InstallProcess.ExitCode)." }

$InstalledExecutable = Join-Path $InstallRoot "gpbiometricspy-studio-native.exe"
$Uninstaller = Join-Path $InstallRoot "unins000.exe"
if (-not (Test-Path -LiteralPath $InstalledExecutable -PathType Leaf)) { throw "Installed native executable is missing." }
if (-not (Test-Path -LiteralPath $Uninstaller -PathType Leaf)) { throw "Inno Setup uninstaller is missing." }
if (-not (Test-Path -LiteralPath $UninstallKey)) { throw "Current-user uninstall registration was not created." }
if (-not (Test-Path -LiteralPath $StartMenuShortcut -PathType Leaf)) { throw "Current-user Start Menu shortcut was not created." }
if (Test-Path -LiteralPath $DesktopShortcut -PathType Leaf) { throw "Desktop shortcut was created even though the task is unchecked by default." }

$InstalledSha256 = Get-Sha256 $InstalledExecutable
if ($InstalledSha256 -ne $SourceExecutableSha256) {
    throw "Installed executable bytes differ from the certified native bundle input."
}

& $IdentityVerifier -Executable $InstalledExecutable -IdentityJson $IdentityJson -IconPath $IconPath
if ($LASTEXITCODE -ne 0) { throw "Installed executable failed the Windows identity contract." }

$OriginalPath = $env:PATH
$OriginalPythonHome = $env:PYTHONHOME
$OriginalPythonPath = $env:PYTHONPATH
try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    if (Get-Command python -CommandType Application -ErrorAction SilentlyContinue) {
        throw "PATH isolation failed: an external python executable is still discoverable."
    }

    $LocalStartup = Invoke-InstalledBoundarySmoke -Executable $InstalledExecutable -Name "local" -BoundaryPort ($Port + 10)
    $PublicStartup = Invoke-InstalledBoundarySmoke -Executable $InstalledExecutable -Name "public" -BoundaryPort ($Port + 11) -PublicDemo
}
finally {
    $env:PATH = $OriginalPath
    if ($null -eq $OriginalPythonHome) { Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue } else { $env:PYTHONHOME = $OriginalPythonHome }
    if ($null -eq $OriginalPythonPath) { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue } else { $env:PYTHONPATH = $OriginalPythonPath }
}

$UninstallArgs = @(
    "/VERYSILENT",
    "/SUPPRESSMSGBOXES",
    "/NORESTART",
    "/LOG=`"$UninstallLog`""
)
$UninstallProcess = Start-Process -FilePath $Uninstaller -ArgumentList $UninstallArgs -Wait -PassThru
if ($UninstallProcess.ExitCode -ne 0) { throw "Uninstaller exited with code $($UninstallProcess.ExitCode)." }

Start-Sleep -Seconds 2
if (Test-Path -LiteralPath $InstalledExecutable -PathType Leaf) { throw "Installed executable survived uninstall." }
if (Test-Path -LiteralPath $Uninstaller -PathType Leaf) { throw "Uninstaller survived uninstall." }
if (Test-Path -LiteralPath $UninstallKey) { throw "Current-user uninstall registration survived uninstall." }
if (Test-Path -LiteralPath $StartMenuShortcut -PathType Leaf) { throw "Start Menu shortcut survived uninstall." }
if (Test-Path -LiteralPath $DesktopShortcut -PathType Leaf) { throw "Desktop shortcut exists after uninstall." }

$ResidualPayload = @()
if (Test-Path -LiteralPath $InstallRoot -PathType Container) {
    $ResidualPayload = @(Get-ChildItem -LiteralPath $InstallRoot -Recurse -Force -File -ErrorAction SilentlyContinue)
}
if ($ResidualPayload.Count -ne 0) {
    throw "Installer payload files survived uninstall: $($ResidualPayload.Count) file(s)."
}
if (Test-Path -LiteralPath $InstallRoot -PathType Container) {
    Remove-Item -LiteralPath $InstallRoot -Recurse -Force
}

Copy-Item -LiteralPath $NativeMetrics -Destination (Join-Path $EvidenceDir "native-metrics.json") -Force
Copy-Item -LiteralPath $IdentityJson -Destination (Join-Path $EvidenceDir "windows-identity.json") -Force
Copy-Item -LiteralPath (Join-Path $BuildArtifacts "identity/version-info.txt") -Destination (Join-Path $EvidenceDir "version-info.txt") -Force

$Metrics = [ordered]@{
    schema = "gpbiometricspy-studio-installer-readiness"
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
    source_executable_sha256 = $SourceExecutableSha256
    installed_executable_sha256 = $InstalledSha256
    installed_executable_identity_match = $true
    installer_sha256 = $InstallerSha256
    installer_bytes = $InstallerBytes
    start_menu_shortcut_created = $true
    desktop_shortcut_default = $false
    uninstall_registration_created = $true
    local_dom_smoke = $true
    public_demo_dom_smoke = $true
    local_http_startup_seconds = $LocalStartup
    public_http_startup_seconds = $PublicStartup
    external_python_required = $false
    uninstall_exit_code = $UninstallProcess.ExitCode
    uninstall_registration_removed = $true
    shortcuts_removed = $true
    payload_files_removed = $true
    webview2_runtime_strategy = "host-provided-evaluation-only"
    production_signing_required = $true
    production_timestamp_required = $true
}
$Metrics | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $MetricsPath -Encoding UTF8

# The proof is diagnostics-only. Remove redistributable payloads before upload.
Remove-Item -LiteralPath $InstallerOutput -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $BuildArtifacts "dist") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $BuildArtifacts "build") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $BuildArtifacts "venv") -Recurse -Force -ErrorAction SilentlyContinue

if (Get-ChildItem -LiteralPath $EvidenceDir -Recurse -File -Include "*.exe", "*.pfx", "*.p12" -ErrorAction SilentlyContinue) {
    throw "Installer-readiness evidence must not retain executable or signing-key material."
}

Write-Host "Windows installer readiness proof passed: per-user install, native launch, public-demo launch, and clean uninstall verified."
