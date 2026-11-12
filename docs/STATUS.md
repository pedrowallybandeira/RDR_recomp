# Estado do port / Status

*Resumo do diário de tentativas do autor (83 tentativas, outubro–novembro de 2026). English summary at the end.*

## Onde está (2026-11-12)

Build adotado: ps3recomp v0.19.0 + 12 PRs abertos do toolkit (`patches/ps3recomp-v0.19.0-upstream-prs.patch`) + `patches/ps3recomp-v0.19.0-rdr.patch` (que já inclui os PRs sp00nznet/ps3recomp#701, sp00nznet/ps3recomp#665 e sp00nznet/ps3recomp#662). Lift feito com o lifter da v0.18.0 + `patches/ps3recomp-v0.18.0-ppu_lifter.patch`.

Boot de regressão (200 s, `boot_seguro.ps1`, `PAD_SCRIPT` até a cena):

| Medida | Valor |
| :--- | :--- |
| Telas iniciais | ~58 FPS |
| Tela título | 5,3–6,8 FPS |
| Primeira cena 3D | a partir de ~115–120 s, **3,5–10 FPS** (a maior parte entre 4 e 6) |
| Áudio | contínuo: abertura (vídeos Bink), tela título e cena; 0–1% de blocos mudos fora das transições |
| Jobs SPU sem tradução (`dispatch MISS`) | 0 |
| Memória privada (pico) | ~2,2 GB |

**Áudio funcionando** desde a tentativa 79: música, ambiente (cigarras, pássaros, vento) e os vídeos da abertura. Foram sete correções independentes (ver a linha do tempo, tentativas 67–78).

O que não funciona:

- **Desempenho:** ~6 FPS na tela título e 4–6 na cena; o jogo é limitado pela CPU. Num experimento com o sp00nznet/ps3recomp#632 (`SPU_FLOAT_RZ=1`: float do SPU nativo e exato em x86), a tela título foi a **29–44 FPS** numa rodada; a cena não mudou, e o jogo travou na cena aos 175 s. Ainda não entrou no build.
- **Imagem:** a cena é desenhada com defeitos (cintilação, elementos que somem, trechos escuros).
- **Backend Vulkan:** testado no Windows (tentativa 82, com o sp00nznet/ps3recomp#746). Desenha as telas 2D e a tela título, mas o 3D sai em polígonos chapados e o jogo cai para ~1,5 FPS na tela título. O motor `rsx_live_draw` com Direct3D 12 continua sendo o renderer.
- **Estabilidade:** o PC hospedeiro já congelou em boots longos; por isso o jogo só roda por `boot_seguro.ps1`, com vigia independente. A passagem da abertura para a tela título às vezes para por alguns segundos.
- **Entrada:** só XInput; um gamepad USB genérico não aparece, e o teclado só funciona com a porta 0 vazia.

## Linha do tempo

| Tentativas | Marco | Correção principal |
| :--- | :--- | :--- |
| 1–2 | 192/192 despachos de `bctr` resolvidos no lift | lifter: base constante `lis`+`addic` dos interpretadores de bytecode, `lwzx` que alimenta o `mtctr` |
| 3–5 | primeiro link (~290 MB) | flags do MinGW (`_WIN32_WINNT`, `-fms-extensions`, bibliotecas D3D12) |
| 6–9 | primeiro boot, janela e 6 SPUs | `LWM_FREE` no `sys_lwmutex`; argumento do taskset na SPURS; `PARAM.SFO` lido no boot; 18 programas SPU do ELF traduzidos |
| 10–15 | dados carregados (`.rpf`, `rdr2_ult.sdat`, cache em disco) | `cellFsReadWithOffset`/`WriteWithOffset` (sp00nznet/ps3recomp#715) |
| 16–20 | execução contínua por 10 min | `SYS_SEMAPHORE_MAX` 256 → 2048; jobs SPU carregados dos dados capturados e traduzidos |
| 21–22 | **primeira imagem**: telas legal e do Social Club, vídeo Bink do logo | motor `rsx_live_draw` (D3D12) |
| 23–25 | primeiro congelamento do PC; boot protegido; de 0,9 para 42 FPS nas telas iniciais | log detalhado desligado (`PS3_VERBOSE=0`) |
| 26–38 | threads estáveis; `Press Start` em 15,5 s | `cellSpursQueuePopBody`, `cellKbRead`, PC persistente nas job chains, jobs EDGE |
| 39 | **tela título** | `oBuffer` dos jobs *in-out* |
| 40–45 | fim do congelamento perto de 20 s | destino do `GET_REPORT`; trechos de overlay do job `7639` embutidos na imagem traduzida |
| 46–48 | **menu principal, dificuldade, `Loading...`** | pacotes de DLC no VFS |
| 49–52 | carga até `Exodus in America`; menus de ~1,5 para ~8 FPS | AVX2 nos fontes SPU; reuso de fiber; `_cellSpursSemaphoreInitialize` |
| 53–54 | **primeira cena 3D** (~3 FPS); laço infinito na lista de vozes | MP3 do Multistream; sonda `[t54]` em `func_0066BEA8` |
| 55–60 | cena estável a 5,5–6,4 FPS | PRs do toolkit; menos cópias por job; jobs da mesma cadeia em paralelo (sp00nznet/ps3recomp#712); contexto de job por thread |
| 61 | `cache.dat` (1,75 GB) sobrevive entre boots | `cellFsAllocateFileAreaWithoutZeroFill` de verdade (sp00nznet/ps3recomp#714); saída estéreo (`PS3_AUDIO_OUT_CH`) |
| 62 | áudio decodificado existe, mixagem lê zeros | diagnóstico |
| 63–66 | base migrada para a ps3recomp v0.19.0; cena desenhada mais correta | merge das mudanças; PRs abertos de render |
| 67 | **primeiro som** e câmera trocando de plano | cópias NV0039 (memória a memória do RSX, subcanal 1; `GCM_SUBCH1_M2MF=1`): a bandeira de pronto da voz de stream vem por elas |
| 68–69 | som picotado separado em dois defeitos do runtime | linha do tempo com `PS3_FTRACE`: o mixer do Multistream entregava 6,8 de 187,5 blocos/s |
| 70 | passada do mixer de ~170 ms para ~7 ms | decodificador MP3 (`flashMP3.pic`, carregado em LS `0x1A100`) traduzido em vez de interpretado (`analysis/tools/lift_mp3.py`; o resultado fica local) |
| 72 | `usleep(800)` do Multistream de 228 ms para ~1 ms | `PPU_PRIO_ABOVE=2040`: threads do guest com prioridade alta em `ABOVE_NORMAL` |
| 73 | buracos no som somem | o processo sai do EcoQoS do Windows 11 (`SetProcessInformation`) |
| 75–76 | som que sumia depois de alguns segundos | o timer de alta resolução do Windows às vezes não dispara (sono de até 17 s): espera do `usleep` limitada |
| 77 | sem buracos com a música da tela título tocando | float nativo (no máximo 1 ulp) só nas unidades de áudio (`port/src/audio_float`) |
| 78 | **som dos vídeos da abertura** | `cellSysutilGetBgmPlaybackStatus` com os valores do PS3: o toolkit dizia ao jogo que havia música do XMB tocando, e o jogo mutava os vídeos Bink |
| 79 | **áudio completo** no build adotado | as correções 67–78, sem sondas |
| 81 | 12 PRs abertos do ps3recomp na base | Vulkan no Windows (#746, #754, #702, #736, #738) e estabilidade (#764, #713, #759, #758, #760, #761, #601) |
| 82 | primeiro boot com Vulkan | telas 2D e tela título; 3D chapado, ~1,5 FPS |
| 83 | tela título a 29–44 FPS (experimento, uma rodada) | sp00nznet/ps3recomp#632 com `SPU_FLOAT_RZ=1` |

## Próximos passos

1. Desempenho: confirmar o #632 (rodadas de controle, travamento na cena) e testar os outros PRs de desempenho do toolkit um por vez.
2. Imagem: os defeitos da cena no `rsx_live_draw`.
3. Mandar ao ps3recomp as correções genéricas de áudio: estado do BGM do `cellSysutil`, saída do EcoQoS, espera limitada do `usleep` (junto do sp00nznet/ps3recomp#628) e `PPU_PRIO_ABOVE`.
4. Lifter: despachos `BRANCH-TO-N unresolved` restantes.

## Pendências conhecidas

- `cellSpursTaskGenerateLsPattern`, `cellSpursTaskGetLoadableSegmentPattern` e `cellSpursEnableExceptionEventHandler` sem handler.
- Faltam testes unitários para `LWM_FREE`, argumentos do taskset, `ReadWithOffset`/`WriteWithOffset` e o limite de semáforos.
- O patch do RDR inclui ajustes específicos deste jogo (o salto da "segment tail word" no FIFO em `cellGcmSys.c`, as pontes `rdr2_spu_*` em `cellSpurs.c`) que não devem ir para o toolkit como estão.

---

## English summary

**Where it is (2026-11-12):** ps3recomp v0.19.0 plus 12 open upstream PRs (Vulkan on Windows and stability fixes) plus this repository's patch, lifted with the v0.18.0 lifter plus the jump-table patch. A 200 s regression boot runs the intro screens at ~58 FPS, the title screen at 5.3–6.8 FPS, and reaches the **first 3D cutscene** after ~115–120 s at 3.5–10 FPS (mostly 4–6), with zero untranslated SPU jobs and ~2.2 GB peak private memory.

**Audio works** (attempt 79): music, ambience and the intro Bink videos. It took seven independent fixes: executing the RSX NV0039 memory-to-memory copies on subchannel 1; lifting the Multistream's runtime-loaded MP3 decoder (`flashMP3.pic`, from your own firmware; the output stays local); raising high-priority guest threads to `ABOVE_NORMAL`; leaving Windows 11 EcoQoS and bounding the `usleep` wait (the high-resolution timer sometimes never fires); native float in the audio units only; and reporting the XMB BGM playback status with the PS3's values (the toolkit told the game user music was playing, so it muted the videos).

**Not working yet:** performance is CPU-bound (~6 FPS at the title, 4–6 in the scene). An experiment with sp00nznet/ps3recomp#632 (`SPU_FLOAT_RZ=1`) ran the title screen at 29–44 FPS in one run, but the scene did not change and the game hung there at 175 s; it is not in the build yet. The scene still renders with defects. The Vulkan backend (via #746) draws the 2D screens and the title screen on Windows, but 3D comes out as flat polygons at ~1.5 FPS, so `rsx_live_draw` on Direct3D 12 stays the renderer. The host PC has frozen on long boots, so only run the game through the guarded boot script. Input is XInput only.

**Next:** confirm #632 and try the other upstream performance PRs one at a time, fix the scene's rendering defects, and upstream the generic audio fixes.
