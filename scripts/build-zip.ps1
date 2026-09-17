# Gera dist/tatiane-cavalcante.zip com SÓ o que vai para public_html.
# Uso (na raiz do projeto):  powershell -ExecutionPolicy Bypass -File scripts\build-zip.ps1
#
# Não usa Compress-Archive: no PowerShell 5.1 ele grava os caminhos com "\" e o unzip do
# servidor Linux (cPanel) pode criar arquivos chamados "assets\x.png" em vez de pastas.
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist"
$zip  = Join-Path $dist "tatiane-cavalcante.zip"
$publish = @("index.html", ".htaccess", "css", "js", "assets")

New-Item -ItemType Directory -Force $dist | Out-Null
if (Test-Path $zip) { Remove-Item -Force $zip }

$files = @()
foreach ($item in $publish) {
  $src = Join-Path $root $item
  if (-not (Test-Path $src)) { throw "Faltando: $item" }
  if (Test-Path $src -PathType Container) {
    Get-ChildItem -Path $src -Recurse -File -Force | ForEach-Object { $files += $_.FullName }
  } else {
    $files += (Get-Item $src -Force).FullName
  }
}

$archive = [System.IO.Compression.ZipFile]::Open($zip, [System.IO.Compression.ZipArchiveMode]::Create)
try {
  foreach ($f in $files) {
    $rel = $f.Substring($root.Length + 1).Replace("\", "/")   # sempre "/" dentro do zip
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $f, $rel, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
  }
} finally {
  $archive.Dispose()
}

$size = [math]::Round((Get-Item $zip).Length / 1KB)
Write-Host "OK -> $zip ($size KB)"
Write-Host "Conteudo:"
$check = [System.IO.Compression.ZipFile]::OpenRead($zip)
try { $check.Entries | ForEach-Object { Write-Host ("  " + $_.FullName) } } finally { $check.Dispose() }
