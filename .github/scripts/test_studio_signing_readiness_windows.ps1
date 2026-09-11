param(
    [string]$Python = "python",
    [string]$ArtifactsDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $ArtifactsDir) {
    $ArtifactsDir = Join-Path ([System.IO.Path]::GetTempPath()) ("gpbiometricspy-signing-readiness-" + [guid]::NewGuid().ToString("N"))
}
$ArtifactsDir = [System.IO.Path]::GetFullPath($ArtifactsDir)
$BuildArtifacts = Join-Path $ArtifactsDir "native-build"
$SigningDir = Join-Path $ArtifactsDir "signing"
$ManifestPath = Join-Path $SigningDir "signing-provenance.json"
$VerifyLog = Join-Path $SigningDir "signtool-verify.log"
$IdentityVerifier = Join-Path $RepoRoot ".github/scripts/assert_studio_windows_identity.ps1"

New-Item -ItemType Directory -Force -Path $SigningDir | Out-Null

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Find-SignTool {
    $KitsRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    if (-not (Test-Path -LiteralPath $KitsRoot -PathType Container)) {
        return $null
    }
    $Candidate = Get-ChildItem -LiteralPath $KitsRoot -Recurse -File -Filter "signtool.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "\\x64\\signtool\.exe$" } |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if ($null -eq $Candidate) { return $null }
    return $Candidate.FullName
}

function Remove-TestCertificate {
    param([System.Security.Cryptography.X509Certificates.X509Certificate2]$Certificate)
    if ($null -eq $Certificate) { return }
    foreach ($StoreName in @("My", "Root", "TrustedPublisher")) {
        $Store = [System.Security.Cryptography.X509Certificates.X509Store]::new($StoreName, "CurrentUser")
        try {
            $Store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
            $Matches = @($Store.Certificates | Where-Object { $_.Thumbprint -eq $Certificate.Thumbprint })
            foreach ($Match in $Matches) { $Store.Remove($Match) }
        }
        finally {
            $Store.Close()
            $Store.Dispose()
        }
    }
}

Write-Host "Building and validating the unsigned native Studio candidate first..."
& (Join-Path $RepoRoot ".github/scripts/test_studio_pyinstaller_native_windows.ps1") `
    -Python $Python `
    -ArtifactsDir $BuildArtifacts
if ($LASTEXITCODE -ne 0) { throw "Unsigned native Studio baseline did not pass before signing readiness." }

$Executable = Join-Path $BuildArtifacts "dist/gpbiometricspy-studio-native/gpbiometricspy-studio-native.exe"
$IdentityJson = Join-Path $BuildArtifacts "identity/windows-identity.json"
$IconPath = Join-Path $BuildArtifacts "identity/gpbiometricspy-studio.ico"
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { throw "Unsigned native executable not found: $Executable" }

$BeforeSignature = Get-AuthenticodeSignature -LiteralPath $Executable
if ($BeforeSignature.Status -ne [System.Management.Automation.SignatureStatus]::NotSigned) {
    throw "Signing-readiness input must be unsigned; got Authenticode status $($BeforeSignature.Status)."
}

$UnsignedSha256 = Get-Sha256 $Executable
$UnsignedBytes = [int64](Get-Item -LiteralPath $Executable).Length
$IdentityManifestSha256 = Get-Sha256 $IdentityJson
Write-Host "Unsigned SHA-256: $UnsignedSha256"

