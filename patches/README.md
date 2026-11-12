# Patches sobre o ps3recomp / ps3recomp patches

Arquivos do [ps3recomp](https://github.com/sp00nznet/ps3recomp) (MIT, Ned Heller / sp00nznet e colaboradores) modificados por este port. Os caminhos dentro dos patches são os do toolkit.

*The paths inside the patches are toolkit paths. `scripts/prepare_toolkit.ps1` exports v0.19.0 from a clean clone and applies the upstream-PRs patch to it (`local\ps3recomp-rdr`); `scripts/prepare_overlay.ps1` then applies the RDR patch to copies of 17 of its files (`local\overlay`). The clone itself is never modified.*

Ordem / order: `v0.19.0` (`ae92407`) → `ps3recomp-v0.19.0-upstream-prs.patch` → `ps3recomp-v0.19.0-rdr.patch`.

## `ps3recomp-v0.19.0-upstream-prs.patch`

Doze PRs ainda abertos no ps3recomp, mesclados sobre a v0.19.0, sem mudanças nossas além da resolução de um conflito. Código dos autores de cada PR, sob a licença MIT do ps3recomp. Ficaram de fora só a documentação (`*.md`) e os workflows do GitHub.

*Twelve still-open ps3recomp PRs merged on top of v0.19.0, unchanged except for one conflict resolution. The code belongs to each PR's author, under ps3recomp's MIT licence. Only documentation (`*.md`) and GitHub workflows were left out.*

| PR | O que faz / what it does |
| :--- | :--- |
| sp00nznet/ps3recomp#746 | backend Vulkan compilável no Windows (opt-in, `PS3RECOMP_RSX_VULKAN`) |
| sp00nznet/ps3recomp#754 | Vulkan: unidade de textura sem nada ligado lê preto transparente |
| sp00nznet/ps3recomp#702 | Vulkan: polygon offset do guest |
| sp00nznet/ps3recomp#736 | Vulkan: relatório de FPS (`PS3RECOMP_VK_FPS=1`) |
| sp00nznet/ps3recomp#738 | Vulkan: apresentação direta (`PS3RECOMP_VK_DIRECT_PRESENT=1`) |
| sp00nznet/ps3recomp#764 | D3D12: a espera da GPU só desiste com o dispositivo removido |
| sp00nznet/ps3recomp#713 | `rsx_live_draw`: esperas de fence validadas |
| sp00nznet/ps3recomp#759 | filas de evento publicadas só depois de inicializadas |
| sp00nznet/ps3recomp#758 | cada contexto de reserva do PPU registrado uma vez |
| sp00nznet/ps3recomp#760 | HLE rápido guarda o TOC do chamador |
| sp00nznet/ps3recomp#761 | ponto de retorno do drain limpo no reinício do driver SPU |
| sp00nznet/ps3recomp#601 | divisão por zero do fragment program sem NaN (o conflito com a v0.19.0 no `OP_RCP` foi resolvido mantendo `DDX`/`DDY`) |

Neste port o Vulkan fica desligado: o build usa o `rsx_live_draw` com Direct3D 12 (ver [docs/STATUS.md](../docs/STATUS.md), tentativa 82).

## `ps3recomp-v0.19.0-rdr.patch`

Base: a v0.19.0 com o patch acima. Inclui ainda o merge dos PRs abertos sp00nznet/ps3recomp#701 (TXD no decompilador de fragment program), sp00nznet/ps3recomp#665 (feedback por alias) e sp00nznet/ps3recomp#662 (vértices imediatos).

| Arquivo | O que muda |
| :--- | :--- |
| `libs/spurs/cellSpurs.c` | `cellSpursQueuePopBody`; `_cellSpursSemaphoreInitialize`; `argTaskset` guardado no atributo; jobs da mesma cadeia em paralelo até `maxContention` (`SPURS_JC_PARALLEL=1`, sp00nznet/ps3recomp#712); PC persistente das job chains e `Run` que chega no fim da volta não se perde (contador `kicks`); `JobGuard` atômico; pontes `rdr2_spu_*` para as chamadas SPURS feitas pelo job `C895` (**específico do jogo**) |
| `libs/spurs/cellFiber.c` | reuso de um `CellFiberPpu` de fiber já terminado |
| `libs/video/cellGcmSys.c` | cópias NV0039 (memória a memória) do subcanal 1 executadas (`GCM_SUBCH1_M2MF=1`; o áudio do stream depende delas); salto da "segment tail word" que o job SPU deixa no fim de cada segmento de 8 KB do FIFO (**específico do jogo**); destino do `GET_REPORT` (`CELL_GCM_CONTEXT_DMA_REPORT_LOCATION_MAIN` relativo ao IO) |
| `libs/system/cellSysutil.c` | `cellSysutilGetBgmPlaybackStatus` com os valores do PS3 (`PLAY = 0`, `STOP = 1`; `ENABLE = 0`, `DISABLE = 1`): com os do toolkit o jogo achava que havia música do XMB tocando e mutava os vídeos Bink |
| `libs/video/rsx_live_draw.c` | `MAX_SURFACES` 64 → 512; PRs sp00nznet/ps3recomp#665 e sp00nznet/ps3recomp#662 |
| `libs/video/rsx_fp_decompiler.c` | PR sp00nznet/ps3recomp#701 |
| `libs/misc/cellAvconfExt.c` | `PS3_AUDIO_OUT_CH` = 2, 6 ou 8 canais |
| `runtime/ppu/ppu_fs.cpp` | `cellFsReadWithOffset`/`WriteWithOffset` (sp00nznet/ps3recomp#715); `cellFsAllocateFileAreaWithoutZeroFill` que estende o arquivo (sp00nznet/ps3recomp#714, com `port/src/fs_area.c`) |
| `runtime/ppu/ppu_sysprx.cpp` | marcador de livre `LWM_FREE` no `sys_lwmutex`/`lwcond` |
| `runtime/spu/spurs_job.c` | contexto de job por thread; menos cópias do LS por job; `oBuffer` de jobs *in-out*; contexto do kernel SPURS (`spuNum` em LS `0x1C8`, tag de DMA) em todo job, não só nos "JOBCRT Ver13" |
| `runtime/spu/spu_channels.c`, `spu_drain.c` | código SPU carregado em tempo de execução roda como chamada (`SPU_INTERP_UNLIFTED=1`) |
| `runtime/spu/spu_context.h` | sondas de LS (`SPU_LS_PROBES`, desligadas) |
| `runtime/syscalls/sys_ppu_thread.c` | `PPU_PRIO_ABOVE=<n>`: thread do guest com prioridade menor que `n` em `THREAD_PRIORITY_ABOVE_NORMAL` (o Multistream, 2033, acordava do `usleep(800)` com até 228 ms de atraso) |
| `runtime/syscalls/sys_semaphore.h` | `SYS_SEMAPHORE_MAX` 256 → 2048 |
| `runtime/syscalls/sys_timer.c` | `PS3_USLEEP_WAIT_US`: `usleep` longo sem girar a CPU (sp00nznet/ps3recomp#628); espera limitada a `usec/1000 + 2` ms, porque o timer de alta resolução do Windows às vezes não dispara (sono de até 17 s; `USLEEP_CAP=0` desliga) |

`sys_semaphore.c` entra no overlay sem mudança (precisa do `sys_semaphore.h` ao lado).

Fora dos patches, em `port/`: a saída do EcoQoS do Windows 11 (`main.cpp`; `PS3_ECOQOS=1` mantém) e o float rápido das unidades de áudio (`src/audio_float/spu_helpers.h`, ligado pelo `CMakeLists.txt`).

## `ps3recomp-v0.18.0-ppu_lifter.patch`

Base: tag `v0.18.0`, commit `4e8f3ca`. Em `tools/ppu_lifter.py` (`discover_jump_tables`): reconhece a base constante `lis` + `addic` (sem TOC) dos dois interpretadores de bytecode do jogo e prefere o `lwzx` que alimenta o `mtctr`. Com ele, 192 de 192 despachos resolvidos (antes, 12). Três testes novos em `tools/test_ppu_jumptables.py`.

## Regras

- Só código do toolkit e código nosso. Nada traduzido do jogo nem do firmware.
- Correção genérica vai também para o ps3recomp, um PR por mudança, com teste. Os itens marcados como específicos do jogo não vão como estão.
- Para regenerar o patch do RDR: `git diff` entre os arquivos do toolkit com os PRs e o overlay, com fim de linha LF. O dos PRs: `git diff ae92407 <merge dos PRs> -- . ':(exclude)*.md' ':(exclude).github'`.
