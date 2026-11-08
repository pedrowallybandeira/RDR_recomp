# Estado do port / Status

*Resumo do diário de tentativas do autor (67 tentativas, outubro–novembro de 2026). English summary at the end.*

## Onde está (2026-11-08)

Build adotado: ps3recomp v0.19.0 + `patches/ps3recomp-v0.19.0-rdr.patch` (inclui os PRs abertos sp00nznet/ps3recomp#701, sp00nznet/ps3recomp#665 e sp00nznet/ps3recomp#662), lift feito com o lifter da v0.18.0 + `patches/ps3recomp-v0.18.0-ppu_lifter.patch`.

Boot de regressão (330 s, `boot_seguro.ps1`, `PAD_SCRIPT` até a cena):

| Medida | Valor |
| :--- | :--- |
| `Press Start` | ~15,4 s |
| Menus | 7–10 FPS (média 6,9 nesse boot; faixa histórica 4,7–16) |
| Primeira cena 3D | a partir de ~130–150 s, estável a **5,6–6,6 FPS** até o fim |
| Jobs SPU sem tradução (`dispatch MISS`) | 0 |
| Ressincronizações do FIFO | 0 |
| Memória privada (pico) | ~2,2 GB |

O que não funciona:

- **Áudio quase mudo.** O Multistream decodifica o MP3 da tela título, mas a mixagem nunca lê esses buffers (slots 0 e 1). Em builds experimentais que executam as cópias NV0039 (memória a memória do RSX, subcanal 1; `GCM_SUBCH1_M2MF=1`, `analysis/experiments/gera_m2mf.py`) sai som cedo, mas muito baixo e esparso: vozes de ambiente com ganhos de −70 a −130 dB, calculados pelo próprio jogo (`audVoicePsn`, `func_00623300`). Ainda não se sabe se esses ganhos são legítimos (sons distantes) nem por que a música fica fora da mixagem.
- **Cena:** nos builds experimentais mais recentes a abertura troca de plano (barco ao longe, depois o cais com a multidão); antes, a câmera ficava parada num plano só. Há cintilação, elementos que somem e, às vezes, uma faixa preta.
- **Desempenho:** ~6 FPS na cena. O gargalo principal são as job chains da SPURS e o código SPU que ainda roda no interpretador (job `297D`).
- **Estabilidade:** o PC hospedeiro congelou em dois boots longos (sem tela azul, só reset). Daí o `boot_seguro.ps1` com vigia independente. Há uma parada intermitente por volta de 23 s com o `cache.dat` já criado, que não se reproduziu em 6 boots seguidos.
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
| 67 | primeiro som (fraco) e câmera trocando de plano, em builds experimentais | NV0039 no subcanal 1 (experimento, fora do build adotado) |

## Próximos passos

1. Áudio: por que o mixer SPU não lê os slots 0 e 1 (música) e se os ganhos pequenos das vozes são legítimos; transformar o NV0039 em correção genérica para o toolkit.
2. Testar o backend Vulkan que já vem na ps3recomp v0.19.0, com o vigia, para ver se a cena desenha e se o sistema fica estável.
3. Lifter: despachos `BRANCH-TO-N unresolved` restantes.
4. Desempenho: guard e kernel da SPURS acordados por evento, prioridade da cadeia de som, menos código SPU interpretado.
5. Mandar ao ps3recomp as demais correções genéricas do patch (uma por PR, com teste).

## Pendências conhecidas

- `cellSpursTaskGenerateLsPattern`, `cellSpursTaskGetLoadableSegmentPattern` e `cellSpursEnableExceptionEventHandler` sem handler.
- Faltam testes unitários para `LWM_FREE`, argumentos do taskset, `ReadWithOffset`/`WriteWithOffset` e o limite de semáforos.
- O patch da v0.19.0 inclui ajustes específicos deste jogo (o salto da "segment tail word" no FIFO em `cellGcmSys.c`, as pontes `rdr2_spu_*` em `cellSpurs.c`) que não devem ir para o toolkit como estão.

---

## English summary

**Where it is (2026-11-08):** ps3recomp v0.19.0 plus this repository's patch (which folds in open PRs sp00nznet/ps3recomp#701, sp00nznet/ps3recomp#665 and sp00nznet/ps3recomp#662), lift made with the v0.18.0 lifter plus the jump-table patch. A 330 s regression boot reaches `Press Start` at ~15 s, menus at 7–10 FPS, and the **first 3D cutscene** after ~130–150 s, stable at **5.6–6.6 FPS**, with zero untranslated SPU jobs and zero FIFO resyncs, ~2.2 GB peak private memory.

**Not working yet:** audio is nearly silent — the title-screen MP3 is decoded but the SPU mixer never reads those buffers; experimental builds that execute the RSX NV0039 memory-to-memory copies on subchannel 1 produce a faint, sparse ambient sound (voice gains of −70 to −130 dB computed by the game itself). In the latest experimental builds the opening cutscene now changes shots (distant boat, then the crowded dock) instead of sitting on one shot; the picture still flickers and loses elements. Performance is bounded by SPURS job chains and interpreted SPU code. The host PC froze twice on long boots, hence the guarded boot script; an intermittent stall around 23 s with an existing cache did not reproduce in 6 runs. Input is XInput only.

**Milestones:** lifter jump tables (attempts 1–2) → first link and boot (3–9) → game data and file I/O (10–20) → first image via `rsx_live_draw` (21–22) → title screen (39) → no more freeze at 20 s (45) → menus and loading screen (46–52) → first 3D scene (54) → stable ~6 FPS through parallel job chains and per-thread job context (55–60) → persistent game cache (61) → migration to ps3recomp v0.19.0 (63–66) → first sound and camera cuts in experiments (67).

**Next:** audio routing in the mixer, try the Vulkan backend, remaining unresolved lifter branches, SPURS wake-ups and less interpreted SPU code, and upstreaming the generic fixes one PR at a time.
