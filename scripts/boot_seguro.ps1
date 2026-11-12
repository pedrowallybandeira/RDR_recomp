# Roda o jogo com travas de seguranca e um monitor gravado direto no disco.
# O jogo fica em prioridade baixa, sem acesso a alguns nucleos, e e encerrado
# sozinho se memoria, threads ou tempo passarem dos limites. Um cmd.exe de
# prioridade alta, independente do monitor, mata o jogo pelo PID em Segundos+45.
#
# Runs the game with safety limits and a monitor written straight to disk: low
# priority, some cores left free, killed when memory, threads or time exceed the
# limits, plus an independent watchdog. Do not run the game without it: an
# unguarded run froze the host PC once.
#
# uso: scripts\boot_seguro.ps1 -Tag <nome> [-Segundos 330] [-Exe <outro exe>] [-Visivel]
param(
  [string]$Exe = "",
  [string]$Tag = 'segura',
  [int]$Segundos = 300,
  [switch]$Visivel,
  [int]$NucleosLivres = 4,
  [int]$LimiteMemMB = 9000,
  [int]$MinLivreMB = 2500,
  [int]$LimiteThreads = 200,
  [int[]]$Amostras = @(),
  [int]$Sonda = 0
)
. "$PSScriptRoot\config.ps1"
$exe = if ($Exe) { $Exe } else { "$RdrBuild\MyGameRecomp.exe" }
$elf = $RdrElf
$out = $RdrBoots
# Amostrador de pilhas (analysis\tools\hsamp_tudo.c), usado com -Sonda.
$hsamp = if ($env:RDR_HSAMP) { $env:RDR_HSAMP } else { "$RdrBuild\hsamp_tudo.exe" }
New-Item -ItemType Directory -Force -Path $out | Out-Null
if (-not $env:PS3_VFS_ROOT) { $env:PS3_VFS_ROOT = $RdrVfs -replace '\','/' }
if (-not $env:RSX_LIVE_DRAW) { $env:RSX_LIVE_DRAW = '1' }
# Com stderr redirecionado, o toolkit liga o log detalhado sozinho, e a disputa
# pela trava do stderr derrubou o jogo para menos de 1 FPS. So ligue para depurar.
if (-not $env:PS3_VERBOSE) { $env:PS3_VERBOSE = '0' }
if (-not $env:PS3_TITLE) { $env:PS3_TITLE = 'Red Dead Redemption' }
# Padroes adotados: jobs paralelos por cadeia, usleep longo sem girar,
# codigo SPU carregado em tempo de execucao como chamada, saida de audio estereo.
if (-not $env:SPURS_JC_PARALLEL) { $env:SPURS_JC_PARALLEL = '1' }
if (-not $env:PS3_USLEEP_WAIT_US) { $env:PS3_USLEEP_WAIT_US = '500' }
if (-not $env:SPU_INTERP_UNLIFTED) { $env:SPU_INTERP_UNLIFTED = '1' }
if (-not $env:GCM_PARK_GRACE_MS) { $env:GCM_PARK_GRACE_MS = '2000' }
if (-not $env:PS3_DEV_FLASH -and (Test-Path $RdrDevFlash)) { $env:PS3_DEV_FLASH = $RdrDevFlash }
if (-not $env:PS3_AUDIO_OUT_CH) { $env:PS3_AUDIO_OUT_CH = '2' }
# Audio: copias NV0039 do RSX (a bandeira de pronto da voz de stream vem por elas) e a
# thread do Multistream (prioridade 2033) em ABOVE_NORMAL, para o usleep(800) dela acordar
# a tempo. / Audio: RSX NV0039 copies, and the Multistream thread in ABOVE_NORMAL.
if (-not $env:GCM_SUBCH1_M2MF) { $env:GCM_SUBCH1_M2MF = '1' }
if (-not $env:PPU_PRIO_ABOVE) { $env:PPU_PRIO_ABOVE = '2040' }
if (-not (Test-Path $exe)) { throw "executavel nao encontrado: $exe" }
if (-not (Test-Path $elf)) { throw "ELF nao encontrado: $elf (defina RDR_ELF)" }

Add-Type -AssemblyName Microsoft.VisualBasic
$info = New-Object Microsoft.VisualBasic.Devices.ComputerInfo
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = [System.Diagnostics.ProcessPriorityClass]::AboveNormal

# WriteThrough: o monitor precisa sobreviver a um reset pelo botao do gabinete.
$fs = New-Object System.IO.FileStream("$out\$Tag.mon", [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write,
  [System.IO.FileShare]::Read, 4096, [System.IO.FileOptions]::WriteThrough)
$w = New-Object System.IO.StreamWriter($fs); $w.AutoFlush = $true
$w.WriteLine("seg ws_mb privado_mb threads cpu_pct livre_mb")

$estilo = if ($Visivel) { 'Normal' } else { 'Hidden' }
$p = Start-Process -FilePath $exe -ArgumentList "`"$elf`"" -WorkingDirectory $RdrBuild -PassThru -WindowStyle $estilo `
  -RedirectStandardOutput "$out\$Tag.out" -RedirectStandardError "$out\$Tag.err"
$null = $p.Handle
$logicos = [Environment]::ProcessorCount
$usaveis = [Math]::Max(2, $logicos - $NucleosLivres)
$p.ProcessorAffinity = [IntPtr](([int64]1 -shl $usaveis) - 1)
$p.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal
# Vigia independente do monitor: um cmd.exe espera o prazo e mata o jogo pelo
# PID, sem PowerShell nem WMI. No seg183 o monitor parou aos 209 s e o jogo
# seguiu rodando sem ninguem para encerra-lo, ate o PC travar.
$prazo = $Segundos + 45
$vlog = "$out\$Tag.vigia"
$vcmd = "ping -n $($prazo + 1) 127.0.0.1 >nul & echo VIGIA disparou %DATE% %TIME% >> `"$vlog`" & " +
        "taskkill /F /PID $($p.Id) /FI `"IMAGENAME eq MyGameRecomp.exe`" >> `"$vlog`" 2>&1"
$vigia = Start-Process -FilePath "$env:SystemRoot\System32\cmd.exe" -ArgumentList "/d /c $vcmd" -WindowStyle Hidden -PassThru
try { $vigia.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::High } catch {}

$t0 = Get-Date; $motivo = ''; $picoMem = 0
$cpuAnt = [TimeSpan]::Zero; $tAnt = $t0
$fila = New-Object System.Collections.Queue; foreach ($a in $Amostras) { $fila.Enqueue($a) }
$foto = $null; $fotoSeg = 0
while (-not $p.HasExited) {
  Start-Sleep -Seconds 1
  try { $p.Refresh() } catch { break }
  if ($p.HasExited) { break }
  $agora = Get-Date
  $cpu = $p.TotalProcessorTime
  $pct = [Math]::Round(100 * ($cpu - $cpuAnt).TotalSeconds / [Math]::Max(0.1, ($agora - $tAnt).TotalSeconds) / $logicos)
  $cpuAnt = $cpu; $tAnt = $agora
  $ws = [Math]::Round($p.WorkingSet64 / 1MB); $pv = [Math]::Round($p.PrivateMemorySize64 / 1MB)
  $livre = [Math]::Round($info.AvailablePhysicalMemory / 1MB); $th = $p.Threads.Count
  if ($pv -gt $picoMem) { $picoMem = $pv }
  $seg = [Math]::Round(($agora - $t0).TotalSeconds)
  $w.WriteLine("$seg $ws $pv $th $pct $livre")
  if ($seg % 5 -eq 0) {
    $w.WriteLine("TITULO $seg $($p.MainWindowTitle)")
    # Bytes lidos do disco: separam carga lenta de carga parada.
    $w.WriteLine("IO $seg " + (Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)").ReadTransferCount)
  }
  # Coleta de pilhas de todas as threads, com hsamp_tudo.exe.
  if ($Sonda -gt 0 -and $seg -ge $Sonda) {
    $Sonda = 0
    $null = Start-Process -FilePath $hsamp -ArgumentList "$($p.Id) 60 10" -WindowStyle Hidden `
      -RedirectStandardOutput "$out\$Tag.pilhas" -RedirectStandardError "$out\$Tag.pilhas.err"
  }
  # CPU por thread em 5 s; o id casa com o hosttid das linhas [THREAD n] do .err.
  if ($foto) {
    if ($seg -ge $fotoSeg + 5) {
      $d = foreach ($t in $p.Threads) { try { if ($foto.ContainsKey($t.Id)) { [pscustomobject]@{ id=$t.Id; pct=[Math]::Round(100 * ($t.TotalProcessorTime.TotalSeconds - $foto[$t.Id]) / ($seg - $fotoSeg)) } } } catch {} }
      $w.WriteLine("THREADS $fotoSeg " + (($d | Sort-Object pct -Descending | Select-Object -First 12 | ForEach-Object { "$($_.id)=$($_.pct)%" }) -join ' '))
      $foto = $null
    }
  } elseif ($fila.Count -gt 0 -and $seg -ge $fila.Peek()) {
    [void]$fila.Dequeue(); $foto = @{}; $fotoSeg = $seg
    foreach ($t in $p.Threads) { try { $foto[$t.Id] = $t.TotalProcessorTime.TotalSeconds } catch {} }
  }
  if ($pv -gt $LimiteMemMB) { $motivo = "memoria do jogo $pv MB" }
  elseif ($livre -lt $MinLivreMB) { $motivo = "memoria livre do sistema $livre MB" }
  elseif ($th -gt $LimiteThreads) { $motivo = "$th threads" }
  elseif ($seg -ge $Segundos) { $motivo = "tempo de $Segundos s" }
  if ($motivo) { break }
}
if ($motivo) {
  $w.WriteLine("PARADO: $motivo")
  Stop-Process -Id $p.Id -Force -Confirm:$false -ErrorAction SilentlyContinue
  "encerrado pelo monitor: $motivo"
} else {
  "encerrou sozinho: exit=$($p.ExitCode)"
}
# O monitor terminou: cancela o vigia (o cmd e o ping dele).
if ($vigia -and -not $vigia.HasExited) { & taskkill /F /T /PID $vigia.Id 2>&1 | Out-Null }
$w.Dispose()
"duracao=$((Get-Date) - $t0) pico_privado_mb=$picoMem"
