param(
    [switch]$SkipLargeImagery
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$dataRoot = Join-Path $repoRoot "data"
$rawRoot = Join-Path $dataRoot "raw"
$manifestPath = Join-Path $dataRoot "public_data_download_manifest.json"
$downloadedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$items = New-Object System.Collections.Generic.List[object]

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Add-ManifestItem {
    param(
        [string]$Name,
        [string]$Source,
        [string]$Destination,
        [string]$Status,
        [string]$Notes = ""
    )

    $sizeBytes = $null
    if (Test-Path -LiteralPath $Destination) {
        $sizeBytes = (Get-Item -LiteralPath $Destination).Length
    }

    $items.Add([ordered]@{
        name = $Name
        source = $Source
        destination = $Destination
        status = $Status
        size_bytes = $sizeBytes
        notes = $Notes
    }) | Out-Null
}

function Download-File {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Destination,
        [int64]$MinimumBytes = 1,
        [string]$Notes = ""
    )

    Ensure-Dir (Split-Path -Parent $Destination)

    if ((Test-Path -LiteralPath $Destination) -and ((Get-Item -LiteralPath $Destination).Length -ge $MinimumBytes)) {
        Write-Host "SKIP  $Name"
        Add-ManifestItem -Name $Name -Source $Url -Destination $Destination -Status "already_present" -Notes $Notes
        return
    }

    Write-Host "GET   $Name"
    curl.exe --location --fail --retry 3 --retry-delay 5 --continue-at - --output $Destination $Url
    if ($LASTEXITCODE -ne 0) {
        throw "Download failed for $Name from $Url"
    }
    Add-ManifestItem -Name $Name -Source $Url -Destination $Destination -Status "downloaded" -Notes $Notes
}

function Expand-Zip {
    param(
        [string]$Name,
        [string]$ZipPath,
        [string]$Destination
    )

    if (-not (Test-Path -LiteralPath $ZipPath)) {
        throw "Zip not found for extraction: $ZipPath"
    }

    Ensure-Dir $Destination
    Write-Host "UNZIP $Name"
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $Destination -Force
}

function Download-Overpass {
    param(
        [string]$Name,
        [string]$Destination
    )

    Ensure-Dir (Split-Path -Parent $Destination)
    $queryPath = Join-Path (Split-Path -Parent $Destination) "overpass_beirut_infrastructure.ql"
    $query = @"
[out:json][timeout:180];
(
  way["building"](33.8500,35.4800,33.9000,35.5500);
  relation["building"](33.8500,35.4800,33.9000,35.5500);
  way["highway"](33.8500,35.4800,33.9000,35.5500);
  relation["highway"](33.8500,35.4800,33.9000,35.5500);
  node["amenity"~"hospital|clinic|doctors|school|university|fire_station|police"](33.8500,35.4800,33.9000,35.5500);
  way["amenity"~"hospital|clinic|doctors|school|university|fire_station|police"](33.8500,35.4800,33.9000,35.5500);
  relation["amenity"~"hospital|clinic|doctors|school|university|fire_station|police"](33.8500,35.4800,33.9000,35.5500);
  node["healthcare"](33.8500,35.4800,33.9000,35.5500);
  way["healthcare"](33.8500,35.4800,33.9000,35.5500);
  relation["healthcare"](33.8500,35.4800,33.9000,35.5500);
  node["power"](33.8500,35.4800,33.9000,35.5500);
  way["power"](33.8500,35.4800,33.9000,35.5500);
  relation["power"](33.8500,35.4800,33.9000,35.5500);
  node["man_made"="water_works"](33.8500,35.4800,33.9000,35.5500);
  way["man_made"="water_works"](33.8500,35.4800,33.9000,35.5500);
  relation["man_made"="water_works"](33.8500,35.4800,33.9000,35.5500);
);
out body geom qt;
"@
    Set-Content -LiteralPath $queryPath -Value $query -Encoding ASCII

    if ((Test-Path -LiteralPath $Destination) -and ((Get-Item -LiteralPath $Destination).Length -gt 1000)) {
        Write-Host "SKIP  $Name"
        Add-ManifestItem -Name $Name -Source "https://overpass.kumi.systems/api/interpreter" -Destination $Destination -Status "already_present" -Notes "AOI bbox: south=33.85 west=35.48 north=33.90 east=35.55"
        return
    }

    Write-Host "POST  $Name"
    curl.exe --location --fail --retry 3 --retry-delay 5 --request POST --data-urlencode "data@$queryPath" --output $Destination "https://overpass.kumi.systems/api/interpreter"
    if ($LASTEXITCODE -ne 0) {
        throw "Overpass download failed for $Name"
    }
    Add-ManifestItem -Name $Name -Source "https://overpass.kumi.systems/api/interpreter" -Destination $Destination -Status "downloaded" -Notes "AOI bbox: south=33.85 west=35.48 north=33.90 east=35.55"
}

