# Caminhos usados pelos scripts. Dot-source: . "$PSScriptRoot\config.ps1"
#
# Tudo que vem do jogo fica fora do repositorio, sob $RdrLocal (padrao:
# <repo>\local, ignorado pelo git). Cada caminho pode ser trocado por uma
# variavel de ambiente, para apontar para uma arvore de trabalho ja existente.
#
# Paths used by the scripts. Everything derived from the game lives outside the
# repository, under $RdrLocal (default <repo>\local, git-ignored). Each path can
# be overridden with the environment variable named next to it.

$RdrRepo  = (Resolve-Path "$PSScriptRoot\..").Path
$RdrLocal = if ($env:RDR_ROOT) { $env:RDR_ROOT } else { "$RdrRepo\local" }

# ps3recomp v0.19.0 limpo (tag v0.19.0, commit ae92407). So e lido.
$Ps3RecompDir = if ($env:PS3RECOMP_DIR) { $env:PS3RECOMP_DIR } else { "$RdrLocal\ps3recomp" }
# ELF decriptado pelo proprio usuario, a partir da copia dele do jogo.
$RdrElf       = if ($env:RDR_ELF)       { $env:RDR_ELF }       else { "$RdrLocal\game\RDR2.elf" }
# Saida do ppu_lifter.py (ppu_recomp.h e ppu_recomp_NNN.cpp).
$RdrLifted    = if ($env:RDR_LIFTED)    { $env:RDR_LIFTED }    else { "$RdrLocal\lifted" }
# Arquivos do toolkit com patches/ aplicado (scripts\prepare_overlay.ps1).
$RdrOverlay   = if ($env:RDR_OVERLAY)   { $env:RDR_OVERLAY }   else { "$RdrLocal\overlay" }
$RdrBuild     = if ($env:RDR_BUILD)     { $env:RDR_BUILD }     else { "$RdrLocal\build" }
$RdrBoots     = if ($env:RDR_BOOTS)     { $env:RDR_BOOTS }     else { "$RdrLocal\boots" }
# Arvore do disco (PS3_GAME/..., USRDIR/...) e dev_flash, do proprio usuario.
$RdrVfs       = if ($env:RDR_VFS)       { $env:RDR_VFS }       else { "$RdrLocal\vfs" }
$RdrDevFlash  = if ($env:RDR_DEV_FLASH) { $env:RDR_DEV_FLASH } else { "$RdrLocal\dev_flash" }

# Toolchain: pasta bin do llvm-mingw (clang, clang++, windres, llvm-nm) e Python 3.
# Se vazios, os programas precisam ja estar no PATH.
$LlvmMingwBin = $env:LLVM_MINGW_BIN
$PythonDir    = $env:PYTHON_DIR
$extra = @($LlvmMingwBin, $PythonDir, $(if ($PythonDir) { "$PythonDir\Scripts" })) | Where-Object { $_ }
if ($extra) { $env:PATH = (($extra -join ';') + ";$env:PATH") }

function Get-RdrTool([string]$Name) {
    if ($LlvmMingwBin -and (Test-Path "$LlvmMingwBin\$Name")) { return "$LlvmMingwBin\$Name" }
    $c = Get-Command $Name -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    throw "$Name nao encontrado: defina LLVM_MINGW_BIN ou ponha no PATH"
}
