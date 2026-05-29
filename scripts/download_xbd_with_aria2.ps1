param(
    [string]$TrainUrl = "",
    [string]$Tier3Url = "",
    [string]$TargetRoot = "E:\CrisisMapData\xbd",
    [switch]$SkipTrain,
    [switch]$SkipTier3,
    [switch]$VerifyOnly,
    [switch]$Extract
)

$ErrorActionPreference = "Stop"

$expected = @{
    train = "b37a4ef4ee9c909e2b19d046e49d42ee3965714b"
    tier3 = "5bf6aaf8a71980b633fb4661776a99a200891de5"
}

$downloadsDir = Join-Path $TargetRoot "downloads"
$extractDir = Join-Path $TargetRoot "extracted"
$trainFile = Join-Path $downloadsDir "train_images_labels_targets.tar.gz"
$tier3File = Join-Path $downloadsDir "tier3.tar.gz"

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Assert-Aria2 {
    if (-not (Get-Command aria2c -ErrorAction SilentlyContinue)) {
        throw "aria2c not found. Install it first with: winget install aria2.aria2"
    }
}

function Download-With-Aria2 {
    param(
        [string]$Name,
        [string]$Url,
        [string]$OutputFile
    )

    if ([string]::IsNullOrWhiteSpace($Url)) {
        throw "$Name URL is empty. Paste a fresh signed URL from https://xview2.org/download-links"
    }

    $outName = Split-Path -Leaf $OutputFile
    Write-Host "Downloading $Name to $OutputFile"
    aria2c `
        --continue=true `
        --max-connection-per-server=4 `
        --split=4 `
        --min-split-size=10M `
        --max-tries=0 `
        --retry-wait=30 `
        --timeout=60 `
        --connect-timeout=60 `
        --summary-interval=60 `
        --dir $downloadsDir `
        --out $outName `
        $Url

    if ($LASTEXITCODE -ne 0) {
        throw "Download failed for $Name. If the xView2 link expired, refresh xView2 download page, copy a fresh URL, and rerun this script."
    }
}

function Verify-Sha1 {
    param(
        [string]$Name,
        [string]$File,
        [string]$ExpectedSha1
    )

    if (-not (Test-Path -LiteralPath $File)) {
        Write-Host "MISSING ${Name}: $File"
        return $false
    }

    $hash = (Get-FileHash -LiteralPath $File -Algorithm SHA1).Hash.ToLowerInvariant()
    $ok = $hash -eq $ExpectedSha1
    $status = if ($ok) { "OK" } else { "FAILED" }
    Write-Host "$status $Name"
    Write-Host "  expected: $ExpectedSha1"
    Write-Host "  actual:   $hash"
    return $ok
}

Ensure-Dir $downloadsDir
Ensure-Dir $extractDir

if (-not $VerifyOnly) {
    Assert-Aria2
    if (-not $SkipTrain) {
        Download-With-Aria2 -Name "xBD Challenge training set" -Url $TrainUrl -OutputFile $trainFile
    }
    if (-not $SkipTier3) {
        Download-With-Aria2 -Name "xBD additional Tier3 training data" -Url $Tier3Url -OutputFile $tier3File
    }
}

$trainOk = $true
$tier3Ok = $true
if (-not $SkipTrain) {
    $trainOk = Verify-Sha1 -Name "train_images_labels_targets.tar.gz" -File $trainFile -ExpectedSha1 $expected.train
}
if (-not $SkipTier3) {
    $tier3Ok = Verify-Sha1 -Name "tier3.tar.gz" -File $tier3File -ExpectedSha1 $expected.tier3
}

if ($Extract) {
    if (-not $SkipTrain -and $trainOk) {
        $target = Join-Path $extractDir "train"
        Ensure-Dir $target
        tar -xvzf $trainFile -C $target
    }
    if (-not $SkipTier3 -and $tier3Ok) {
        $target = Join-Path $extractDir "tier3"
        Ensure-Dir $target
        tar -xvzf $tier3File -C $target
    }
}

Write-Host "Done. Download folder: $downloadsDir"
