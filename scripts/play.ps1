# Abre o jogo com a janela visivel e as travas do boot_seguro.ps1 (30 min).
# Opens the game in a visible window with boot_seguro.ps1's limits (30 min).
param([int]$Segundos = 1800, [switch]$AteACena)
if ($AteACena -and -not $env:PAD_SCRIPT) { $env:PAD_SCRIPT = '24:0x0008,44:0x4000,64:0x4000,84:0x8000,104:0x4000' }
& "$PSScriptRoot\boot_seguro.ps1" -Tag ("jogar_" + (Get-Date -Format 'yyyyMMdd_HHmmss')) -Segundos $Segundos -Visivel
