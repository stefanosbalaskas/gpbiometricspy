param(
    [Parameter(Mandatory = $true)][string]$Executable,
    [Parameter(Mandatory = $true)][string]$IdentityJson,
    [Parameter(Mandatory = $true)][string]$IconPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { throw "Executable not found: $Executable" }
if (-not (Test-Path -LiteralPath $IdentityJson -PathType Leaf)) { throw "Identity manifest not found: $IdentityJson" }
if (-not (Test-Path -LiteralPath $IconPath -PathType Leaf)) { throw "Generated icon not found: $IconPath" }

$Expected = Get-Content -LiteralPath $IdentityJson -Raw | ConvertFrom-Json
$Actual = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($Executable)

function Assert-Equal {
    param([string]$Field, $ExpectedValue, $ActualValue)
    if ([string]$ExpectedValue -cne [string]$ActualValue) {
        throw "Windows identity mismatch for $Field. Expected '$ExpectedValue', got '$ActualValue'."
    }
}

Assert-Equal "FileDescription" $Expected.file_description $Actual.FileDescription
Assert-Equal "FileVersion" $Expected.file_version $Actual.FileVersion
Assert-Equal "InternalName" $Expected.internal_name $Actual.InternalName
Assert-Equal "LegalCopyright" $Expected.legal_copyright $Actual.LegalCopyright
Assert-Equal "OriginalFilename" $Expected.original_filename $Actual.OriginalFilename
Assert-Equal "ProductName" $Expected.product_name $Actual.ProductName
Assert-Equal "ProductVersion" $Expected.product_version $Actual.ProductVersion

$Fixed = @($Expected.fixed_file_version)
if ($Fixed.Count -ne 4) { throw "Expected fixed_file_version to contain four integers." }
Assert-Equal "FileMajorPart" $Fixed[0] $Actual.FileMajorPart
Assert-Equal "FileMinorPart" $Fixed[1] $Actual.FileMinorPart
Assert-Equal "FileBuildPart" $Fixed[2] $Actual.FileBuildPart
Assert-Equal "FilePrivatePart" $Fixed[3] $Actual.FilePrivatePart
Assert-Equal "ProductMajorPart" $Fixed[0] $Actual.ProductMajorPart
Assert-Equal "ProductMinorPart" $Fixed[1] $Actual.ProductMinorPart
Assert-Equal "ProductBuildPart" $Fixed[2] $Actual.ProductBuildPart
Assert-Equal "ProductPrivatePart" $Fixed[3] $Actual.ProductPrivatePart

# Verify that the executable exposes an icon resource and that its 32px frame
# matches the deterministic source icon embedded by the PyInstaller spec.
Add-Type -AssemblyName System.Drawing
$EmbeddedIcon = [System.Drawing.Icon]::ExtractAssociatedIcon($Executable)
if ($null -eq $EmbeddedIcon) { throw "Frozen executable does not expose an associated icon resource." }
$SourceIcon = New-Object System.Drawing.Icon($IconPath, 32, 32)
try {
    $EmbeddedBitmap = $EmbeddedIcon.ToBitmap()
    $SourceBitmap = $SourceIcon.ToBitmap()
    try {
        if ($EmbeddedBitmap.Width -ne $SourceBitmap.Width -or $EmbeddedBitmap.Height -ne $SourceBitmap.Height) {
            throw "Embedded icon dimensions do not match the generated icon frame."
        }
        for ($x = 0; $x -lt $SourceBitmap.Width; $x++) {
            for ($y = 0; $y -lt $SourceBitmap.Height; $y++) {
                if ($EmbeddedBitmap.GetPixel($x, $y).ToArgb() -ne $SourceBitmap.GetPixel($x, $y).ToArgb()) {
                    throw "Embedded icon pixels do not match the deterministic generated icon."
                }
            }
        }
    }
    finally {
        $EmbeddedBitmap.Dispose()
        $SourceBitmap.Dispose()
    }
}
finally {
    $EmbeddedIcon.Dispose()
    $SourceIcon.Dispose()
}

Write-Host ("Windows identity verified: {0} {1} ({2})" -f $Expected.product_name, $Expected.product_version, $Expected.original_filename)
