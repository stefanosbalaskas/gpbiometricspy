param(
    [string]$Python = "python",
    [string]$ArtifactsDir = "",
    [Parameter(Mandatory = $true)][string]$SourceCommit
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path ([System.IO.Path]::GetTempPath()) ("gpbiometricspy-release-orchestration-" + [guid]::NewGuid().ToString("N"))
}
$ArtifactsDir = [System.IO.Path]::GetFullPath($ArtifactsDir)
$EvidenceDir = Join-Path $ArtifactsDir "evidence"
$IdentityDir = Join-Path $EvidenceDir "identity"
$BuildRoot = Join-Path $ArtifactsDir "build"
$DistRoot = Join-Path $ArtifactsDir "dist"
$VenvRoot = Join-Path $ArtifactsDir "venv"
$VenvPython = Join-Path $VenvRoot "Scripts/python.exe"
$InstallerOutput = Join-Path $ArtifactsDir "installer-output"
$InstallRoot = Join-Path $ArtifactsDir "installed\gpbiometricspy Studio"
$SigningRoot = Join-Path $ArtifactsDir "signing"
$PfxPath = Join-Path $SigningRoot "ephemeral-release-orchestration.pfx"
$ManifestPath = Join-Path $EvidenceDir "release-orchestration-readiness.json"
$ChecksumsPath = Join-Path $EvidenceDir "SHA256SUMS.txt"
$CompileLog = Join-Path $EvidenceDir "iscc.log"
$InstallLog = Join-Path $EvidenceDir "install.log"
$UninstallLog = Join-Path $EvidenceDir "uninstall.log"
$ExeSignLog = Join-Path $EvidenceDir "signtool-executable-sign.log"
$InstallerSignLog = Join-Path $EvidenceDir "signtool-installer-sign.log"
$SpecPath = Join-Path $RepoRoot "tools/pyinstaller/gpbiometricspy_studio_native_windowed.spec"
$PackagingRequirements = Join-Path $RepoRoot "tools/pyinstaller/requirements.txt"
$IdentityGenerator = Join-Path $RepoRoot "tools/pyinstaller/generate_windows_identity.py"
$IdentityVerifier = Join-Path $RepoRoot ".github/scripts/assert_studio_windows_identity.ps1"
$InstallerScript = Join-Path $RepoRoot "tools/installer/gpbiometricspy_studio.iss"
$ProvenanceHarness = Join-Path $RepoRoot ".github/scripts/test_studio_release_provenance_windows.ps1"
$ProvenancePolicy = Join-Path $RepoRoot "tests/test_release_provenance_readiness_policy.py"
$ReleaseRequirements = Join-Path $RepoRoot "tools/release/requirements.txt"
$AppId = "fd3ca1af-0ebb-5061-9c59-f7ab1079252e"
$UninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\${AppId}_is1"
$StartMenuShortcut = Join-Path ([Environment]::GetFolderPath("Programs")) "gpbiometricspy Studio.lnk"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "gpbiometricspy Studio.lnk"

New-Item -ItemType Directory -Force -Path $ArtifactsDir, $EvidenceDir, $InstallerOutput, $SigningRoot | Out-Null

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

function Find-SignTool {
    $KitsRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    if (-not (Test-Path -LiteralPath $KitsRoot -PathType Container)) { return $null }
    $Candidates = @(
        Get-ChildItem -LiteralPath $KitsRoot -Directory -ErrorAction SilentlyContinue |
            ForEach-Object {
                $Path = Join-Path $_.FullName "x64\signtool.exe"
                if (Test-Path -LiteralPath $Path -PathType Leaf) { Get-Item -LiteralPath $Path }
            }
    )
    if ($Candidates.Count -eq 0) { return $null }
    return ($Candidates | Sort-Object FullName -Descending | Select-Object -First 1).FullName
}

