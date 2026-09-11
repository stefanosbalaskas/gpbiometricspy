param(
    [string]$Python = "python",
    [string]$ArtifactsDir = "",
    [Parameter(Mandatory = $true)][string]$SourceCommit
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path ([System.IO.Path]::GetTempPath()) ("gpbiometricspy-release-provenance-" + [guid]::NewGuid().ToString("N"))
}
$ArtifactsDir = [System.IO.Path]::GetFullPath($ArtifactsDir)
$EvidenceDir = Join-Path $ArtifactsDir "evidence"
$BuildRoot = Join-Path $ArtifactsDir "build"
$DistRoot = Join-Path $ArtifactsDir "dist"
$InstallerOutput = Join-Path $ArtifactsDir "installer-output"
$BuildVenv = Join-Path $ArtifactsDir "build-venv"
$BuildPython = Join-Path $BuildVenv "Scripts/python.exe"
$ToolVenv = Join-Path $ArtifactsDir "provenance-tool-venv"
$ToolPython = Join-Path $ToolVenv "Scripts/python.exe"
$IdentityDir = Join-Path $EvidenceDir "identity"
$IdentityJson = Join-Path $IdentityDir "windows-identity.json"
$IconPath = Join-Path $IdentityDir "gpbiometricspy-studio.ico"
$SbomPath = Join-Path $EvidenceDir "studio-build-environment.cdx.json"
$FreezePath = Join-Path $EvidenceDir "studio-build-environment.freeze.txt"
$PipListPath = Join-Path $EvidenceDir "studio-build-environment.pip-list.json"
$ChecksumsPath = Join-Path $EvidenceDir "SHA256SUMS.txt"
$ProvenancePath = Join-Path $EvidenceDir "release-provenance-readiness.json"
$CompileLog = Join-Path $EvidenceDir "iscc.log"
$SpecPath = Join-Path $RepoRoot "tools/pyinstaller/gpbiometricspy_studio_native_windowed.spec"
$InstallerScript = Join-Path $RepoRoot "tools/installer/gpbiometricspy_studio.iss"
$PackagingRequirements = Join-Path $RepoRoot "tools/pyinstaller/requirements.txt"
$ReleaseRequirements = Join-Path $RepoRoot "tools/release/requirements.txt"
$PyprojectPath = Join-Path $RepoRoot "pyproject.toml"
$IdentityGenerator = Join-Path $RepoRoot "tools/pyinstaller/generate_windows_identity.py"
$IdentityVerifier = Join-Path $RepoRoot ".github/scripts/assert_studio_windows_identity.ps1"
$ThisScript = $MyInvocation.MyCommand.Path

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

function Get-InnoCompilerVersion {
    param([Parameter(Mandatory = $true)][string]$Compiler)

    $RegistryCandidates = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"
    )
    foreach ($Key in $RegistryCandidates) {
        if (-not (Test-Path -LiteralPath $Key)) { continue }
        $DisplayVersion = [string](Get-ItemPropertyValue -LiteralPath $Key -Name "DisplayVersion" -ErrorAction SilentlyContinue)
        if ($DisplayVersion -and $DisplayVersion.Trim() -and $DisplayVersion.Trim() -ne "0.0.0.0") {
            return [pscustomobject]@{ Version = $DisplayVersion.Trim(); Source = "uninstall-registry" }
        }
    }

    $HelpText = (& $Compiler "/?" 2>&1 | Out-String)
    if ($HelpText -match "Inno Setup\s+(?<version>[0-9]+(?:\.[0-9]+)*)\s+Command-Line Compiler") {
        return [pscustomobject]@{ Version = $Matches.version; Source = "iscc-help-banner" }
    }

    throw "Unable to establish an authoritative Inno Setup compiler version."
}

if ($SourceCommit -notmatch "^[0-9a-fA-F]{40}$") {
    throw "SourceCommit must be an exact 40-character Git SHA."
}
foreach ($RequiredPath in @(
    $SpecPath,
    $InstallerScript,
    $PackagingRequirements,
    $ReleaseRequirements,
    $PyprojectPath,
    $IdentityGenerator,
    $IdentityVerifier,
    $ThisScript
)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required release-provenance input is missing: $RequiredPath"
    }
}

$Iscc = Find-InnoCompiler
if ($null -eq $Iscc) { throw "Inno Setup ISCC.exe was not found on the Windows runner." }
$InnoEvidence = Get-InnoCompilerVersion -Compiler $Iscc
$InnoCompilerSha256 = Get-Sha256 $Iscc