$Certificate = $null
$Signed = $false
try {
    $Certificate = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject "CN=gpbiometricspy Studio CI Test Signing" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -HashAlgorithm "SHA256" `
        -NotAfter (Get-Date).AddDays(1)

    if ($null -eq $Certificate -or -not $Certificate.HasPrivateKey) {
        throw "Failed to create the ephemeral CI code-signing certificate."
    }

    # Trust only this ephemeral public certificate in the current-user stores so
    # Authenticode verification can exercise the full trusted-signature path.
    foreach ($StoreName in @("Root", "TrustedPublisher")) {
        $Store = [System.Security.Cryptography.X509Certificates.X509Store]::new($StoreName, "CurrentUser")
        try {
            $Store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
            $Store.Add($Certificate)
        }
        finally {
            $Store.Close()
            $Store.Dispose()
        }
    }

    Write-Host "Applying ephemeral test-only Authenticode signature with SHA-256..."
    $Applied = Set-AuthenticodeSignature `
        -LiteralPath $Executable `
        -Certificate $Certificate `
        -HashAlgorithm SHA256
    if ($Applied.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
        throw "Set-AuthenticodeSignature did not produce a valid trusted test signature: $($Applied.Status) $($Applied.StatusMessage)"
    }
    $Signed = $true

    $AfterSignature = Get-AuthenticodeSignature -LiteralPath $Executable
    if ($AfterSignature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
        throw "Signed native executable failed Authenticode verification: $($AfterSignature.Status) $($AfterSignature.StatusMessage)"
    }
    if ($null -eq $AfterSignature.SignerCertificate) { throw "Signed executable has no signer certificate metadata." }
    if ($AfterSignature.SignerCertificate.Thumbprint -ne $Certificate.Thumbprint) {
        throw "Signer thumbprint does not match the ephemeral CI signing certificate."
    }

    $SignedSha256 = Get-Sha256 $Executable
    $SignedBytes = [int64](Get-Item -LiteralPath $Executable).Length
    if ($SignedSha256 -eq $UnsignedSha256) { throw "Authenticode signing did not change the executable SHA-256." }

    # Signing must not alter the already-certified PE identity/icon resources.
    & $IdentityVerifier -Executable $Executable -IdentityJson $IdentityJson -IconPath $IconPath
    if ($LASTEXITCODE -ne 0) { throw "Windows application identity changed after Authenticode signing." }

    $SignTool = Find-SignTool
    $SignToolVerified = $false
    if ($null -ne $SignTool) {
        Write-Host "Verifying the test signature with Windows SignTool /pa..."
        & $SignTool verify /pa /v $Executable 2>&1 | Tee-Object -FilePath $VerifyLog
        if ($LASTEXITCODE -ne 0) { throw "SignTool Authenticode verification failed with exit code $LASTEXITCODE." }
        $SignToolVerified = $true
    }
    else {
        "SignTool not found on runner; PowerShell Authenticode verification was still required and passed." | Set-Content -LiteralPath $VerifyLog -Encoding UTF8
    }

    $Manifest = [ordered]@{
        schema = "gpbiometricspy-studio-signing-provenance"
        schema_version = 1
        test_only = $true
        release_artifact = $false
        certificate_ephemeral = $true
        certificate_persisted = $false
        timestamped = $false
        production_timestamp_required = $true
        production_digest_algorithm = "SHA256"
        production_timestamp_digest_algorithm = "SHA256"
        unsigned_sha256 = $UnsignedSha256
        signed_sha256 = $SignedSha256
        unsigned_bytes = $UnsignedBytes
        signed_bytes = $SignedBytes
        identity_manifest_sha256 = $IdentityManifestSha256
        signature_status = [string]$AfterSignature.Status
        signer_subject = $AfterSignature.SignerCertificate.Subject
        signer_thumbprint = $AfterSignature.SignerCertificate.Thumbprint
        signer_not_after_utc = $AfterSignature.SignerCertificate.NotAfter.ToUniversalTime().ToString("o")
        signtool_verified = $SignToolVerified
        executable_name = [System.IO.Path]::GetFileName($Executable)
    }
    $Manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
    Write-Host "Signing readiness proof passed. Signed SHA-256: $SignedSha256"
}
finally {
    if ($null -ne $Certificate) {
        Remove-TestCertificate $Certificate
    }
}

if (-not $Signed) { throw "Signing readiness did not reach a signed state." }

# Fail closed if the ephemeral certificate survived cleanup in any tested store.
foreach ($StoreName in @("My", "Root", "TrustedPublisher")) {
    $Store = [System.Security.Cryptography.X509Certificates.X509Store]::new($StoreName, "CurrentUser")
    try {
        $Store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
        if (@($Store.Certificates | Where-Object { $_.Thumbprint -eq $Certificate.Thumbprint }).Count -ne 0) {
            throw "Ephemeral CI certificate was not removed from CurrentUser/$StoreName."
        }
    }
    finally {
        $Store.Close()
        $Store.Dispose()
    }
}

Write-Host "Ephemeral signing certificate cleanup verified."
