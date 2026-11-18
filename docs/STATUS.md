# Estado do port / Status

*Resumo do diário de tentativas do autor (140 tentativas, outubro–novembro de 2026). English summary at the end.*

## Onde está (2026-11-17)

Build adotado (v19): ps3recomp v0.19.0 + 12 PRs abertos do toolkit (`patches/ps3recomp-v0.19.0-upstream-prs.patch`) + `patches/ps3recomp-v0.19.0-rdr.patch` (que já inclui os PRs sp00nznet/ps3recomp#701, sp00nznet/ps3recomp#665 e sp00nznet/ps3recomp#662). Lift feito com o lifter da v0.18.0 + `patches/ps3recomp-v0.18.0-ppu_lifter.patch`. 29 jobs SPU traduzidos (`spu/images.json`).

Boot de conferência (`seg343`, 600 s, visível, jogado com o controle de Xbox):

| Medida | Valor |
| :--- | :--- |
| Abertura | vídeos Bink com som, tela título, carga, cutscene do trem (20–30 FPS) |
| Parte jogável | Armadillo: andar, correr, subir na caixa d'água, pular de telhados, atirar, brigar, autosave |
| FPS na rua | mediana 5,5 (4–10 conforme a cena; até ~1 FPS por ~15 s em cenas com 17 mil desenhos) |
| Pisca de cor de um quadro | nenhum |
| Jobs SPU sem tradução (`dispatch MISS`) | 0 |
| Memória privada (pico) | ~2,5 GB |

**Jogável na cidade** desde a tentativa 85; **combate** (soco, tiro, mortes) desde a 113; **primeira missão** iniciada na 114 (entrar no saloon); **controle de Xbox** funcionando.

O que não funciona:

- **Desempenho:** limitado pela CPU (4–10 FPS na rua). A thread do FIFO/live draw fica ~90% ocupada, sobretudo montando vértices e lendo o FIFO.
- **Imagem:** no build adotado a cena só tem luz ambiente: sem sol, sem sombra, superfícies chapadas. Em experimento (tentativas 134–135) a luz voltou: a passada de luz lê a profundidade da cena como textura A8R8G8B8, e o live draw entregava a memória do PS3 (zeros); uma cópia da profundidade do host no formato D24S8 trouxe sol, névoa, reflexos na água e feixes de luz. A sombra projetada ainda não aparece: o atlas de sombra do mundo (1200×1200) só recebe a primeira de quatro cascatas (tentativas 136–140, em diagnóstico). Vegetação ao longe sai em blocos escuros de escadinha; o chão sai borrado.
- **Cutscene:** às vezes a carga de uma cutscene para com um taskset SPURS esperando em `WAIT_SIGNAL` (sempre, com as cadeias de jobs em série).
- **Estabilidade:** o PC hospedeiro já congelou em sessões longas de boots seguidos; o jogo só roda por `boot_seguro.ps1`, com vigia independente.

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
| 84 | cena de 5,1–5,5 para 7,2–8,2 FPS | índices de hash para texturas e superfícies; envio parcial da lista de comandos sem esperar a GPU |
| 85 | **primeira vez jogável**: John Marston anda pela cidade | teclado mapeado para o controle (experimento) |
| 86–93 | defeitos da cena medidos | registro desenho a desenho, RenderDoc dentro do port, referência do RPCS3 (só leitura); recorte de profundidade do RSX (experimento) |
| 94–101 | origem das rajadas de vértices quebrados | o job da grama usa um anel de vértices por SPU, e a cadeia só pode rodar nas SPUs da sua tabela de prioridade (`JC_SPU_PRIO`, sp00nznet/ps3recomp#803) |
| 102–107 | as rajadas restantes somem; controle de Xbox funcionando | reserva de SPU e aviso de fim de job em ordem no modo paralelo (`JC_SPU_ORDER`, `JC_DONE_ORDER`) |
| 108–110 | **combate sem congelar** | inanição da SPU 0 (`JC_SPU_FAIR`) |
| 111–113 | tiro que acerta e mortes funcionam | o job SPU de 93 KB que faltava, traduzido (29 jobs) |
| 114 | **primeira missão iniciada** (entra no saloon) | — |
| 115–131 | **fim do pisca de cor de um quadro** | o remendo do FIFO que pulava a palavra do fim dos segmentos de 8 KB pulava também a CALL da rotina de vertex program do material seguinte; agora só pula o que não é CALL/RET (`GCM_TAIL_KEEP_CALL`) |
| 132–133 | build adotado: v19 | 84 + 101–113 + 131, sem sondas; conferência sem pisca nem travamento |
| 134–135 | **sol, névoa e reflexos** (experimento) | profundidade lida como A8R8G8B8 vem de uma cópia da profundidade do host (bytes D24S8 big-endian, *remap* da textura) |
| 136–140 | sombra projetada ainda ausente (em diagnóstico) | comparação de profundidade do RSX ligada; o atlas de sombra só recebe a primeira cascata |

## Próximos passos

1. Imagem: adotar a correção da luz (134–135); fazer o atlas de sombra receber as quatro cascatas (138–140); vegetação em blocos; chão borrado (anisotropia e LOD bias).
2. A parada na carga de cutscenes (`WAIT_SIGNAL`).
3. Desempenho: a thread do FIFO/live draw (montagem de vértices, leitura do FIFO); os PRs de desempenho do toolkit, um por vez.
4. Mandar ao ps3recomp as correções genéricas: as das cadeias de jobs (sp00nznet/ps3recomp#712 e sp00nznet/ps3recomp#803), o estado do BGM do `cellSysutil`, as cópias NV0039 e a espera limitada do `usleep`.

## Pendências conhecidas

- `cellSpursTaskGenerateLsPattern`, `cellSpursTaskGetLoadableSegmentPattern` e `cellSpursEnableExceptionEventHandler` sem handler.
- Faltam testes unitários para `LWM_FREE`, argumentos do taskset, `ReadWithOffset`/`WriteWithOffset` e o limite de semáforos.
- O patch do RDR inclui ajustes específicos deste jogo (o salto da "segment tail word" no FIFO em `cellGcmSys.c`, as pontes `rdr2_spu_*` em `cellSpurs.c`) que não devem ir para o toolkit como estão.
- Os logs `[tail-keep]` e `segment tail word` são amostrados (as 8 primeiras linhas e uma a cada 1.024): contar linhas subestima os eventos.

---

## English summary

**Where it is (2026-11-17):** build v19 = ps3recomp v0.19.0 plus 12 open upstream PRs plus this repository's patch, lifted with the v0.18.0 lifter plus the jump-table patch; 29 SPU jobs lifted. A 600 s check boot (`seg343`, played with an Xbox controller) goes through the intro videos (with sound), the title screen and the train cutscene (20–30 FPS) into **Armadillo, which is playable**: walking, running, climbing, jumping off roofs, shooting, melee and autosave all work, and the **first mission starts** (go to the saloon). Town runs at a median of 5.5 FPS (4–10 depending on the scene), with zero untranslated SPU jobs and ~2.5 GB peak private memory.

**Fixed since the last update:** SPURS job chains in parallel mode now honor each chain's SPU priority table, reserve SPUs and signal job completion in order, and no longer starve SPU 0 (this removed corrupted grass vertices and a freeze in combat); the last missing 93 KB SPU job is lifted; the **one-frame color flicker is gone** (our own FIFO workaround skipped the word at the end of 8 KB command segments, and that word was often a legit CALL to the next material's vertex-program routine); hash indices for texture/surface lookups and partial command-list submission without waiting on the GPU (~+40% in cutscenes).

**Not working yet:** performance is CPU-bound (the FIFO/live-draw thread is ~90% busy). In the adopted build the scene has ambient light only. In an experiment the sun, fog, water reflections and light shafts are back: the light pass reads the scene depth as an A8R8G8B8 texture, which used to fall back to guest memory (zeros); it now gets a copy of the host depth in the big-endian D24S8 layout. Cast shadows are still missing: the world shadow atlas (1200x1200) only receives the first of four cascades (under investigation). Distant vegetation renders as dark blocky shapes and the ground is blurry. Loading a cutscene sometimes hangs with a SPURS taskset in `WAIT_SIGNAL`. The host PC has frozen during long series of boots, so only run the game through the guarded boot script.

**Next:** adopt the lighting fix, get all four shadow cascades into the atlas, fix the vegetation and the ground textures, the cutscene hang, then performance; upstream the generic job-chain and audio fixes.