Ensure-Dir $rawRoot

$maxarDir = Join-Path $rawRoot "imagery\maxar\beirut_explosion"
$maxarVectorDir = Join-Path $rawRoot "vector\maxar\beirut_explosion"
$oamDir = Join-Path $rawRoot "imagery\openaerialmap\beirut_aoi"
$emsDir = Join-Path $rawRoot "ground_truth\copernicus_ems\EMSR452"
$osmDir = Join-Path $rawRoot "vector\osm\beirut_aoi"
$hdxDir = Join-Path $rawRoot "humanitarian\hdx\lebanon_healthsites"
$worldPopDir = Join-Path $rawRoot "population\worldpop\LBN\2020"
$modelDir = Join-Path $rawRoot "models\microsoft_building_damage_assessment_cnn_siamese"

Download-File `
    -Name "Maxar Beirut pre-event full orthomosaic 2020-07-31" `
    -Url "https://opendata.digitalglobe.com/events/beirut-explosion/pre-event/2020-07-31/10300500A5F95600/10300500A5F95600.tif" `
    -Destination (Join-Path $maxarDir "pre_event_2020-07-31_10300500A5F95600.tif") `
    -MinimumBytes 100000000 `
    -Notes "High-resolution pre-disaster image for building-level damage assessment."

Download-File `
    -Name "Maxar Beirut post-event full orthomosaic 2020-08-05" `
    -Url "https://opendata.digitalglobe.com/events/beirut-explosion/post-event/2020-08-05/104001005EBCEB00/104001005EBCEB00.tif" `
    -Destination (Join-Path $maxarDir "post_event_2020-08-05_104001005EBCEB00.tif") `
    -MinimumBytes 100000000 `
    -Notes "High-resolution post-disaster image for building-level damage assessment."

Download-File `
    -Name "Maxar Beirut pre-event preview ortho 2020-07-31" `
    -Url "https://opendata.digitalglobe.com/events/beirut-explosion/vector-data/2020-08-04/ortho/ortho_0731.tif" `
    -Destination (Join-Path $maxarDir "preview_ortho_0731.tif") `
    -MinimumBytes 1000000 `
    -Notes "Small preview ortho useful for quick QA."

Download-File `
    -Name "Maxar Beirut post-event preview ortho 2020-08-05" `
    -Url "https://opendata.digitalglobe.com/events/beirut-explosion/vector-data/2020-08-04/ortho/ortho_0805.tif" `
    -Destination (Join-Path $maxarDir "preview_ortho_0805.tif") `
    -MinimumBytes 1000000 `
    -Notes "Small preview ortho useful for quick QA."

Download-File `
    -Name "Maxar Beirut 2D building footprints" `
    -Url "https://opendata.digitalglobe.com/events/beirut-explosion/vector-data/2020-08-04/footprints/Beirut%20-%202D%20Footprints.zip" `
    -Destination (Join-Path $maxarVectorDir "Beirut_2D_Footprints.zip") `
    -MinimumBytes 1000000 `
    -Notes "Building footprint vector data from Maxar Open Data."

Expand-Zip `
    -Name "Maxar Beirut 2D building footprints" `
    -ZipPath (Join-Path $maxarVectorDir "Beirut_2D_Footprints.zip") `
    -Destination (Join-Path $maxarVectorDir "extracted")

Download-File `
    -Name "OpenAerialMap Beirut AOI metadata" `
    -Url "https://api.openaerialmap.org/meta?bbox=35.48,33.85,35.55,33.90&limit=100" `
    -Destination (Join-Path $oamDir "oam_metadata_beirut_2020.json") `
    -MinimumBytes 1000 `
    -Notes "Catalog metadata for available UAV/satellite imagery over Beirut."

if (-not $SkipLargeImagery) {
    Download-File `
        -Name "OpenAerialMap Beirut post-event UAV image 2020-08-05" `
        -Url "https://oin-hotosm-temp.s3.amazonaws.com/5f2bd274b0052e00067dbaed/0/5f2bd274b0052e00067dbaee.tif" `
        -Destination (Join-Path $oamDir "post_event_uav_2020-08-05_beirut_port_012m.tif") `
        -MinimumBytes 100000000 `
        -Notes "0.12m UAV post-event image around Beirut port; useful as detailed visual reference, not a full pre/post pair."
}

