# Resume <boots>\<tag>.pilhas (scripts\boot_seguro.ps1 -Sonda): uma linha por thread, com os nomes das funcoes.
# Summarises a stack capture: one line per thread with symbol names.
param([string]$Tag, [int]$Quadros = 6, [string]$Exe = "")
. "$PSScriptRoot\..\..\scripts\config.ps1"
$exe = if ($Exe) { $Exe } else { "$RdrBuild\MyGameRecomp.exe" }
$nm = "$env:TEMP\rdr2_nm.txt"
& (Get-RdrTool 'llvm-nm.exe') --defined-only -n $exe 2>$null | Out-File -Encoding ascii $nm
$py = 'python'
$e = Get-Content "$RdrBoots\$Tag.err"
$nomes = @{}; $pend = @{}
foreach ($l in $e) {
  if ($l -match 'sys_ppu_thread_create tid=(\d+) name="([^"]*)"') { $pend[$Matches[1]] = $Matches[2] }
  elseif ($l -match '\[THREAD (\d+)\] host thread started.*hosttid=(\d+)') { $nomes[$Matches[2]] = $pend[$Matches[1]] }
}
$s = Get-Content "$RdrBoots\$Tag.pilhas"
$rvas = @($s | ForEach-Object { if ($_ -match 'MyGameRecomp\+0x([0-9A-F]+)') { $Matches[1] } } | Select-Object -Unique)
$mapa = @{}
if ($rvas.Count) { & $py -I "$PSScriptRoot\rva2sym.py" $nm 140000000 @rvas | ForEach-Object { $x = $_ -split ': ',2; $mapa[$x[0]] = $x[1] } }
$cpu = @{}
foreach ($l in $s) { if ($l -match '^thread (\d+): (\d+)%') { $cpu[$Matches[1]] = $Matches[2] } }
$tid = ''; $fr = @()
function Linha {
  if (-not $tid) { return }
  $g = @($fr | Where-Object { $_ -notmatch '^(ntdll|KERNEL|ucrtbase|msvcp|BaseThread)' -and $_ -notmatch 'ps3_indirect_call|ppu_host_thread|ppu_thread_entry|lv2_try|lv2_syscall|ps3_hle_call' } |
    ForEach-Object { ($_ -replace '\+0x[0-9A-F]+$','' -replace '_Z13func_','f_' -replace 'P11ppu_context','' -replace 'spu_[0-9a-f]{64}_','' -replace 'spujob_([0-9A-F]{4})[0-9A-F]+_\d+_spu_func_','j$1_') } | Select-Object -First $Quadros)
  if ($g.Count -eq 0) { return }
  $t = $g -join ' < '
  if ($t -match '^(spurs_pm_worker|spurs_kernel_thread|audio_mix_thread_func|ps3_stdio_flusher)') { return }
  "{0,3}% {1,-28} {2}" -f $cpu[$tid], ($nomes[$tid] + ''), $t.Substring(0,[Math]::Min(130,$t.Length))
}
foreach ($l in $s) {
  if ($l -match '^=== thread (\d+):') { Linha; $tid = $Matches[1]; $fr = @() }
  elseif ($l -match 'MyGameRecomp\+0x([0-9A-F]+)') { $fr += $mapa[$Matches[1]] }
  elseif ($l -match '^\s+(\S+)') { $fr += $Matches[1] }
}
Linha