Write-Host "Creating exact build environment..."
& $Python -m venv $BuildVenv
if ($LASTEXITCODE -ne 0) { throw "Failed to create build environment." }
& $BuildPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade build-environment pip." }
& $BuildPython -m pip install -e ("{0}[studio-native]" -f $RepoRoot)
if ($LASTEXITCODE -ne 0) { throw "Failed to install gpbiometricspy native Studio dependencies." }
& $BuildPython -m pip install -r $PackagingRequirements
if ($LASTEXITCODE -ne 0) { throw "Failed to install pinned packaging tools." }

Write-Host "Generating Windows identity and transient windowed bundle..."
& $BuildPython $IdentityGenerator --repo-root $RepoRoot --output-dir $IdentityDir --target native
if ($LASTEXITCODE -ne 0) { throw "Failed to generate Windows identity." }
$env:GPBIOMETRICSPY_WINDOWS_IDENTITY_DIR = $IdentityDir
Push-Location $RepoRoot
try {
    & $BuildPython -m PyInstaller --noconfirm --clean --distpath $DistRoot --workpath $BuildRoot $SpecPath
    if ($LASTEXITCODE -ne 0) { throw "Windowed PyInstaller provenance build failed." }
}
finally { Pop-Location }

$BundleRoot = Join-Path $DistRoot "gpbiometricspy-studio-native"
$SourceExecutable = Join-Path $BundleRoot "gpbiometricspy-studio-native.exe"
if (-not (Test-Path -LiteralPath $SourceExecutable -PathType Leaf)) { throw "Windowed source executable is missing." }
& $IdentityVerifier -Executable $SourceExecutable -IdentityJson $IdentityJson -IconPath $IconPath
if ($LASTEXITCODE -ne 0) { throw "Windowed source executable failed Windows identity verification." }
$Identity = Get-Content -LiteralPath $IdentityJson -Raw | ConvertFrom-Json
$SourcePeSubsystem = Get-PeSubsystem -Executable $SourceExecutable
if ($SourcePeSubsystem -ne 2) { throw "Windowed source executable is not IMAGE_SUBSYSTEM_WINDOWS_GUI (2)." }
$SourceExecutableSha256 = Get-Sha256 $SourceExecutable

Write-Host "Compiling transient Inno Setup installer..."
$OldBundleEnv = $env:GPBIOMETRICSPY_INSTALLER_BUNDLE
$OldIconEnv = $env:GPBIOMETRICSPY_INSTALLER_ICON
$OldAppVersionEnv = $env:GPBIOMETRICSPY_INSTALLER_APP_VERSION
$OldFileVersionEnv = $env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION
try {
    $env:GPBIOMETRICSPY_INSTALLER_BUNDLE = $BundleRoot
    $env:GPBIOMETRICSPY_INSTALLER_ICON = $IconPath
    $env:GPBIOMETRICSPY_INSTALLER_APP_VERSION = [string]$Identity.product_version
    $env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION = [string]$Identity.file_version
    $CompileOutput = & $Iscc "/Qp" ("/O{0}" -f $InstallerOutput) $InstallerScript 2>&1
    $CompileExit = $LASTEXITCODE
    $CompileOutput | Set-Content -LiteralPath $CompileLog -Encoding UTF8
    if ($CompileExit -ne 0) { throw "Inno Setup provenance compilation failed with exit code $CompileExit." }
}
finally {
    if ($null -eq $OldBundleEnv) { Remove-Item Env:GPBIOMETRICSPY_INSTALLER_BUNDLE -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_INSTALLER_BUNDLE = $OldBundleEnv }
    if ($null -eq $OldIconEnv) { Remove-Item Env:GPBIOMETRICSPY_INSTALLER_ICON -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_INSTALLER_ICON = $OldIconEnv }
    if ($null -eq $OldAppVersionEnv) { Remove-Item Env:GPBIOMETRICSPY_INSTALLER_APP_VERSION -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_INSTALLER_APP_VERSION = $OldAppVersionEnv }
    if ($null -eq $OldFileVersionEnv) { Remove-Item Env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION -ErrorAction SilentlyContinue } else { $env:GPBIOMETRICSPY_INSTALLER_FILE_VERSION = $OldFileVersionEnv }
}

$Installer = Join-Path $InstallerOutput "gpbiometricspy-studio-setup.exe"
if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) { throw "Transient installer executable was not created." }
if ([string](Get-AuthenticodeSignature -LiteralPath $Installer).Status -ne "NotSigned") {
    throw "Release-provenance readiness installer must remain unsigned."
}
$InstallerSha256 = Get-Sha256 $Installer
$InstallerBytes = [int64](Get-Item -LiteralPath $Installer).Length

