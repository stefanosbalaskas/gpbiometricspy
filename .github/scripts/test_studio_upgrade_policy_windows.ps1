param(
    [string]$Python = "python",
    [string]$ArtifactsDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path ([System.IO.Path]::GetTempPath()) ("gpbiometricspy-upgrade-policy-" + [guid]::NewGuid().ToString("N"))
}
$ArtifactsDir = [System.IO.Path]::GetFullPath($ArtifactsDir)
$EvidenceDir = Join-Path $ArtifactsDir "evidence"
$WorkRoot = Join-Path $ArtifactsDir "upgrade-policy-work"
$BuildRoot = Join-Path $WorkRoot "build"
$DistRoot = Join-Path $WorkRoot "dist"
$VenvRoot = Join-Path $WorkRoot "venv"
$VenvPython = Join-Path $VenvRoot "Scripts/python.exe"
$IdentityDir = Join-Path $WorkRoot "identity"
$IdentityJson = Join-Path $IdentityDir "windows-identity.json"
$IconPath = Join-Path $IdentityDir "gpbiometricspy-studio.ico"
$InstallerOutput = Join-Path $WorkRoot "installer-output"
$InstallRoot = Join-Path $WorkRoot "installed\gpbiometricspy Studio"
$MetricsPath = Join-Path $EvidenceDir "upgrade-policy-metrics.json"
$FirstInstallLog = Join-Path $EvidenceDir "upgrade-policy-first-install.log"
$FallbackRepairLog = Join-Path $EvidenceDir "upgrade-policy-fallback-repair.log"
$RegistryRepairLog = Join-Path $EvidenceDir "upgrade-policy-registry-repair.log"
$UpgradeLog = Join-Path $EvidenceDir "upgrade-policy-upgrade.log"
$DowngradeLog = Join-Path $EvidenceDir "upgrade-policy-downgrade.log"
$UninstallLog = Join-Path $EvidenceDir "upgrade-policy-uninstall.log"
$SpecPath = Join-Path $RepoRoot "tools/pyinstaller/gpbiometricspy_studio_native_windowed.spec"
$RequirementsPath = Join-Path $RepoRoot "tools/pyinstaller/requirements.txt"
$IdentityGenerator = Join-Path $RepoRoot "tools/pyinstaller/generate_windows_identity.py"
$IdentityVerifier = Join-Path $RepoRoot ".github/scripts/assert_studio_windows_identity.ps1"
$IssPath = Join-Path $RepoRoot "tools/installer/gpbiometricspy_studio.iss"
$AppId = "fd3ca1af-0ebb-5061-9c59-f7ab1079252e"
$UninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\${AppId}_is1"
$UpgradePolicyKey = "HKCU:\Software\StefanosBalaskas\gpbiometricspy Studio"
$UpgradePolicyValue = "InstalledFileVersion"
$PreviousFileVersion = "0.1.5.0"
$FutureFileVersion = "0.1.7.0"
$StartMenuShortcut = Join-Path ([Environment]::GetFolderPath("Programs")) "gpbiometricspy Studio.lnk"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "gpbiometricspy Studio.lnk"

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
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