Download-File `
    -Name "Copernicus EMSR452 Beirut grading vector package" `
    -Url "https://cems-mapping-website.s3.eu-west-1.amazonaws.com/static/activations/EMSR452/EMSR452_AOI01_GRA_PRODUCT_r1_RTP01_v2_vector.zip" `
    -Destination (Join-Path $emsDir "EMSR452_AOI01_GRA_PRODUCT_r1_RTP01_v2_vector.zip") `
    -MinimumBytes 100000 `
    -Notes "Public ground-truth/validation vector package for Beirut explosion damage grading."

Expand-Zip `
    -Name "Copernicus EMSR452 Beirut grading vector package" `
    -ZipPath (Join-Path $emsDir "EMSR452_AOI01_GRA_PRODUCT_r1_RTP01_v2_vector.zip") `
    -Destination (Join-Path $emsDir "extracted")

Download-Overpass `
    -Name "OpenStreetMap Beirut AOI buildings, roads, critical infrastructure" `
    -Destination (Join-Path $osmDir "overpass_beirut_infrastructure.json")

Download-File `
    -Name "HDX Lebanon Healthsites package metadata" `
    -Url "https://data.humdata.org/api/3/action/package_search?q=Lebanon%20healthsites" `
    -Destination (Join-Path $hdxDir "lebanon_healthsites_package.json") `
    -MinimumBytes 1000 `
    -Notes "HDX package metadata used to track source and license."

Download-File `
    -Name "HDX Lebanon Healthsites GeoJSON" `
    -Url "https://data.humdata.org/dataset/b04dc45f-5377-4b80-8432-2470325eeb47/resource/b32d0126-8e54-4421-a996-f6d4bf506fa2/download/lebanon.geojson" `
    -Destination (Join-Path $hdxDir "lebanon_healthsites.geojson") `
    -MinimumBytes 100000 `
    -Notes "Health facility locations for humanitarian impact and cascade analysis."

Download-File `
    -Name "WorldPop Lebanon 2020 100m population raster" `
    -Url "https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/LBN/lbn_ppp_2020.tif" `
    -Destination (Join-Path $worldPopDir "lbn_ppp_2020.tif") `
    -MinimumBytes 1000000 `
    -Notes "Population exposure raster, people per 100m grid cell."

Download-File `
    -Name "WorldPop Lebanon population API index" `
    -Url "https://www.worldpop.org/rest/data/pop/wpgp?iso3=LBN" `
    -Destination (Join-Path $worldPopDir "worldpop_lbn_wpgp_index.json") `
    -MinimumBytes 1000 `
    -Notes "WorldPop API metadata and citation information."

Download-File `
    -Name "Microsoft Siamese CNN baseline pretrained weights" `
    -Url "https://raw.githubusercontent.com/microsoft/building-damage-assessment-cnn-siamese/main/models/model_best.pth.tar" `
    -Destination (Join-Path $modelDir "model_best.pth.tar") `
    -MinimumBytes 10000000 `
    -Notes "Public PyTorch checkpoint for baseline xBD-style building damage assessment."

Download-File `
    -Name "Microsoft Siamese CNN baseline model definition" `
    -Url "https://raw.githubusercontent.com/microsoft/building-damage-assessment-cnn-siamese/main/models/end_to_end_Siam_UNet.py" `
    -Destination (Join-Path $modelDir "end_to_end_Siam_UNet.py") `
    -MinimumBytes 1000 `
    -Notes "Model architecture source needed to load the baseline checkpoint."

Download-File `
    -Name "Microsoft Siamese CNN baseline README" `
    -Url "https://raw.githubusercontent.com/microsoft/building-damage-assessment-cnn-siamese/main/README.md" `
    -Destination (Join-Path $modelDir "README.md") `
    -MinimumBytes 1000 `
    -Notes "Source documentation for the baseline model."

Download-File `
    -Name "Microsoft Siamese CNN baseline license" `
    -Url "https://raw.githubusercontent.com/microsoft/building-damage-assessment-cnn-siamese/main/LICENSE" `
    -Destination (Join-Path $modelDir "LICENSE") `
    -MinimumBytes 100 `
    -Notes "License for the downloaded baseline model repository."

$manifest = [ordered]@{
    downloaded_at = $downloadedAt
    repo_root = $repoRoot
    aoi = [ordered]@{
        name = "Beirut Port AOI"
        bbox_lonlat = @(35.48, 33.85, 35.55, 33.90)
        crs = "EPSG:4326"
    }
    items = $items
    manual_required = @(
        "xBD/xView2 official dataset: requires account/Kaggle or explicit dataset access.",
        "ACLED API conflict-event data: requires registered ACLED access token.",
        "Copernicus Data Space Sentinel products: public but authenticated account is usually required for full product download.",
        "Any commercial imagery outside Maxar/OpenAerialMap open-data disaster releases."
    )
}

$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Host "DONE  Manifest: $manifestPath"