Write-Host "Capturing the actual build-environment inventory..."
$Freeze = (& $BuildPython -m pip freeze --all 2>&1 | Out-String).TrimEnd()
if ($LASTEXITCODE -ne 0) { throw "pip freeze failed for the build environment." }
$Freeze + "`n" | Set-Content -LiteralPath $FreezePath -Encoding UTF8
$PipList = (& $BuildPython -m pip list --format=json 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw "pip list failed for the build environment." }
$PipList | Set-Content -LiteralPath $PipListPath -Encoding UTF8
$PipPackages = @(Get-Content -LiteralPath $PipListPath -Raw | ConvertFrom-Json)
if ($PipPackages.Count -lt 10) { throw "Build-environment package inventory is unexpectedly small." }

Write-Host "Creating isolated CycloneDX tooling environment..."
& $Python -m venv $ToolVenv
if ($LASTEXITCODE -ne 0) { throw "Failed to create provenance-tool environment." }
& $ToolPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade provenance-tool pip." }
& $ToolPython -m pip install -r $ReleaseRequirements
if ($LASTEXITCODE -ne 0) { throw "Failed to install pinned release-provenance tooling." }
$CycloneDxVersion = ((& $ToolPython -c "import importlib.metadata as m; print(m.version('cyclonedx-bom'))" 2>&1) | Out-String).Trim()
if ($CycloneDxVersion -ne "7.3.1") { throw "Unexpected cyclonedx-bom version: $CycloneDxVersion" }

