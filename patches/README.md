# Patches sobre o ps3recomp / ps3recomp patches

Arquivos do [ps3recomp](https://github.com/sp00nznet/ps3recomp) (MIT, Ned Heller / sp00nznet) modificados por este port. Os caminhos dentro dos patches são os do toolkit, então eles também aplicam direto num clone (`git apply`).

*The paths inside the patches are toolkit paths, so they also apply directly to a checkout with `git apply`. `scripts/prepare_overlay.ps1` applies the v0.19.0 patch to copies instead, leaving the checkout clean.*

## `ps3recomp-v0.19.0-rdr.patch`

Base: tag `v0.19.0`, commit `ae92407`. Inclui o merge dos PRs abertos sp00nznet/ps3recomp#701 (TXD no decompilador de fragment program), sp00nznet/ps3recomp#665 (feedback por alias) e sp00nznet/ps3recomp#662 (vértices imediatos).

| Arquivo | O que muda |
| :--- | :--- |
| `libs/spurs/cellSpurs.c` | `cellSpursQueuePopBody`; `_cellSpursSemaphoreInitialize`; `argTaskset` guardado no atributo; jobs da mesma cadeia em paralelo até `maxContention` (`SPURS_JC_PARALLEL=1`, sp00nznet/ps3recomp#712); `JobGuard` atômico; pontes `rdr2_spu_*` para as chamadas SPURS feitas pelo job `C895` (**específico do jogo**) |
| `libs/spurs/cellFiber.c` | reuso de um `CellFiberPpu` de fiber já terminado |
| `libs/video/cellGcmSys.c` | salto da "segment tail word" que o job SPU deixa no fim de cada segmento de 8 KB do FIFO (**específico do jogo**); destino do `GET_REPORT` (`CELL_GCM_CONTEXT_DMA_REPORT_LOCATION_MAIN` relativo ao IO) |
| `libs/video/rsx_live_draw.c` | `MAX_SURFACES` 64 → 512; PRs sp00nznet/ps3recomp#665 e sp00nznet/ps3recomp#662 |
| `libs/video/rsx_fp_decompiler.c` | PR sp00nznet/ps3recomp#701 |
| `libs/misc/cellAvconfExt.c` | `PS3_AUDIO_OUT_CH` = 2, 6 ou 8 canais |
| `runtime/ppu/ppu_fs.cpp` | `cellFsReadWithOffset`/`WriteWithOffset` (sp00nznet/ps3recomp#715); `cellFsAllocateFileAreaWithoutZeroFill` que estende o arquivo (sp00nznet/ps3recomp#714, com `port/src/fs_area.c`) |
| `runtime/ppu/ppu_sysprx.cpp` | marcador de livre `LWM_FREE` no `sys_lwmutex`/`lwcond` |
| `runtime/spu/spurs_job.c` | contexto de job por thread; menos cópias do LS por job; `oBuffer` de jobs *in-out* |
| `runtime/spu/spu_channels.c`, `spu_drain.c` | código SPU carregado em tempo de execução roda como chamada (`SPU_INTERP_UNLIFTED=1`) |
| `runtime/spu/spu_context.h` | sondas de LS (`SPU_LS_PROBES`, desligadas) |
| `runtime/syscalls/sys_semaphore.h` | `SYS_SEMAPHORE_MAX` 256 → 2048 |
| `runtime/syscalls/sys_timer.c` | `PS3_USLEEP_WAIT_US`: `usleep` longo sem girar a CPU |

`sys_semaphore.c` entra no overlay sem mudança (precisa do `sys_semaphore.h` ao lado).

## `ps3recomp-v0.18.0-ppu_lifter.patch`

Base: tag `v0.18.0`, commit `4e8f3ca`. Em `tools/ppu_lifter.py` (`discover_jump_tables`): reconhece a base constante `lis` + `addic` (sem TOC) dos dois interpretadores de bytecode do jogo e prefere o `lwzx` que alimenta o `mtctr`. Com ele, 192 de 192 despachos resolvidos (antes, 12). Três testes novos em `tools/test_ppu_jumptables.py`.

## Regras

- Só código do toolkit e código nosso. Nada traduzido do jogo.
- Correção genérica vai também para o ps3recomp, um PR por mudança, com teste. Os itens marcados como específicos do jogo não vão como estão.
- Para regenerar o patch: `git diff --no-index` entre os arquivos da tag e o overlay, com fim de linha LF.
