# Arquitetura / Architecture

*Português; resumo em inglês no fim. / English summary at the end.*

## Fluxo

```
 sua cópia do jogo (BLUS30418)
        │  (você mesmo: ELF decriptado + árvore de dados aberta → local\)
        ▼
 local\game\RDR2.elf ──► ppu_loader.py ──► prep_lift.py ──► ppu_lifter.py (v0.18.0 + patch)
        │                (funções, imports)  (corta .rodata)     │
        │                                                        ▼
        │                                              local\lifted\ppu_recomp_*.cpp (66 TUs)
        │                                                        │   gera_voz.py → [t54] opcional
        ├──► PORT_SPU_INPUTS ──► build_spu_workloads.py ──► build\generated_spu (18 programas)
        │
        │    boot com SPU_DUMP_MISS / SPU_DUMP_OVL
        └──► dumps ──► lift_jobs.py / lift_dsp.py ──► local\spu_jobs (27) / local\spu_dsp (3)
 flashMP3.pic do seu firmware ──► lift_mp3.py ──► local\spu_mp3 (decodificador MP3)
                                                                 │
 ps3recomp v0.19.0 ──► prepare_toolkit.ps1 + 12 PRs ──► local\ps3recomp-rdr
                         │
                         └──► prepare_overlay.ps1 + patch ──► local\overlay (17 arquivos)
                                                                 │
                                    port\CMakeLists.txt + main.cpp ▼
                                         local\build\MyGameRecomp.exe ──► boot_seguro.ps1
```

## Modelo de execução (do ps3recomp)

- **PPU:** cada função do ELF vira uma função C++ que recebe `ppu_context*`. Memória do console num bloco de 4 GB (`vm_base`), leitura e escrita big-endian. Chamadas indiretas passam pela tabela de funções; imports viram `ps3_hle_call` por NID.
- **LV2 e bibliotecas:** syscalls e módulos do firmware (`cellFs`, `cellSpurs`, `cellGcmSys`, `cellAudio`, `cellPad`…) são HLE em C, no `runtime/` e em `libs/`.
- **SPU:** cada programa SPU traduzido roda numa thread do host com o seu LS de 256 KB; o despacho é por fingerprint do conteúdo. O que não tem tradução vai para o interpretador (`SPU_INTERP_UNLIFTED=1`) ou aparece como `dispatch MISS`.
- **SPURS:** kernel, tasksets, job chains e workloads em `libs/spurs/cellSpurs.c` e `runtime/spu/spurs_job.c`.
- **RSX:** o FIFO do GCM é percorrido no host. Este port usa o `rsx_live_draw` (NV4097 → Direct3D 12), ligado por `RSX_LIVE_DRAW=1`, porque o RDR emite `BEGIN_END` sem os métodos de desenho que o caminho padrão decodifica.

## Este port

| Peça | Onde |
| :--- | :--- |
| PRs abertos do ps3recomp usados na base | `patches/ps3recomp-v0.19.0-upstream-prs.patch` (lista em `patches/README.md`) |
| Mudanças no runtime e nas bibliotecas | `patches/ps3recomp-v0.19.0-rdr.patch` (tabela em `patches/README.md`) |
| Float rápido do áudio | `port/src/audio_float/spu_helpers.h` |
| Tabelas de salto dos interpretadores de bytecode | `patches/ps3recomp-v0.18.0-ppu_lifter.patch` |
| Executável | `port/` (motor live-draw, `PARAM.SFO`, NIDs extras, `fs_area.c`) |
| Programas SPU | `spu/images.json` (só identificadores) |
| Padrões de execução | `scripts/boot_seguro.ps1`: `SPURS_JC_PARALLEL=1`, `PS3_USLEEP_WAIT_US=500`, `SPU_INTERP_UNLIFTED=1`, `GCM_PARK_GRACE_MS=2000`, `PS3_AUDIO_OUT_CH=2`, `GCM_SUBCH1_M2MF=1`, `PPU_PRIO_ABOVE=2040`, `PS3_VERBOSE=0` |
| Build | llvm-mingw (clang), Ninja; PPU a `-O1 -fwrapv`; SPU a `-O2 -mavx2 -mfma -ffp-contract=off` |

## Fatos medidos do jogo

- **PPU:** ~68 mil funções depois da recuperação de fronteiras (28.165 funções juntas separadas pelo prólogo); 347 stubs de import; 192 despachos indiretos com 255 destinos, quase todos de dois interpretadores de bytecode (156 e 17 opcodes) cuja base é montada por `lis` + `addic`, fora do TOC.
- **SPU:** 18 programas embutidos no ELF (entre eles o `inflateServer` e o Multistream); 27 jobs SPURS carregados dos arquivos de dados, que não estão no ELF; 3 plugins DSP do Multistream carregados em LS `0x36800`. Os jobs EDGE da render chamam funções SPURS de dentro do próprio job (`C895`).
- **Arquivos:** o jogo cria `/dev_hdd1/cache.dat` com `0x6FE02000` bytes (1,75 GiB) por `cellFsAllocateFileAreaWithoutZeroFill` e confere o tamanho no boot seguinte; lê os `.rpf` por `cellFsReadWithOffset`.
- **Sincronização:** mais de 280 semáforos vivos (pool de 1024); fibers recriados sobre um `CellFiberPpu` que já terminou, a cada etapa da carga.
- **RSX:** o job SPU fecha cada segmento de 8 KB do FIFO com um `JUMP` para o próximo e deixa uma palavra inválida no fim; os relatórios (`GET_REPORT`) usam a janela de IO.
- **Áudio:** mixagem do Multistream em tempo real (~1,5 MB/s na porta), MP3 da tela título decodificado em buffers que a mixagem não lê; cópias NV0039 (memória a memória) no subcanal 1.

---

## English summary

The game's decrypted ELF (produced by the user) goes through ps3recomp's `ppu_loader.py`, `scripts/prep_lift.py` and the v0.18.0 `ppu_lifter.py` with this repo's jump-table patch, giving 66 lifted C++ translation units. The 18 SPU programs embedded in the ELF are found and lifted at configure time (`PORT_SPU_INPUTS`); the 27 SPURS jobs and 3 Multistream DSP plugins that the game loads from its data files are captured at runtime (`SPU_DUMP_MISS`, `SPU_DUMP_OVL`) and lifted by `analysis/tools/lift_jobs.py` and `lift_dsp.py`; the Multistream's MP3 decoder is lifted from your own firmware's `flashMP3.pic` by `lift_mp3.py`. The toolkit is ps3recomp v0.19.0 plus 12 open upstream PRs (`prepare_toolkit.ps1`), and seventeen of its files are patched into `local/overlay`, and `port/` links everything into `MyGameRecomp.exe`, which is only ever started by `scripts/boot_seguro.ps1`. Rendering goes through ps3recomp's `rsx_live_draw` Direct3D 12 engine. Measured facts: ~68k PPU functions, 192 indirect dispatchers from two bytecode interpreters whose table base is built with `lis`+`addic`, a 1.75 GiB disk cache sized through `cellFsAllocateFileAreaWithoutZeroFill`, 280+ live semaphores, EDGE jobs that call SPURS from inside the job, a FIFO whose 8 KB segments end in a junk word after the `JUMP`, and NV0039 memory-to-memory copies on subchannel 1 that the audio path depends on.
