# Monta local\overlay: copia do ps3recomp v0.19.0 (ae92407) os arquivos que o
# port substitui e aplica patches\ps3recomp-v0.19.0-rdr.patch sobre eles.
# Nao altera o checkout do ps3recomp.
#
# Builds local\overlay: takes the files the port replaces from ps3recomp v0.19.0
# (ae92407), applies patches\ps3recomp-v0.19.0-rdr.patch to them, and leaves the
# toolkit checkout untouched.
param([switch]$Force)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\config.ps1"

$Base  = 'ae92407'
$Patch = "$RdrRepo\patches\ps3recomp-v0.19.0-rdr.patch"
# nome no overlay = caminho no toolkit
$Map = [ordered]@{
    'cellAvconfExt.c'       = 'libs/misc/cellAvconfExt.c'
    'cellFiber.c'           = 'libs/spurs/cellFiber.c'
    'cellGcmSys.c'          = 'libs/video/cellGcmSys.c'
    'cellSpurs.c'           = 'libs/spurs/cellSpurs.c'
    'ppu_fs.cpp'            = 'runtime/ppu/ppu_fs.cpp'
    'ppu_sysprx.cpp'        = 'runtime/ppu/ppu_sysprx.cpp'
    'rsx_fp_decompiler.c'   = 'libs/video/rsx_fp_decompiler.c'
    'rsx_live_draw.c'       = 'libs/video/rsx_live_draw.c'
    'spu_channels.c'        = 'runtime/spu/spu_channels.c'
    'spu_drain.c'           = 'runtime/spu/spu_drain.c'
    'spurs_job.c'           = 'runtime/spu/spurs_job.c'
    'sys_semaphore.c'       = 'runtime/syscalls/sys_semaphore.c'
    'sys_semaphore.h'       = 'runtime/syscalls/sys_semaphore.h'
    'sys_timer.c'           = 'runtime/syscalls/sys_timer.c'
    'spu_inc/spu_context.h' = 'runtime/spu/spu_context.h'
}

if (-not (Test-Path "$Ps3RecompDir\.git")) { throw "PS3RECOMP_DIR ($Ps3RecompDir) nao e um clone git do ps3recomp" }
& git -C $Ps3RecompDir cat-file -e "$Base^{commit}" 2>$null
if ($LASTEXITCODE) { throw "o clone em $Ps3RecompDir nao tem o commit $Base (v0.19.0); rode git fetch --tags" }
$head = (& git -C $Ps3RecompDir rev-parse --short=7 HEAD).Trim()
if ($head -ne $Base) { Write-Warning "HEAD de $Ps3RecompDir e $head, nao ${Base}: o build vai misturar versoes do toolkit" }

if (Test-Path $RdrOverlay) {
    if (-not $Force) { throw "$RdrOverlay ja existe; use -Force para refazer (ppu_recomp_023.cpp, se houver, e preservado)" }
    Get-ChildItem $RdrOverlay -Recurse -File | Where-Object { $_.Name -ne 'ppu_recomp_023.cpp' } | Remove-Item -Force
}

$tmp = Join-Path ([IO.Path]::GetTempPath()) ("rdr_overlay_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $tmp | Out-Null
try {
    # git archive grava os arquivos byte a byte (LF, sem conversao); um pipe do
    # PowerShell recodificaria o texto.
    & git -C $Ps3RecompDir -c core.autocrlf=false archive --format=tar -o "$tmp\base.tar" $Base -- @($Map.Values)
    if ($LASTEXITCODE) { throw "git archive falhou" }
    & tar -xf "$tmp\base.tar" -C $tmp
    if ($LASTEXITCODE) { throw "tar falhou" }
    Remove-Item "$tmp\base.tar"
    Push-Location $tmp
    try {
        & git -c core.autocrlf=false apply --whitespace=nowarn $Patch
        if ($LASTEXITCODE) { throw "git apply falhou" }
    } finally { Pop-Location }
    foreach ($k in $Map.Keys) {
        $dst = Join-Path $RdrOverlay $k
        New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
        Copy-Item (Join-Path $tmp $Map[$k]) $dst -Force
    }
} finally { Remove-Item $tmp -Recurse -Force }
"overlay pronto em $RdrOverlay ($($Map.Count) arquivos)"
if (-not (Test-Path "$RdrOverlay\ppu_recomp_023.cpp")) {
    "  sem ppu_recomp_023.cpp: opcional, gerado por scripts\gera_voz.py a partir do seu lift"
}