function Invoke-SilentSetup {
    param(
        [Parameter(Mandatory = $true)][string]$Installer,
        [Parameter(Mandatory = $true)][string]$LogPath,
        [string]$Directory = ""
    )

    $Arguments = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOCANCEL", "/SP-", "/LOG=`"$LogPath`"")
    if ($Directory) { $Arguments += "/DIR=`"$Directory`"" }
    return Start-Process -FilePath $Installer -ArgumentList $Arguments -Wait -PassThru
}

function Read-Log {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Expected setup log is missing: $Path" }
    return Get-Content -LiteralPath $Path -Raw
}

function Get-UpgradeMarker {
    if (-not (Test-Path -LiteralPath $UpgradePolicyKey)) { return $null }
    return [string](Get-ItemPropertyValue -LiteralPath $UpgradePolicyKey -Name $UpgradePolicyValue -ErrorAction SilentlyContinue)
}

function Assert-SourceBytesRestored {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string]$ExpectedSha256,
        [Parameter(Mandatory = $true)][string]$Context
    )
    $Actual = Get-Sha256 $Executable
    if ($Actual -ne $ExpectedSha256) { throw "$Context did not restore the certified source executable bytes." }
}

New-Item -ItemType Directory -Force -Path $ArtifactsDir, $EvidenceDir | Out-Null
if (Test-Path -LiteralPath $WorkRoot) { Remove-Item -LiteralPath $WorkRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $WorkRoot, $InstallerOutput | Out-Null

if (Test-Path -LiteralPath $UninstallKey) { throw "Runner is contaminated by an existing gpbiometricspy Studio uninstall registration." }
if (Test-Path -LiteralPath $UpgradePolicyKey) { throw "Runner is contaminated by an existing gpbiometricspy Studio upgrade-policy registry key." }
foreach ($Shortcut in @($StartMenuShortcut, $DesktopShortcut)) {
    if (Test-Path -LiteralPath $Shortcut) { throw "Runner is contaminated by an existing gpbiometricspy Studio shortcut: $Shortcut" }
}

$Iscc = Find-InnoCompiler
if ($null -eq $Iscc) { throw "Inno Setup ISCC.exe was not found on the Windows runner." }
$InnoVersion = (Get-Item -LiteralPath $Iscc).VersionInfo.FileVersion

Write-Host "Creating isolated upgrade-policy build environment..."
& $Python -m venv $VenvRoot
if ($LASTEXITCODE -ne 0) { throw "Failed to create upgrade-policy build environment." }
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }
& $VenvPython -m pip install -e ("{0}[studio-native]" -f $RepoRoot)
if ($LASTEXITCODE -ne 0) { throw "Failed to install native Studio dependencies." }
& $VenvPython -m pip install -r $RequirementsPath
if ($LASTEXITCODE -ne 0) { throw "Failed to install pinned PyInstaller tools." }

Write-Host "Building GUI-subsystem bundle for upgrade-policy proof..."
& $VenvPython $IdentityGenerator --repo-root $RepoRoot --output-dir $IdentityDir --target native
if ($LASTEXITCODE -ne 0) { throw "Failed to generate Windows identity." }
$Identity = Get-Content -LiteralPath $IdentityJson -Raw | ConvertFrom-Json
$TargetFileVersion = [string]$Identity.file_version
if ($TargetFileVersion -ne "0.1.6.0") { throw "Upgrade-policy fixture expects the 0.1.6.0 development file-version line; got $TargetFileVersion." }

$env:GPBIOMETRICSPY_WINDOWS_IDENTITY_DIR = $IdentityDir
Push-Location $RepoRoot
try {
    & $VenvPython -m PyInstaller --noconfirm --clean --distpath $DistRoot --workpath $BuildRoot $SpecPath
    if ($LASTEXITCODE -ne 0) { throw "Upgrade-policy PyInstaller build failed." }
}
finally { Pop-Location }

$BundleRoot = Join-Path $DistRoot "gpbiometricspy-studio-native"
$SourceExecutable = Join-Path $BundleRoot "gpbiometricspy-studio-native.exe"
if (-not (Test-Path -LiteralPath $SourceExecutable -PathType Leaf)) { throw "Upgrade-policy source executable is missing." }
& $IdentityVerifier -Executable $SourceExecutable -IdentityJson $IdentityJson -IconPath $IconPath
if ($LASTEXITCODE -ne 0) { throw "Upgrade-policy source executable failed Windows identity verification." }
$SourceExecutableSha256 = Get-Sha256 $SourceExecutable

$OldBundleEnv = $env:GPBIOMETRICSPY_INSTALLER_BUNDLE
$OldIconEnv = $env:GPBIOMETRICSPY_INSTALLER_ICON
$OldAppVersionEnv = $env:GPBIOMETRICSPY_INSTALLER_APP_VERSION
$OldFileVersionEnv = $env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION
try {
    $env:GPBIOMETRICSPY_INSTALLER_BUNDLE = $BundleRoot
    $env:GPBIOMETRICSPY_INSTALLER_ICON = $IconPath
    $env:GPBIOMETRICSPY_INSTALLER_APP_VERSION = [string]$Identity.product_version
    $env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION = $TargetFileVersion
    & $Iscc "/Qp" ("/O{0}" -f $InstallerOutput) $IssPath
    if ($LASTEXITCODE -ne 0) { throw "Upgrade-policy Inno Setup compilation failed." }
}
finally {
    if ($null -eq $OldBundleEnv) { Remove-Item Env:GPBIOMETRICSPY_INSTALLER_BUNDLE -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_INSTALLER_BUNDLE = $OldBundleEnv }
    if ($null -eq $OldIconEnv) { Remove-Item Env:GPBIOMETRICSPY_INSTALLER_ICON -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_INSTALLER_ICON = $OldIconEnv }
    if ($null -eq $OldAppVersionEnv) { Remove-Item Env:GPBIOMETRICSPY_INSTALLER_APP_VERSION -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_INSTALLER_APP_VERSION = $OldAppVersionEnv }
    if ($null -eq $OldFileVersionEnv) { Remove-Item Env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION = $OldFileVersionEnv }
}

$Installer = Join-Path $InstallerOutput "gpbiometricspy-studio-setup.exe"
if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) { throw "Upgrade-policy installer was not created." }
if ([string](Get-AuthenticodeSignature -LiteralPath $Installer).Status -ne "NotSigned") { throw "Upgrade-policy proof installer must remain unsigned." }
$InstallerSha256 = Get-Sha256 $Installer
$InstalledExecutable = Join-Path $InstallRoot "gpbiometricspy-studio-native.exe"

Write-Host "Proving first-install path..."
$FirstProcess = Invoke-SilentSetup -Installer $Installer -LogPath $FirstInstallLog -Directory $InstallRoot
if ($FirstProcess.ExitCode -ne 0) { throw "First install failed with exit code $($FirstProcess.ExitCode)." }
$FirstText = Read-Log $FirstInstallLog
if ($FirstText -notmatch "Upgrade policy: first install allowed") { throw "First-install log missed upgrade-policy evidence." }
if (-not (Test-Path -LiteralPath $InstalledExecutable -PathType Leaf)) { throw "First install did not create the custom-path executable." }
Assert-SourceBytesRestored -Executable $InstalledExecutable -ExpectedSha256 $SourceExecutableSha256 -Context "First install"
if ((Get-UpgradeMarker) -ne $TargetFileVersion) { throw "First install did not persist the numeric file-version marker." }

Write-Host "Proving migration fallback for an installation that predates the registry marker..."
Remove-ItemProperty -LiteralPath $UpgradePolicyKey -Name $UpgradePolicyValue -ErrorAction Stop
[System.IO.File]::AppendAllText($InstalledExecutable, "fallback-repair-sentinel")
if ((Get-Sha256 $InstalledExecutable) -eq $SourceExecutableSha256) { throw "Fallback-repair sentinel did not alter installed bytes." }
$FallbackProcess = Invoke-SilentSetup -Installer $Installer -LogPath $FallbackRepairLog
if ($FallbackProcess.ExitCode -ne 0) { throw "Fallback same-version repair failed with exit code $($FallbackProcess.ExitCode)." }
$FallbackText = Read-Log $FallbackRepairLog
if ($FallbackText -notmatch "Upgrade policy: same-version repair allowed") { throw "Fallback repair log missed same-version policy evidence." }
if ($FallbackText -notmatch "source=executable") { throw "Fallback repair did not derive version from the installed executable." }
Assert-SourceBytesRestored -Executable $InstalledExecutable -ExpectedSha256 $SourceExecutableSha256 -Context "Fallback same-version repair"
if ((Get-UpgradeMarker) -ne $TargetFileVersion) { throw "Fallback repair did not migrate the numeric registry marker." }

Write-Host "Proving same-version repair from the persisted registry marker..."
[System.IO.File]::AppendAllText($InstalledExecutable, "registry-repair-sentinel")
if ((Get-Sha256 $InstalledExecutable) -eq $SourceExecutableSha256) { throw "Registry-repair sentinel did not alter installed bytes." }
$RegistryRepairProcess = Invoke-SilentSetup -Installer $Installer -LogPath $RegistryRepairLog
if ($RegistryRepairProcess.ExitCode -ne 0) { throw "Registry same-version repair failed with exit code $($RegistryRepairProcess.ExitCode)." }
$RegistryRepairText = Read-Log $RegistryRepairLog
if ($RegistryRepairText -notmatch "Upgrade policy: same-version repair allowed") { throw "Registry repair log missed same-version policy evidence." }
if ($RegistryRepairText -notmatch "source=registry") { throw "Registry repair did not use the persisted version marker." }
Assert-SourceBytesRestored -Executable $InstalledExecutable -ExpectedSha256 $SourceExecutableSha256 -Context "Registry same-version repair"

Write-Host "Proving an in-place upgrade from the previous numeric file-version line..."
Set-ItemProperty -LiteralPath $UpgradePolicyKey -Name $UpgradePolicyValue -Value $PreviousFileVersion
[System.IO.File]::AppendAllText($InstalledExecutable, "upgrade-sentinel")
if ((Get-Sha256 $InstalledExecutable) -eq $SourceExecutableSha256) { throw "Upgrade sentinel did not alter installed bytes." }
$UpgradeProcess = Invoke-SilentSetup -Installer $Installer -LogPath $UpgradeLog
if ($UpgradeProcess.ExitCode -ne 0) { throw "Simulated in-place upgrade failed with exit code $($UpgradeProcess.ExitCode)." }
$UpgradeText = Read-Log $UpgradeLog
if ($UpgradeText -notmatch "Upgrade policy: in-place upgrade allowed") { throw "Upgrade log missed in-place upgrade evidence." }
if ($UpgradeText -notmatch [regex]::Escape("installed=$PreviousFileVersion")) { throw "Upgrade log did not record the previous numeric version." }
Assert-SourceBytesRestored -Executable $InstalledExecutable -ExpectedSha256 $SourceExecutableSha256 -Context "In-place upgrade"
if ((Get-UpgradeMarker) -ne $TargetFileVersion) { throw "In-place upgrade did not rewrite the target numeric version marker." }

Write-Host "Proving a downgrade from a newer numeric file-version line is blocked before payload mutation..."
Set-ItemProperty -LiteralPath $UpgradePolicyKey -Name $UpgradePolicyValue -Value $FutureFileVersion
$BeforeDowngradeSha256 = Get-Sha256 $InstalledExecutable
$DowngradeProcess = Invoke-SilentSetup -Installer $Installer -LogPath $DowngradeLog
if ($DowngradeProcess.ExitCode -ne 7) { throw "Downgrade must fail with setup exit code 7; got $($DowngradeProcess.ExitCode)." }
$DowngradeText = Read-Log $DowngradeLog
if ($DowngradeText -notmatch "Upgrade policy: downgrade blocked") { throw "Downgrade log missed fail-closed policy evidence." }
if ($DowngradeText -notmatch [regex]::Escape("installed=$FutureFileVersion")) { throw "Downgrade log did not record the simulated newer version." }
if ((Get-Sha256 $InstalledExecutable) -ne $BeforeDowngradeSha256) { throw "Blocked downgrade mutated the installed executable." }
if ((Get-UpgradeMarker) -ne $FutureFileVersion) { throw "Blocked downgrade mutated the installed version marker." }

Set-ItemProperty -LiteralPath $UpgradePolicyKey -Name $UpgradePolicyValue -Value $TargetFileVersion
$Uninstaller = Join-Path $InstallRoot "unins000.exe"
if (-not (Test-Path -LiteralPath $Uninstaller -PathType Leaf)) { throw "Upgrade-policy uninstaller is missing." }
$UninstallArgs = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=`"$UninstallLog`"")
$UninstallProcess = Start-Process -FilePath $Uninstaller -ArgumentList $UninstallArgs -Wait -PassThru
if ($UninstallProcess.ExitCode -ne 0) { throw "Upgrade-policy uninstall failed with exit code $($UninstallProcess.ExitCode)." }
Start-Sleep -Seconds 2
if (Test-Path -LiteralPath $UninstallKey) { throw "Upgrade-policy uninstall registration survived uninstall." }
if (Test-Path -LiteralPath $UpgradePolicyKey) { throw "Private upgrade-policy registry key survived uninstall." }
if (Test-Path -LiteralPath $StartMenuShortcut) { throw "Upgrade-policy Start Menu shortcut survived uninstall." }
if (Test-Path -LiteralPath $DesktopShortcut) { throw "Upgrade-policy desktop shortcut survived uninstall." }
$ResidualFiles = @()
if (Test-Path -LiteralPath $InstallRoot) {
    $ResidualFiles = @(Get-ChildItem -LiteralPath $InstallRoot -Recurse -Force -File -ErrorAction SilentlyContinue)
}
if ($ResidualFiles.Count -ne 0) { throw "Upgrade-policy payload files survived uninstall: $($ResidualFiles.Count)." }

$Metrics = [ordered]@{
    schema = "gpbiometricspy-studio-upgrade-policy-readiness"
    schema_version = 1
    release_artifact = $false
    installer_published = $false
    installer_signed = $false
    install_scope = "current-user"
    elevation_required = $false
    app_id = $AppId
    upgrade_policy = "numeric-file-version-fail-closed"
    version_authority = "windows-fixed-file-version"
    target_file_version = $TargetFileVersion
    migration_fallback = "installed-executable-fixed-version"
    first_install_allowed = $true
    custom_install_path_preserved = $true
    migration_fallback_repair_allowed = $true
    migration_fallback_repair_restored_bytes = $true
    same_version_repair_allowed = $true
    same_version_repair_restored_bytes = $true
    upgrade_allowed = $true
    upgrade_from = $PreviousFileVersion
    upgrade_to = $TargetFileVersion
    upgrade_restored_source_bytes = $true
    downgrade_blocked = $true
    downgrade_from = $FutureFileVersion
    downgrade_to = $TargetFileVersion
    downgrade_exit_code = $DowngradeProcess.ExitCode
    downgrade_payload_unchanged = $true
    downgrade_marker_unchanged = $true
    upgrade_registry_removed_on_uninstall = $true
    uninstall_registration_removed = $true
    payload_files_removed = $true
    installer_sha256 = $InstallerSha256
    source_executable_sha256 = $SourceExecutableSha256
    installer_tool = "Inno Setup"
    installer_tool_version = $InnoVersion
    python_version = ((& $VenvPython --version 2>&1) | Out-String).Trim()
    pyinstaller_version = ((& $VenvPython -m PyInstaller --version 2>&1) | Out-String).Trim()
    pywebview_version = ((& $VenvPython -c "import importlib.metadata as m; print(m.version('pywebview'))" 2>&1) | Out-String).Trim()
}
$Metrics | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $MetricsPath -Encoding UTF8

Remove-Item -LiteralPath $WorkRoot -Recurse -Force -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath $WorkRoot) { throw "Upgrade-policy transient work root survived cleanup." }
if (Get-ChildItem -LiteralPath $EvidenceDir -Recurse -File -Include "*.exe", "*.dll", "*.pfx", "*.p12" -ErrorAction SilentlyContinue) {
    throw "Upgrade-policy evidence must contain diagnostics only."
}

Write-Host "Studio upgrade policy proof passed: first install, migration fallback, same-version repair, in-place upgrade, fail-closed downgrade, and uninstall cleanup verified."
