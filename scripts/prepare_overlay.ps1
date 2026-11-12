# Monta local\overlay: copia do toolkit com os PRs (local\ps3recomp-rdr, feito por
# scripts\prepare_toolkit.ps1) os arquivos que o port substitui e aplica
# patches\ps3recomp-v0.19.0-rdr.patch sobre eles. Nao altera o toolkit.
#
# Builds local\overlay: takes the files the port replaces from the toolkit with the
# upstream PRs (local\ps3recomp-rdr, made by scripts\prepare_toolkit.ps1), applies
# patches\ps3recomp-v0.19.0-rdr.patch to them, and leaves the toolkit untouched.
param([switch]$Force)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\config.ps1"

$Patch = "$RdrRepo\patches\ps3recomp-v0.19.0-rdr.patch"
$Prs   = "$RdrRepo\patches\ps3recomp-v0.19.0-upstream-prs.patch"
# nome no overlay = caminho no toolkit
$Map = [ordered]@{
    'cellAvconfExt.c'       = 'libs/misc/cellAvconfExt.c'
    'cellFiber.c'           = 'libs/spurs/cellFiber.c'
    'cellGcmSys.c'          = 'libs/video/cellGcmSys.c'
    'cellSpurs.c'           = 'libs/spurs/cellSpurs.c'
    'cellSysutil.c'         = 'libs/system/cellSysutil.c'
    'ppu_fs.cpp'            = 'runtime/ppu/ppu_fs.cpp'
    'ppu_sysprx.cpp'        = 'runtime/ppu/ppu_sysprx.cpp'
    'rsx_fp_decompiler.c'   = 'libs/video/rsx_fp_decompiler.c'
    'rsx_live_draw.c'       = 'libs/video/rsx_live_draw.c'
    'spu_channels.c'        = 'runtime/spu/spu_channels.c'
    'spu_drain.c'           = 'runtime/spu/spu_drain.c'
    'spurs_job.c'           = 'runtime/spu/spurs_job.c'
    'sys_ppu_thread.c'      = 'runtime/syscalls/sys_ppu_thread.c'
    'sys_semaphore.c'       = 'runtime/syscalls/sys_semaphore.c'
    'sys_semaphore.h'       = 'runtime/syscalls/sys_semaphore.h'
    'sys_timer.c'           = 'runtime/syscalls/sys_timer.c'
    'spu_inc/spu_context.h' = 'runtime/spu/spu_context.h'
}

# O patch do RDR e relativo ao toolkit com os PRs: confere que e esse o toolkit.
# The RDR patch is relative to the toolkit with the PRs: check that this is it.
$marca = "$Ps3RecompDir\.rdr-upstream-prs"
if (-not (Test-Path $marca)) { throw "$Ps3RecompDir nao foi montado por scripts\prepare_toolkit.ps1 (rode-o antes)" }
if ((Get-Content $marca -Raw).Trim() -ne (Get-FileHash $Prs -Algorithm SHA256).Hash) {
    throw "$Ps3RecompDir foi montado com outro patch de PRs; rode scripts\prepare_toolkit.ps1 -Force"
}

if (Test-Path $RdrOverlay) {
    if (-not $Force) { throw "$RdrOverlay ja existe; use -Force para refazer (ppu_recomp_023.cpp, se houver, e preservado)" }
    Get-ChildItem $RdrOverlay -Recurse -File | Where-Object { $_.Name -ne 'ppu_recomp_023.cpp' } | Remove-Item -Force
}

$tmp = Join-Path ([IO.Path]::GetTempPath()) ("rdr_overlay_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $tmp | Out-Null
try {
    foreach ($p in $Map.Values) {
        $dst = Join-Path $tmp $p
        New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
        Copy-Item (Join-Path $Ps3RecompDir $p) $dst
    }
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
