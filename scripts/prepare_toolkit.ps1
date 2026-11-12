# Monta local\ps3recomp-rdr: a arvore da v0.19.0 (ae92407) tirada do clone limpo com
# git archive, mais patches\ps3recomp-v0.19.0-upstream-prs.patch (12 PRs abertos do
# ps3recomp; lista em patches\README.md). O clone em local\ps3recomp nao e alterado.
#
# Builds local\ps3recomp-rdr: the v0.19.0 tree (ae92407) exported from the clean
# clone with git archive, plus patches\ps3recomp-v0.19.0-upstream-prs.patch (12 open
# ps3recomp PRs; listed in patches\README.md). The clone itself is left untouched.
param([switch]$Force)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\config.ps1"

$Base  = 'ae92407'
$Patch = "$RdrRepo\patches\ps3recomp-v0.19.0-upstream-prs.patch"
$Marca = '.rdr-upstream-prs'   # SHA-256 do patch aplicado / SHA-256 of the applied patch

if (-not (Test-Path "$Ps3RecompSrc\.git")) { throw "PS3RECOMP_SRC ($Ps3RecompSrc) nao e um clone git do ps3recomp" }
& git -C $Ps3RecompSrc cat-file -e "$Base^{commit}" 2>$null
if ($LASTEXITCODE) { throw "o clone em $Ps3RecompSrc nao tem o commit $Base (v0.19.0); rode git fetch --tags" }
if ((Resolve-Path $Ps3RecompSrc).Path -eq [IO.Path]::GetFullPath($Ps3RecompDir)) {
    throw "PS3RECOMP_DIR e PS3RECOMP_SRC apontam para a mesma pasta; o toolkit com os PRs precisa de uma pasta propria"
}
if (Test-Path $Ps3RecompDir) {
    if (-not $Force) { throw "$Ps3RecompDir ja existe; use -Force para refazer" }
    Remove-Item $Ps3RecompDir -Recurse -Force
}

# Monta fora do repositorio: dentro dele, o git apply aplicaria os caminhos a partir
# da raiz do RDR_recomp. / Built outside the repository, where git apply would
# resolve paths from the RDR_recomp root.
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("rdr_toolkit_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $tmp | Out-Null
try {
    # git archive grava os arquivos byte a byte (LF), como o patch espera.
    & git -C $Ps3RecompSrc -c core.autocrlf=false archive --format=tar -o "$tmp.tar" $Base
    if ($LASTEXITCODE) { throw "git archive falhou" }
    & tar -xf "$tmp.tar" -C $tmp
    if ($LASTEXITCODE) { throw "tar falhou" }
    Push-Location $tmp
    try {
        & git -c core.autocrlf=false apply --whitespace=nowarn $Patch
        if ($LASTEXITCODE) { throw "git apply falhou" }
    } finally { Pop-Location }
    Set-Content -Path "$tmp\$Marca" -Value (Get-FileHash $Patch -Algorithm SHA256).Hash -Encoding ascii
    New-Item -ItemType Directory -Force (Split-Path $Ps3RecompDir) | Out-Null
    Move-Item $tmp $Ps3RecompDir
} finally {
    Remove-Item "$tmp.tar" -Force -ErrorAction SilentlyContinue
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
}
"toolkit pronto em $Ps3RecompDir (v0.19.0 + PRs de $(Split-Path $Patch -Leaf))"