function New-EphemeralCodeSigningCertificate {
    $Rsa = [System.Security.Cryptography.RSA]::Create(3072)
    try {
        $Request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new(
            "CN=gpbiometricspy Studio Release Orchestration CI",
            $Rsa,
            [System.Security.Cryptography.HashAlgorithmName]::SHA256,
            [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
        )
        $Request.CertificateExtensions.Add(
            [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $true)
        )
        $Request.CertificateExtensions.Add(
            [System.Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new(
                [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature,
                $true
            )
        )
        $EnhancedKeyUsages = [System.Security.Cryptography.OidCollection]::new()
        [void]$EnhancedKeyUsages.Add([System.Security.Cryptography.Oid]::new("1.3.6.1.5.5.7.3.3", "Code Signing"))
        $Request.CertificateExtensions.Add(
            [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($EnhancedKeyUsages, $true)
        )
        $Certificate = $Request.CreateSelfSigned((Get-Date).AddMinutes(-5), (Get-Date).AddDays(1))
        if ($null -eq $Certificate -or -not $Certificate.HasPrivateKey) {
            throw "Failed to create ephemeral release-orchestration certificate."
        }
        return [pscustomobject]@{ Certificate = $Certificate; Rsa = $Rsa }
    }
    catch {
        $Rsa.Dispose()
        throw
    }
}

function Invoke-SignToolSign {
    param(
        [Parameter(Mandatory = $true)][string]$SignTool,
        [Parameter(Mandatory = $true)][string]$Target,
        [Parameter(Mandatory = $true)][string]$Pfx,
        [Parameter(Mandatory = $true)][string]$Password,
        [Parameter(Mandatory = $true)][string]$LogPath
    )
    $ErrorLog = "$LogPath.stderr"
    Remove-Item -LiteralPath $LogPath, $ErrorLog -Force -ErrorAction SilentlyContinue
    $Process = Start-Process -FilePath $SignTool `
        -ArgumentList @("sign", "/fd", "SHA256", "/f", $Pfx, "/p", $Password, $Target) `
        -PassThru -RedirectStandardOutput $LogPath -RedirectStandardError $ErrorLog
    try {
        if (-not $Process.WaitForExit(60000)) {
            Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
            throw "SignTool timed out while signing $Target"
        }
        $Process.Refresh()
        if ($Process.ExitCode -ne 0) {
            $Text = ((Get-Content -LiteralPath $LogPath -Raw -ErrorAction SilentlyContinue) + "`n" + (Get-Content -LiteralPath $ErrorLog -Raw -ErrorAction SilentlyContinue)).Trim()
            throw "SignTool failed with exit code $($Process.ExitCode): $Text"
        }
    }
    finally {
        $Process.Dispose()
    }
}

function Assert-EphemeralSignature {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Thumbprint
    )
    $Signature = Get-AuthenticodeSignature -LiteralPath $Path
    if ($null -eq $Signature.SignerCertificate) { throw "Signed file has no signer certificate: $Path" }
    if ($Signature.SignerCertificate.Thumbprint -ne $Thumbprint) {
        throw "Signer thumbprint mismatch for $Path"
    }
    if ([string]$Signature.Status -notin @("Valid", "NotTrusted", "UnknownError")) {
        throw "Unexpected Authenticode status $($Signature.Status) for $Path"
    }
    if ([string]$Signature.Status -eq "UnknownError" -and [string]$Signature.StatusMessage -notmatch "(?i)(not trusted|certificate chain|root certificate|trust provider|unknown certificate authority)") {
        throw "Unexpected Authenticode verification error for ${Path}: $($Signature.StatusMessage)"
    }
    return [pscustomobject]@{
        Status = [string]$Signature.Status
        StatusMessage = [string]$Signature.StatusMessage
        SignerSubject = [string]$Signature.SignerCertificate.Subject
        SignerThumbprint = [string]$Signature.SignerCertificate.Thumbprint
    }
}

if ($SourceCommit -notmatch "^[0-9a-fA-F]{40}$") { throw "SourceCommit must be an exact 40-character Git SHA." }
$CheckoutSha = (& git -C $RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $CheckoutSha -notmatch "^[0-9a-fA-F]{40}$") { throw "Unable to establish exact checkout SHA." }
if ($CheckoutSha.ToLowerInvariant() -ne $SourceCommit.ToLowerInvariant()) {
    throw "Release orchestration source commit does not match checked-out HEAD."
}

foreach ($RequiredPath in @(
    $SpecPath,
    $PackagingRequirements,
    $IdentityGenerator,
    $IdentityVerifier,
    $InstallerScript,
    $ProvenanceHarness,
    $ProvenancePolicy,
    $ReleaseRequirements
)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) { throw "Required release input is missing: $RequiredPath" }
}
if (Test-Path -LiteralPath $UninstallKey) { throw "Runner is contaminated by an existing gpbiometricspy Studio installation." }

$Iscc = Find-InnoCompiler
if ($null -eq $Iscc) { throw "Inno Setup ISCC.exe was not found." }
$SignTool = Find-SignTool
if ($null -eq $SignTool) { throw "Windows SignTool was not found." }

$CertificateBundle = $null
$Certificate = $null
$PfxPassword = [guid]::NewGuid().ToString("N")
$Installed = $false
$Succeeded = $false
try {
    Write-Host "Creating isolated release-orchestration build environment..."
    & $Python -m venv $VenvRoot
    if ($LASTEXITCODE -ne 0) { throw "Failed to create build environment." }
    & $VenvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }
    & $VenvPython -m pip install -e ("{0}[studio-native]" -f $RepoRoot)
    if ($LASTEXITCODE -ne 0) { throw "Failed to install native Studio dependencies." }
    & $VenvPython -m pip install -r $PackagingRequirements
    if ($LASTEXITCODE -ne 0) { throw "Failed to install pinned packaging tools." }

    Write-Host "Generating exact Windows identity and GUI-subsystem bundle..."
    & $VenvPython $IdentityGenerator --repo-root $RepoRoot --output-dir $IdentityDir --target native
    if ($LASTEXITCODE -ne 0) { throw "Failed to generate Windows identity." }
    $IdentityJson = Join-Path $IdentityDir "windows-identity.json"
    $IconPath = Join-Path $IdentityDir "gpbiometricspy-studio.ico"
    $env:GPBIOMETRICSPY_WINDOWS_IDENTITY_DIR = $IdentityDir
    Push-Location $RepoRoot
    try {
        & $VenvPython -m PyInstaller --noconfirm --clean --distpath $DistRoot --workpath $BuildRoot $SpecPath
        if ($LASTEXITCODE -ne 0) { throw "Windowed PyInstaller build failed." }
    }
    finally { Pop-Location }

    $BundleRoot = Join-Path $DistRoot "gpbiometricspy-studio-native"
    $SourceExecutable = Join-Path $BundleRoot "gpbiometricspy-studio-native.exe"
    if (-not (Test-Path -LiteralPath $SourceExecutable -PathType Leaf)) { throw "Windowed source executable is missing." }
    & $IdentityVerifier -Executable $SourceExecutable -IdentityJson $IdentityJson -IconPath $IconPath
    if ($LASTEXITCODE -ne 0) { throw "Unsigned executable failed Windows identity verification." }
    if ((Get-PeSubsystem -Executable $SourceExecutable) -ne 2) {
        throw "Release-orchestration executable is not IMAGE_SUBSYSTEM_WINDOWS_GUI (2)."
    }
    if ([string](Get-AuthenticodeSignature -LiteralPath $SourceExecutable).Status -ne "NotSigned") {
        throw "Release-orchestration input executable must begin unsigned."
    }

    Write-Host "Creating ephemeral CI signing identity without trust-store mutation..."
    $CertificateBundle = New-EphemeralCodeSigningCertificate
    $Certificate = $CertificateBundle.Certificate
    $CertificateThumbprint = $Certificate.Thumbprint
    [System.IO.File]::WriteAllBytes($PfxPath, $Certificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Pfx, $PfxPassword))

    $UnsignedExecutableSha256 = Get-Sha256 $SourceExecutable
    Invoke-SignToolSign -SignTool $SignTool -Target $SourceExecutable -Pfx $PfxPath -Password $PfxPassword -LogPath $ExeSignLog
    $ExecutableSignature = Assert-EphemeralSignature -Path $SourceExecutable -Thumbprint $CertificateThumbprint
    & $IdentityVerifier -Executable $SourceExecutable -IdentityJson $IdentityJson -IconPath $IconPath
    if ($LASTEXITCODE -ne 0) { throw "Windows application identity changed after executable signing." }
    $SignedExecutableSha256 = Get-Sha256 $SourceExecutable
    if ($SignedExecutableSha256 -eq $UnsignedExecutableSha256) { throw "Executable SHA-256 did not change after Authenticode signing." }

    Write-Host "Compiling installer from the already-signed GUI bundle..."
    $Identity = Get-Content -LiteralPath $IdentityJson -Raw | ConvertFrom-Json
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
    if ([string](Get-AuthenticodeSignature -LiteralPath $Installer).Status -ne "NotSigned") {
        throw "Freshly compiled installer must begin unsigned."
    }
    $UnsignedInstallerSha256 = Get-Sha256 $Installer
    Invoke-SignToolSign -SignTool $SignTool -Target $Installer -Pfx $PfxPath -Password $PfxPassword -LogPath $InstallerSignLog
    $InstallerSignature = Assert-EphemeralSignature -Path $Installer -Thumbprint $CertificateThumbprint
    $SignedInstallerSha256 = Get-Sha256 $Installer
    if ($SignedInstallerSha256 -eq $UnsignedInstallerSha256) { throw "Installer SHA-256 did not change after Authenticode signing." }

    Write-Host "Installing the signed installer and verifying the installed signed executable..."
    $InstallArgs = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOCANCEL", "/SP-", "/DIR=`"$InstallRoot`"", "/LOG=`"$InstallLog`"")
    $InstallProcess = Start-Process -FilePath $Installer -ArgumentList $InstallArgs -Wait -PassThru
    if ($InstallProcess.ExitCode -ne 0) { throw "Signed installer exited with code $($InstallProcess.ExitCode)." }
    $Installed = $true
    $InstalledExecutable = Join-Path $InstallRoot "gpbiometricspy-studio-native.exe"
    if (-not (Test-Path -LiteralPath $InstalledExecutable -PathType Leaf)) { throw "Installed executable is missing." }
    $InstalledExecutableSha256 = Get-Sha256 $InstalledExecutable
    if ($InstalledExecutableSha256 -ne $SignedExecutableSha256) {
        throw "Installed executable is not byte-identical to the signed source executable."
    }
    $InstalledSignature = Assert-EphemeralSignature -Path $InstalledExecutable -Thumbprint $CertificateThumbprint
    & $IdentityVerifier -Executable $InstalledExecutable -IdentityJson $IdentityJson -IconPath $IconPath
    if ($LASTEXITCODE -ne 0) { throw "Installed signed executable failed Windows identity verification." }
    if ((Get-PeSubsystem -Executable $InstalledExecutable) -ne 2) {
        throw "Installed signed executable lost the GUI PE subsystem contract."
    }

    Write-Host "Uninstalling transient signed-chain installation..."
    $Uninstaller = Join-Path $InstallRoot "unins000.exe"
    if (-not (Test-Path -LiteralPath $Uninstaller -PathType Leaf)) { throw "Uninstaller is missing." }
    $UninstallArgs = @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=`"$UninstallLog`"")
    $UninstallProcess = Start-Process -FilePath $Uninstaller -ArgumentList $UninstallArgs -Wait -PassThru
    if ($UninstallProcess.ExitCode -ne 0) { throw "Uninstaller exited with code $($UninstallProcess.ExitCode)." }
    $Installed = $false
    $CleanupDeadline = (Get-Date).AddSeconds(10)
    while ((Get-Date) -lt $CleanupDeadline -and (Test-Path -LiteralPath $InstallRoot)) {
        $ResidualFiles = @(Get-ChildItem -LiteralPath $InstallRoot -Recurse -Force -File -ErrorAction SilentlyContinue)
        if ($ResidualFiles.Count -eq 0) { break }
        Start-Sleep -Milliseconds 250
    }
    if (Test-Path -LiteralPath $UninstallKey) { throw "Uninstall registration survived signed-chain uninstall." }
    $ResidualFiles = @()
    if (Test-Path -LiteralPath $InstallRoot) {
        $ResidualFiles = @(Get-ChildItem -LiteralPath $InstallRoot -Recurse -Force -File -ErrorAction SilentlyContinue)
    }
    if ($ResidualFiles.Count -ne 0) { throw "Installed payload files survived signed-chain uninstall: $($ResidualFiles.FullName -join ', ')" }
    foreach ($Shortcut in @($StartMenuShortcut, $DesktopShortcut)) {
        if (Test-Path -LiteralPath $Shortcut) { throw "Application shortcut survived signed-chain uninstall: $Shortcut" }
    }

    $IdentityManifestSha256 = Get-Sha256 $IdentityJson
    $ContractHashes = [ordered]@{
        provenance_harness_sha256 = Get-Sha256 $ProvenanceHarness
        provenance_policy_sha256 = Get-Sha256 $ProvenancePolicy
        release_requirements_sha256 = Get-Sha256 $ReleaseRequirements
        installer_script_sha256 = Get-Sha256 $InstallerScript
        windowed_spec_sha256 = Get-Sha256 $SpecPath
    }
    @(
        "$SignedExecutableSha256  gpbiometricspy-studio-native.exe",
        "$SignedInstallerSha256  gpbiometricspy-studio-setup.exe",
        "$IdentityManifestSha256  identity/windows-identity.json"
    ) | Set-Content -LiteralPath $ChecksumsPath -Encoding UTF8

    $Manifest = [ordered]@{
        schema = "gpbiometricspy-studio-release-orchestration-readiness"
        schema_version = 1
        source_commit = $SourceCommit.ToLowerInvariant()
        checkout_sha = $CheckoutSha.ToLowerInvariant()
        exact_source_binding = $true
        test_only = $true
        release_artifact = $false
        published = $false
        attested = $false
        certificate_ephemeral = $true
        certificate_persisted = $false
        trust_store_mutated = $false
        timestamped = $false
        production_trusted_certificate_required = $true
        production_timestamp_required = $true
        production_timestamp_digest_algorithm = "SHA256"
        production_release_attestation_required = $true
        production_protected_environment_required = $true
        checksums_algorithm = "SHA256"
        sbom_contract = "CycloneDX 1.6 via studio-release-provenance-readiness"
        provenance_contract_sha256 = $ContractHashes
        identity_manifest_sha256 = $IdentityManifestSha256
        unsigned_executable_sha256 = $UnsignedExecutableSha256
        signed_executable_sha256 = $SignedExecutableSha256
        unsigned_installer_sha256 = $UnsignedInstallerSha256
        signed_installer_sha256 = $SignedInstallerSha256
        installed_executable_sha256 = $InstalledExecutableSha256
        installed_executable_matches_signed_source = $true
        executable_signed_before_installer_compile = $true
        installer_signed_after_compile = $true
        executable_signer_thumbprint = $ExecutableSignature.SignerThumbprint
        installer_signer_thumbprint = $InstallerSignature.SignerThumbprint
        installed_executable_signer_thumbprint = $InstalledSignature.SignerThumbprint
        signer_identity_consistent = ($ExecutableSignature.SignerThumbprint -eq $InstallerSignature.SignerThumbprint -and $InstallerSignature.SignerThumbprint -eq $InstalledSignature.SignerThumbprint)
        executable_signature_status = $ExecutableSignature.Status
        installer_signature_status = $InstallerSignature.Status
        installed_executable_signature_status = $InstalledSignature.Status
        install_verified = $true
        uninstall_verified = $true
        binary_retained_as_evidence = $false
        signing_key_retained_as_evidence = $false
    }
    if (-not $Manifest.signer_identity_consistent) { throw "Signer identity is not consistent across executable, installer, and installed executable." }
    $Manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
    $Succeeded = $true
}
finally {
    if ($Installed -and (Test-Path -LiteralPath (Join-Path $InstallRoot "unins000.exe") -PathType Leaf)) {
        try {
            Start-Process -FilePath (Join-Path $InstallRoot "unins000.exe") -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") -Wait | Out-Null
        }
        catch { Write-Warning "Best-effort uninstall cleanup failed: $($_.Exception.Message)" }
    }
    if (Test-Path -LiteralPath $PfxPath -PathType Leaf) { Remove-Item -LiteralPath $PfxPath -Force -ErrorAction SilentlyContinue }
    if ($null -ne $Certificate) { $Certificate.Dispose() }
    if ($null -ne $CertificateBundle -and $null -ne $CertificateBundle.Rsa) { $CertificateBundle.Rsa.Dispose() }
    foreach ($Shortcut in @($StartMenuShortcut, $DesktopShortcut)) {
        if (Test-Path -LiteralPath $Shortcut) { Remove-Item -LiteralPath $Shortcut -Force -ErrorAction SilentlyContinue }
    }
    foreach ($Transient in @($InstallerOutput, $DistRoot, $BuildRoot, $VenvRoot, $SigningRoot, (Join-Path $ArtifactsDir "installed"))) {
        if (Test-Path -LiteralPath $Transient) { Remove-Item -LiteralPath $Transient -Recurse -Force -ErrorAction SilentlyContinue }
    }
    Remove-Item Env:GPBIOMETRICSPY_WINDOWS_IDENTITY_DIR -ErrorAction SilentlyContinue
}

if (-not $Succeeded) { throw "Release-orchestration readiness did not complete successfully." }
if (Test-Path -LiteralPath $PfxPath -PathType Leaf) { throw "Ephemeral signing PFX survived cleanup." }
if (Test-Path -LiteralPath $UninstallKey) { throw "Uninstall registration survived final cleanup." }
if (Get-ChildItem -LiteralPath $EvidenceDir -Recurse -File -Include "*.exe", "*.dll", "*.pfx", "*.p12", "*.pem", "*.key" -ErrorAction SilentlyContinue) {
    throw "Release-orchestration evidence must not retain redistributable binaries or signing-key material."
}
Write-Host "Release-orchestration readiness passed: transient signed executable -> signed installer -> installed signed executable chain is exact-source/hash bound, cleanly uninstalled, and binary-free in evidence."
