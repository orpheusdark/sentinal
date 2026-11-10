param(
    [Parameter(Mandatory = $true)][string]$TargetFile,
    [switch]$RequireSigning
)
$ErrorActionPreference = 'Stop'
if (-not $env:WINDOWS_SIGNING_PFX_BASE64) {
    if ($RequireSigning) { throw 'Windows signing was required but no certificate is configured.' }
    Write-Output 'Unsigned preview: no Windows signing certificate configured.'
    exit 0
}
if (-not $env:WINDOWS_SIGNING_TIMESTAMP_URL -or -not $env:WINDOWS_SIGNING_TIMESTAMP_URL.StartsWith('https://')) {
    throw 'Configure an HTTPS RFC 3161 timestamp URL before signing.'
}
$resolvedTarget = (Resolve-Path -LiteralPath $TargetFile).Path
$toolRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
$signTool = Get-ChildItem -LiteralPath $toolRoot -Recurse -Filter signtool.exe |
    Where-Object { $_.FullName -match '\\x64\\signtool.exe$' } |
    Sort-Object FullName -Descending | Select-Object -First 1
if (-not $signTool) { throw 'Windows SDK signtool.exe was not found.' }
$certificateFile = Join-Path ([System.IO.Path]::GetTempPath()) ('sentinel-signing-' + [guid]::NewGuid() + '.pfx')
$certificate = $null
try {
    [System.IO.File]::WriteAllBytes($certificateFile, [Convert]::FromBase64String($env:WINDOWS_SIGNING_PFX_BASE64))
    $password = ConvertTo-SecureString $env:WINDOWS_SIGNING_PFX_PASSWORD -AsPlainText -Force
    $certificate = Import-PfxCertificate -FilePath $certificateFile -CertStoreLocation Cert:\CurrentUser\My -Password $password
    & $signTool.FullName sign /sha1 $certificate.Thumbprint /s My /fd SHA256 /tr $env:WINDOWS_SIGNING_TIMESTAMP_URL /td SHA256 /d Sentinel $resolvedTarget
    if ($LASTEXITCODE -ne 0) { throw 'Windows application signing failed.' }
    & $signTool.FullName verify /pa $resolvedTarget
    if ($LASTEXITCODE -ne 0) { throw 'Windows signature verification failed.' }
    Write-Output 'Windows Authenticode signature verified.'
} finally {
    Remove-Item -LiteralPath $certificateFile -Force -ErrorAction SilentlyContinue
    if ($certificate) { Remove-Item -LiteralPath ('Cert:\CurrentUser\My\' + $certificate.Thumbprint) -Force -ErrorAction SilentlyContinue }
}
