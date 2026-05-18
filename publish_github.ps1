param(
    [string]$Owner = "zetmar-collab",
    [string]$Repo = "Teleprom",
    [string]$ReleaseTag = "v1.0.0",
    [string]$ReleaseName = "Teleprom v1.0.0"
)

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ZipPath = Join-Path $ProjectDir "Teleprom.zip"
$NotesPath = Join-Path $ProjectDir "RELEASE_NOTES.md"
$Repository = "$Owner/$Repo"
$Token = $env:GITHUB_TOKEN
if (!$Token) {
    $Token = $env:GH_TOKEN
}
if (!$Token) {
    throw "Ustaw GITHUB_TOKEN albo GH_TOKEN z uprawnieniami do repozytoriów i release w $Owner."
}
if (!(Test-Path $ZipPath)) {
    throw "Brak paczki ZIP: $ZipPath"
}

$Headers = @{
    Authorization = "Bearer $Token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

function Invoke-GitHub {
    param(
        [string]$Method,
        [string]$Uri,
        [object]$Body = $null,
        [hashtable]$ExtraHeaders = @{}
    )

    $allHeaders = $Headers.Clone()
    foreach ($key in $ExtraHeaders.Keys) {
        $allHeaders[$key] = $ExtraHeaders[$key]
    }

    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $allHeaders
    }

    return Invoke-RestMethod `
        -Method $Method `
        -Uri $Uri `
        -Headers $allHeaders `
        -Body ($Body | ConvertTo-Json -Depth 20) `
        -ContentType "application/json"
}

function Test-RepoExists {
    try {
        Invoke-GitHub -Method Get -Uri "https://api.github.com/repos/$Repository" | Out-Null
        return $true
    }
    catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 404) {
            return $false
        }
        throw
    }
}

Write-Host "Publikuję $Repository..."

if (!(Test-RepoExists)) {
    $me = Invoke-GitHub -Method Get -Uri "https://api.github.com/user"
    $body = @{
        name = $Repo
        private = $false
        description = "Teleprom - teleprompter autorstwa Marek Zettel"
        auto_init = $false
    }

    if ($me.login -eq $Owner) {
        Invoke-GitHub -Method Post -Uri "https://api.github.com/user/repos" -Body $body | Out-Null
    }
    else {
        Invoke-GitHub -Method Post -Uri "https://api.github.com/orgs/$Owner/repos" -Body $body | Out-Null
    }
}

git -C $ProjectDir remote | Where-Object { $_ -eq "origin" } | ForEach-Object {
    git -C $ProjectDir remote remove origin
}
git -C $ProjectDir remote add origin "https://x-access-token:$Token@github.com/$Repository.git"
git -C $ProjectDir push -u origin main

git -C $ProjectDir tag -f $ReleaseTag
git -C $ProjectDir push origin $ReleaseTag --force
git -C $ProjectDir remote set-url origin "https://github.com/$Repository.git"

$releaseBody = if (Test-Path $NotesPath) { Get-Content -Raw $NotesPath } else { "Teleprom release." }

try {
    $release = Invoke-GitHub -Method Post -Uri "https://api.github.com/repos/$Repository/releases" -Body @{
        tag_name = $ReleaseTag
        target_commitish = "main"
        name = $ReleaseName
        body = $releaseBody
        draft = $false
        prerelease = $false
    }
}
catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 422) {
        throw
    }
    $release = Invoke-GitHub -Method Get -Uri "https://api.github.com/repos/$Repository/releases/tags/$ReleaseTag"
}

$assets = Invoke-GitHub -Method Get -Uri "https://api.github.com/repos/$Repository/releases/$($release.id)/assets"
foreach ($asset in $assets) {
    if ($asset.name -eq "Teleprom.zip") {
        Invoke-GitHub -Method Delete -Uri "https://api.github.com/repos/$Repository/releases/assets/$($asset.id)" | Out-Null
    }
}

$uploadUrl = $release.upload_url -replace "\{\?name,label\}", "?name=Teleprom.zip"
$uploadHeaders = @{
    Authorization = "Bearer $Token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "Content-Type" = "application/zip"
}
Invoke-RestMethod -Method Post -Uri $uploadUrl -Headers $uploadHeaders -InFile $ZipPath | Out-Null

Write-Host "Gotowe: https://github.com/$Repository/releases/tag/$ReleaseTag"
