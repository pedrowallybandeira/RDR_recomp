# Configura (na primeira vez) e compila o port com Ninja e llvm-mingw.
# Antes: scripts\prepare_overlay.ps1 e o lift em $RdrLifted (docs\BUILDING.md).
#
# Configures (first time) and builds the port with Ninja and llvm-mingw.
param([int]$Jobs = 6, [switch]$NoSpuScan)
. "$PSScriptRoot\config.ps1"
$cc  = (Get-RdrTool 'clang.exe')   -replace '\\', '/'
$cxx = (Get-RdrTool 'clang++.exe') -replace '\\', '/'
$rc  = (Get-RdrTool 'windres.exe') -replace '\\', '/'
$f = { param($p) $p -replace '\\', '/' }
New-Item -ItemType Directory -Force $RdrBuild | Out-Null
$t = Get-Date
if (-not (Test-Path "$RdrBuild\build.ninja")) {
    $cmakeArgs = @('-G', 'Ninja', '-S', "$RdrRepo\port", '-B', $RdrBuild,
        "-DPS3RECOMP_DIR=$(& $f $Ps3RecompDir)",
        "-DRECOMP_DIR=$(& $f $RdrLifted)",
        "-DPORT_LOCAL_DIR=$(& $f $RdrLocal)",
        "-DPORT_OVERLAY_DIR=$(& $f $RdrOverlay)",
        "-DCMAKE_C_COMPILER=$cc", "-DCMAKE_CXX_COMPILER=$cxx", "-DCMAKE_RC_COMPILER=$rc",
        '-DCMAKE_C_FLAGS=-D_WIN32_WINNT=0x0A00', '-DCMAKE_CXX_FLAGS=-D_WIN32_WINNT=0x0A00')
    # Varre o ELF atras dos programas SPU embutidos e traduz cada um (build\generated_spu).
    if (-not $NoSpuScan) { $cmakeArgs += "-DPORT_SPU_INPUTS=$(& $f $RdrElf)" }
    cmake @cmakeArgs *> "$RdrBuild\configure.log"
    "cmake exit=$LASTEXITCODE"
    if ($LASTEXITCODE) { Get-Content "$RdrBuild\configure.log" -Tail 30; exit 1 }
}
ninja -C $RdrBuild -j $Jobs -k 0 *> "$RdrBuild\build.log"
"ninja exit=$LASTEXITCODE tempo=$((Get-Date) - $t)"
$l = Get-Content "$RdrBuild\build.log"
"FAILED: $(@($l | Select-String '^FAILED:').Count)"
$l | Select-String ': (fatal )?error:' | Select-Object -First 25 | ForEach-Object { $_.Line }
$l | Select-String 'undefined symbol|duplicate symbol' | Select-Object -First 25 | ForEach-Object { $_.Line }
Get-ChildItem "$RdrBuild\*.exe" -EA SilentlyContinue | ForEach-Object { "$($_.Name) $($_.Length) $((Get-FileHash $_.FullName).Hash)" }
