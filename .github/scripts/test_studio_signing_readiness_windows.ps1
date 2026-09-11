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
$SignLog = Join-Path $SigningDir "signtool-sign.log"
$PfxPath = Join-Path $SigningDir "ephemeral-test-signing.pfx"
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

function Invoke-BoundedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$StdoutPath,
        [Parameter(Mandatory = $true)][string]$StderrPath,
        [int]$TimeoutSeconds = 60
    )

    Remove-Item -LiteralPath $StdoutPath, $StderrPath -Force -ErrorAction SilentlyContinue
    $Process = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -PassThru `
        -RedirectStandardOutput $StdoutPath -RedirectStandardError $StderrPath
    try {
        if (-not $Process.WaitForExit($TimeoutSeconds * 1000)) {
            Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
            throw "Process timed out after $TimeoutSeconds seconds: $FilePath $($ArgumentList -join ' ')"
        }
        $Process.Refresh()
        $Stdout = if (Test-Path -LiteralPath $StdoutPath) { Get-Content -LiteralPath $StdoutPath -Raw } else { "" }
        $Stderr = if (Test-Path -LiteralPath $StderrPath) { Get-Content -LiteralPath $StderrPath -Raw } else { "" }
        if ($Stdout) { Write-Host $Stdout.TrimEnd() }
        if ($Stderr) { Write-Host $Stderr.TrimEnd() }
        return [pscustomobject]@{
            ExitCode = $Process.ExitCode
            Stdout = $Stdout
            Stderr = $Stderr
        }
    }
    finally {
        $Process.Dispose()
    }
}

function Get-BoundedAuthenticodeSnapshot {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$TimeoutSeconds = 30
    )

    $Job = Start-Job -ScriptBlock {
        param($TargetPath)
        $Signature = Get-AuthenticodeSignature -LiteralPath $TargetPath
        [pscustomobject]@{
            Status = [string]$Signature.Status
            StatusMessage = [string]$Signature.StatusMessage
            SignerSubject = if ($null -ne $Signature.SignerCertificate) { $Signature.SignerCertificate.Subject } else { $null }
            SignerThumbprint = if ($null -ne $Signature.SignerCertificate) { $Signature.SignerCertificate.Thumbprint } else { $null }
            SignerNotAfterUtc = if ($null -ne $Signature.SignerCertificate) { $Signature.SignerCertificate.NotAfter.ToUniversalTime().ToString("o") } else { $null }
        }
    } -ArgumentList $Path
    try {
        if ($null -eq (Wait-Job -Job $Job -Timeout $TimeoutSeconds)) {
            Stop-Job -Job $Job -ErrorAction SilentlyContinue
            throw "Get-AuthenticodeSignature timed out after $TimeoutSeconds seconds for $Path"
        }
        if ($Job.State -ne "Completed") {
            $Reason = if ($null -ne $Job.ChildJobs[0].JobStateInfo.Reason) { $Job.ChildJobs[0].JobStateInfo.Reason.Message } else { $Job.State }
            throw "Get-AuthenticodeSignature job did not complete successfully: $Reason"
        }
        $Result = Receive-Job -Job $Job
        if ($null -eq $Result) { throw "Get-AuthenticodeSignature returned no result for $Path" }
        return $Result
    }
    finally {
        Remove-Job -Job $Job -Force -ErrorAction SilentlyContinue
    }
}

function New-EphemeralCodeSigningCertificate {
    # Build the one-day CI certificate entirely in memory. It is intentionally
    # never written to a Windows trust store: CI proves signing mechanics and
    # file/signature binding without installing a fake root CA on the runner.
    $Rsa = [System.Security.Cryptography.RSA]::Create(3072)
    try {
        $Request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new(
            "CN=gpbiometricspy Studio CI Test Signing",
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
            throw "Failed to create an in-memory ephemeral CI code-signing certificate."
        }
        return [pscustomobject]@{
            Certificate = $Certificate
            Rsa = $Rsa
        }
    }
    catch {
        $Rsa.Dispose()
        throw
    }
}

function Assert-CustomCertificateChain {
    param([System.Security.Cryptography.X509Certificates.X509Certificate2]$Certificate)

    $Chain = [System.Security.Cryptography.X509Certificates.X509Chain]::new()
    try {
        $Chain.ChainPolicy.TrustMode = [System.Security.Cryptography.X509Certificates.X509ChainTrustMode]::CustomRootTrust
        $Chain.ChainPolicy.RevocationMode = [System.Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
        [void]$Chain.ChainPolicy.CustomTrustStore.Add($Certificate)
        if (-not $Chain.Build($Certificate)) {
            $Statuses = @($Chain.ChainStatus | ForEach-Object { $_.Status.ToString() }) -join ", "
            throw "Ephemeral code-signing certificate failed in-memory custom-root validation: $Statuses"
        }
    }
    finally {
        $Chain.Dispose()
    }
}

$SignTool = Find-SignTool
if ($null -eq $SignTool) {
    throw "Windows SignTool was not found; signing readiness requires the production-class Authenticode toolchain."
}
Write-Host "Using SignTool: $SignTool"

Write-Host "Building and validating the unsigned native Studio candidate first..."
& (Join-Path $RepoRoot ".github/scripts/test_studio_pyinstaller_native_windows.ps1") `
    -Python $Python `
    -ArtifactsDir $BuildArtifacts
if ($LASTEXITCODE -ne 0) { throw "Unsigned native Studio baseline did not pass before signing readiness." }

$Executable = Join-Path $BuildArtifacts "dist/gpbiometricspy-studio-native/gpbiometricspy-studio-native.exe"
$IdentityJson = Join-Path $BuildArtifacts "identity/windows-identity.json"
$IconPath = Join-Path $BuildArtifacts "identity/gpbiometricspy-studio.ico"
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { throw "Unsigned native executable not found: $Executable" }

$BeforeSignature = Get-BoundedAuthenticodeSnapshot -Path $Executable -TimeoutSeconds 30
if ($BeforeSignature.Status -ne "NotSigned") {
    throw "Signing-readiness input must be unsigned; got Authenticode status $($BeforeSignature.Status)."
}

$UnsignedSha256 = Get-Sha256 $Executable
$UnsignedBytes = [int64](Get-Item -LiteralPath $Executable).Length
$IdentityManifestSha256 = Get-Sha256 $IdentityJson
Write-Host "Unsigned SHA-256: $UnsignedSha256"

$CertificateBundle = $null
$Certificate = $null
$CertificateThumbprint = $null
$PfxPassword = [guid]::NewGuid().ToString("N")
$Signed = $false
try {
    Write-Host "Creating in-memory ephemeral CI code-signing certificate..."
    $CertificateBundle = New-EphemeralCodeSigningCertificate
    $Certificate = $CertificateBundle.Certificate
    $CertificateThumbprint = $Certificate.Thumbprint
    Assert-CustomCertificateChain $Certificate
    Write-Host "Ephemeral certificate created and validated in memory: $CertificateThumbprint"

    [System.IO.File]::WriteAllBytes(
        $PfxPath,
        $Certificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Pfx, $PfxPassword)
    )

    Write-Host "Applying ephemeral test-only Authenticode signature with SignTool /fd SHA256..."
    $SignStderr = Join-Path $SigningDir "signtool-sign-stderr.log"
    $SignResult = Invoke-BoundedProcess -FilePath $SignTool `
        -ArgumentList @("sign", "/fd", "SHA256", "/f", $PfxPath, "/p", $PfxPassword, $Executable) `
        -StdoutPath $SignLog -StderrPath $SignStderr -TimeoutSeconds 60
    if ($SignResult.ExitCode -ne 0) { throw "SignTool signing failed with exit code $($SignResult.ExitCode)." }
    $Signed = $true

    $AfterSignature = Get-BoundedAuthenticodeSnapshot -Path $Executable -TimeoutSeconds 30
    $AllowedStatuses = @("Valid", "NotTrusted", "UnknownError")
    if ($AfterSignature.Status -notin $AllowedStatuses) {
        throw "Signed native executable has an invalid Authenticode state: $($AfterSignature.Status) $($AfterSignature.StatusMessage)"
    }
    if ($AfterSignature.Status -eq "UnknownError" -and $AfterSignature.StatusMessage -notmatch "(?i)(not trusted|certificate chain|root certificate|trust provider)") {
        throw "Unexpected Authenticode verification error for test certificate: $($AfterSignature.StatusMessage)"
    }
    if (-not $AfterSignature.SignerThumbprint) { throw "Signed executable has no signer certificate metadata." }
    if ($AfterSignature.SignerThumbprint -ne $CertificateThumbprint) {
        throw "Signer thumbprint does not match the ephemeral CI signing certificate."
    }

    $SignedSha256 = Get-Sha256 $Executable
    $SignedBytes = [int64](Get-Item -LiteralPath $Executable).Length
    if ($SignedSha256 -eq $UnsignedSha256) { throw "Authenticode signing did not change the executable SHA-256." }

    & $IdentityVerifier -Executable $Executable -IdentityJson $IdentityJson -IconPath $IconPath
    if ($LASTEXITCODE -ne 0) { throw "Windows application identity changed after Authenticode signing." }

    Write-Host "Running SignTool policy verification; the ephemeral self-signed certificate is intentionally not trusted by the runner..."
    $VerifyStderr = Join-Path $SigningDir "signtool-verify-stderr.log"
    $VerifyResult = Invoke-BoundedProcess -FilePath $SignTool `
        -ArgumentList @("verify", "/pa", "/v", $Executable) `
        -StdoutPath $VerifyLog -StderrPath $VerifyStderr -TimeoutSeconds 60
    $VerifyText = (($VerifyResult.Stdout + "`n" + $VerifyResult.Stderr).Trim())
    $SignToolTrustResult = if ($VerifyResult.ExitCode -eq 0) { "trusted" } else { "expected-untrusted-test-certificate" }
    if ($VerifyResult.ExitCode -ne 0) {
        if ($VerifyText -match "(?i)hash mismatch") {
            throw "SignTool reported an Authenticode hash mismatch."
        }
        if ($VerifyText -notmatch "(?i)(not trusted|certificate chain|root certificate|trust provider|unknown certificate authority)") {
            throw "SignTool verification failed for a reason other than the expected untrusted ephemeral certificate (exit $($VerifyResult.ExitCode))."
        }
        Write-Host "SignTool reached the expected trust boundary for the self-signed CI certificate."
    }

    $Manifest = [ordered]@{
        schema = "gpbiometricspy-studio-signing-provenance"
        schema_version = 4
        test_only = $true
        release_artifact = $false
        certificate_ephemeral = $true
        certificate_persisted = $false
        trust_store_mutated = $false
        test_certificate_trusted = ($AfterSignature.Status -eq "Valid")
        production_trusted_certificate_required = $true
        timestamped = $false
        production_timestamp_required = $true
        production_digest_algorithm = "SHA256"
        production_timestamp_digest_algorithm = "SHA256"
        signing_tool = "signtool"
        bounded_process_seconds = 60
        bounded_authenticode_seconds = 30
        unsigned_sha256 = $UnsignedSha256
        signed_sha256 = $SignedSha256
        unsigned_bytes = $UnsignedBytes
        signed_bytes = $SignedBytes
        identity_manifest_sha256 = $IdentityManifestSha256
        signature_status = $AfterSignature.Status
        signature_status_message = $AfterSignature.StatusMessage
        signer_subject = $AfterSignature.SignerSubject
        signer_thumbprint = $AfterSignature.SignerThumbprint
        signer_not_after_utc = $AfterSignature.SignerNotAfterUtc
        signtool_verify_exit_code = $VerifyResult.ExitCode
        signtool_trust_result = $SignToolTrustResult
        signer_identity_match = $true
        executable_name = [System.IO.Path]::GetFileName($Executable)
    }
    $Manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
    Write-Host "Signing readiness proof passed. Signed SHA-256: $SignedSha256"
}
finally {
    if (Test-Path -LiteralPath $PfxPath -PathType Leaf) {
        Remove-Item -LiteralPath $PfxPath -Force
    }
    if ($null -ne $Certificate) {
        $Certificate.Dispose()
    }
    if ($null -ne $CertificateBundle -and $null -ne $CertificateBundle.Rsa) {
        $CertificateBundle.Rsa.Dispose()
    }
}

if (-not $Signed) { throw "Signing readiness did not reach a signed state." }
if (Test-Path -LiteralPath $PfxPath -PathType Leaf) { throw "Ephemeral test PFX survived signing cleanup." }
Write-Host "Ephemeral signing PFX cleanup verified; no Windows trust store was modified."