$OldPythonPath = $env:PYTHONPATH
$OldPythonHome = $env:PYTHONHOME
$OldVirtualEnv = $env:VIRTUAL_ENV
try {
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
    & $ToolPython -m cyclonedx_py environment `
        --spec-version 1.6 `
        --output-format JSON `
        --output-reproducible `
        --validate `
        --pyproject $PyprojectPath `
        --output-file $SbomPath `
        $BuildPython
    if ($LASTEXITCODE -ne 0) { throw "CycloneDX SBOM generation failed." }
}
finally {
    if ($null -eq $OldPythonPath) { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue } else { $env:PYTHONPATH = $OldPythonPath }
    if ($null -eq $OldPythonHome) { Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue } else { $env:PYTHONHOME = $OldPythonHome }
    if ($null -eq $OldVirtualEnv) { Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue } else { $env:VIRTUAL_ENV = $OldVirtualEnv }
}

if (-not (Test-Path -LiteralPath $SbomPath -PathType Leaf)) { throw "CycloneDX SBOM was not created." }
$Sbom = Get-Content -LiteralPath $SbomPath -Raw | ConvertFrom-Json
if ([string]$Sbom.bomFormat -ne "CycloneDX") { throw "Unexpected SBOM format." }
if ([string]$Sbom.specVersion -ne "1.6") { throw "Unexpected CycloneDX spec version: $($Sbom.specVersion)" }
if ([string]$Sbom.metadata.component.name -ne "gpbiometricspy") { throw "SBOM root component is not gpbiometricspy." }
if ([string]$Sbom.metadata.component.version -ne [string]$Identity.product_version) { throw "SBOM root version does not match Windows product version." }
$SbomComponentNames = @($Sbom.components | ForEach-Object { [string]$_.name })
foreach ($RequiredComponent in @("shiny", "pywebview", "PyInstaller")) {
    if ($SbomComponentNames -notcontains $RequiredComponent) {
        throw "SBOM is missing required build-environment component: $RequiredComponent"
    }
}

$InputHashes = [ordered]@{}
foreach ($Input in @(
    $PyprojectPath,
    $SpecPath,
    $InstallerScript,
    $PackagingRequirements,
    $ReleaseRequirements,
    $IdentityGenerator,
    $IdentityVerifier,
    $ThisScript
)) {
    $Relative = [System.IO.Path]::GetRelativePath($RepoRoot, $Input).Replace("\", "/")
    $InputHashes[$Relative] = Get-Sha256 $Input
}

$IdentityManifestSha256 = Get-Sha256 $IdentityJson
$SbomSha256 = Get-Sha256 $SbomPath
$FreezeSha256 = Get-Sha256 $FreezePath
$PipListSha256 = Get-Sha256 $PipListPath
$ChecksumLines = @(
    "$InstallerSha256  gpbiometricspy-studio-setup.exe",
    "$SourceExecutableSha256  gpbiometricspy-studio-native.exe",
    "$IdentityManifestSha256  identity/windows-identity.json",
    "$SbomSha256  studio-build-environment.cdx.json",
    "$FreezeSha256  studio-build-environment.freeze.txt",
    "$PipListSha256  studio-build-environment.pip-list.json"
)
$ChecksumLines | Set-Content -LiteralPath $ChecksumsPath -Encoding ASCII
$ChecksumsSha256 = Get-Sha256 $ChecksumsPath

$CheckoutSha = ((git -C $RepoRoot rev-parse HEAD 2>&1) | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $CheckoutSha -notmatch "^[0-9a-f]{40}$") { throw "Unable to establish checkout SHA." }

$Provenance = [ordered]@{
    schema = "gpbiometricspy-studio-release-provenance-readiness"
    schema_version = 1
    release_artifact = $false
    published = $false
    signed = $false
    attested = $false
    slsa_claimed = $false
    readiness_only = $true
    source_commit = $SourceCommit.ToLowerInvariant()
    checkout_sha = $CheckoutSha.ToLowerInvariant()
    repository = $env:GITHUB_REPOSITORY
    workflow = $env:GITHUB_WORKFLOW
    github_run_id = $env:GITHUB_RUN_ID
    github_run_number = $env:GITHUB_RUN_NUMBER
    github_run_attempt = $env:GITHUB_RUN_ATTEMPT
    runner_os = $env:RUNNER_OS
    runner_image_os = $env:ImageOS
    product_name = $Identity.product_name
    product_version = $Identity.product_version
    file_version = $Identity.file_version
    artifact_name = "gpbiometricspy-studio-setup.exe"
    artifact_sha256 = $InstallerSha256
    artifact_bytes = $InstallerBytes
    source_executable_sha256 = $SourceExecutableSha256
    source_pe_subsystem = $SourcePeSubsystem
    pe_subsystem_name = "IMAGE_SUBSYSTEM_WINDOWS_GUI"
    installer_tool = "Inno Setup"
    installer_tool_version = $InnoEvidence.Version
    installer_tool_version_source = $InnoEvidence.Source
    installer_compiler_sha256 = $InnoCompilerSha256
    python_version = ((& $BuildPython --version 2>&1) | Out-String).Trim()
    pyinstaller_version = ((& $BuildPython -m PyInstaller --version 2>&1) | Out-String).Trim()
    pywebview_version = ((& $BuildPython -c "import importlib.metadata as m; print(m.version('pywebview'))" 2>&1) | Out-String).Trim()
    cyclonedx_bom_version = $CycloneDxVersion
    cyclonedx_spec_version = "1.6"
    cyclonedx_output_reproducible = $true
    cyclonedx_validation_enabled = $true
    sbom_target = "actual-build-venv"
    sbom_environment_pollution_mitigation = @("PYTHONPATH-cleared", "PYTHONHOME-cleared", "VIRTUAL_ENV-cleared")
    sbom_component_count = $SbomComponentNames.Count
    sbom_sha256 = $SbomSha256
    pip_freeze_sha256 = $FreezeSha256
    pip_list_sha256 = $PipListSha256
    checksums_algorithm = "SHA256"
    checksums_sha256 = $ChecksumsSha256
    identity_manifest_sha256 = $IdentityManifestSha256
    build_input_sha256 = $InputHashes
    production_signing_required = $true
    production_timestamp_required = $true
    production_release_attestation_required = $true
    production_release_attestation_policy = "Attest the actual published artifact in the release workflow; do not attest this readiness-only CI build."
    production_release_sbom_required = $true
    production_release_checksums_required = $true
    readiness_oidc_used = $false
    readiness_attestation_permissions_used = $false
    binary_retained_as_evidence = $false
}
$Provenance | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ProvenancePath -Encoding UTF8

Remove-Item -LiteralPath $InstallerOutput -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $DistRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $BuildRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $BuildVenv -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $ToolVenv -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item Env:GPBIOMETRICSPY_WINDOWS_IDENTITY_DIR -ErrorAction SilentlyContinue

foreach ($Path in @($InstallerOutput, $DistRoot, $BuildRoot, $BuildVenv, $ToolVenv)) {
    if (Test-Path -LiteralPath $Path) { throw "Transient release-provenance path survived cleanup: $Path" }
}
if (Get-ChildItem -LiteralPath $EvidenceDir -Recurse -File -Include "*.exe", "*.pfx", "*.p12" -ErrorAction SilentlyContinue) {
    throw "Release-provenance evidence must not retain executables or signing-key material."
}

Write-Host "Release-provenance readiness proof passed: exact source identity, transient installer SHA-256, actual build-environment inventory, CycloneDX SBOM, input hashes, and binary-free evidence verified."
