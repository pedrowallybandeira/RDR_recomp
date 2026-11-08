# Playbook de depuração / Debugging playbook

Lições que custaram boots para aprender. *Lessons that cost boots to learn; English notes in italics.*

## Antes de rodar

- **Só por `scripts\boot_seguro.ps1`.** Dois boots longos congelaram o PC (sem tela azul, só reset). O script limita núcleos, memória privada (9 GB), memória livre (2,5 GB), threads (200) e tempo, grava um `.mon` com `WriteThrough` (sobrevive a reset) e inicia um vigia `cmd.exe` que mata o jogo em `Segundos + 45`, mesmo que o monitor PowerShell morra. Um boot por vez; espere um pouco entre boots longos. *Always boot through the guarded script; never two at once.*
- **`PS3_VERBOSE=0`.** Com stderr redirecionado o toolkit liga o log detalhado sozinho, e a disputa pela trava do stderr derrubou as telas iniciais de 42 para 0,9 FPS. Ligue só para depurar, e só por pouco tempo. *Verbose logging alone cost 40+ FPS.*
- **Rebuild depois de copiar um fonte de uma baseline:** limpe o atributo somente leitura e atualize a data do arquivo, senão o Ninja reaproveita o objeto antigo.
- Variáveis de ambiente vazam entre boots na mesma janela do PowerShell: confira o que está definido antes de comparar rodadas.

## Critério de regressão

Um boot de 330 s com o `PAD_SCRIPT` do BUILDING deve ter: `[STARTUP] Time to Press Start` perto de 15 s; 0 `dispatch MISS`; 0 ressincronizações do FIFO; 0 `drop surface != 0`; cena 3D depois de ~130–150 s a 5,5–6,6 FPS. A sonda `[t54]` pode disparar no `Loading...` (até 3 vezes) e o jogo segue.

## Variáveis úteis

| Variável | Origem | Para quê |
| :--- | :--- | :--- |
| `PAD_SCRIPT=<s>:<máscara>,…` | toolkit | aperta botões em tempos fixos (START `0x0008`, X `0x4000`, □ `0x8000`) |
| `RSX_LIVE_DRAW=1` | toolkit | motor de desenho NV4097 → D3D12 (obrigatório para o RDR) |
| `LD_FRAME_DUMP=<dir>`, `_EVERY=<n>`, `_FROM=<n>` | toolkit | grava quadros `.ppm` (converta com `analysis\tools\ppm2png.py`; ficam locais) |
| `SPU_DUMP_MISS=<dir>` | toolkit | grava o binário de cada job sem tradução (a pasta precisa existir) |
| `SPU_DUMP_OVL=<dir>,0x36800` | toolkit | grava os módulos carregados em LS (plugins DSP) |
| `SPU_INTERP_UNLIFTED=1` | toolkit + patch | código SPU carregado em tempo de execução roda no interpretador como chamada |
| `SPU_INTERP_STATS=<s>` | toolkit | páginas de LS interpretadas, a cada `s` segundos |
| `SPU_JOBPROF` | toolkit | contagem e tempo por job |
| `SPURS_JC_PARALLEL=1` | patch | jobs da mesma cadeia em paralelo até `maxContention` (cena de 3,8 para 5,9 FPS) |
| `SPURS_JOB_FULLCLEAR` | patch | limpa o LS inteiro entre jobs, em vez de só a parte usada |
| `PS3_USLEEP_WAIT_US=500` | patch | `usleep` longo dorme em vez de girar |
| `GCM_PARK_GRACE_MS=2000` | toolkit | prazo antes de estacionar o caminhador do FIFO |
| `PS3_AUDIO_OUT_CH=2` | patch | canais anunciados pela saída de áudio (2, 6 ou 8) |
| `AUDIO_WAV=<arquivo>`, `AUDIO_PEAK`, `AUDIO_RATE=1` | toolkit | grava a saída de áudio; picos; taxa da porta |
| `PPU_WWATCH=<ea>`, `PPU_WWATCH_LEN`, `PPU_WWATCH_MAX` | toolkit | vigia escritas do PPU numa faixa e mostra a pilha do jogo |
| `PS3_SAMPLE=<ms>` | toolkit | amostrador de pilhas do PPU |
| `PS3_SCTRACE=fail` | toolkit | registra syscalls que falham |
| `PS3_FSLOG` | toolkit | registra o acesso a arquivos |
| `GCM_SUBCH1_M2MF=1` | experimento | executa as cópias NV0039 do subcanal 1 (`analysis/experiments/gera_m2mf.py`) |
| `SPU_AUDIT_IMG`, `SPU_AUDIT_TRACE`, `SPU_AUDIT_WATCH`, `SPU_AUDIT_SUM`, `SPU_AUDIT_HEX` | experimento | sonda de DMA do SPU (`analysis/experiments/audit.c`) |
| `PPU_WWATCH_STACKFN=<func>` | experimento | pilha só quando a escrita vigiada vem dessa função (`gera_ww.py`) |

## Receitas

- **`dispatch MISS fp=… size=…` no `.err`:** um job SPU sem tradução. Rode de novo com `SPU_DUMP_MISS`, traduza com `lift_jobs.py`, reconfigure e compile. Um job novo pode aparecer só depois de minutos; boots curtos não o mostram. `analysis\tools\fpbusca.c` acha o job no ELF pelo fingerprint, quando ele está lá.
- **Quadros param, jogo não cai:** colete pilhas com `boot_seguro.ps1 -Sonda <seg>` e leia com `analysis\tools\pilhas.ps1 -Tag <tag>`. Thread de render girando em espera de rótulo do RSX costuma ser job SPU que não terminou ou comando do FIFO descartado numa ressincronização (procure `gcm_fifo_resync`).
- **`FIFO JUMP to unmapped IO`:** a palavra inválida no fim dos segmentos de 8 KB do FIFO; o patch do `cellGcmSys.c` pula essa palavra.
- **Laço infinito em `func_0066BEA8` durante o `Loading...`:** lista de vozes com cabeça `0xCDCD` (o preenchimento do alocador do RAGE). Gere o `ppu_recomp_023.cpp` com `scripts\gera_voz.py`; a sonda `[t54]` registra o estado e sai do laço.
- **CPU baixa e disco parado na carga:** compare as linhas `IO <seg> <bytes>` do `.mon` (só se sobem ou param; o valor absoluto varia).
- **Modo lento para reproduzir problemas de tempo:** `-NucleosLivres 7` deixa o jogo com 5 núcleos.
- **Áudio mudo:** grave com `AUDIO_WAV` e meça a fração de amostras não nulas, em vez de confiar no ouvido. Para ver quais buffers a mixagem lê, use a sonda `audit.c` no `exp_build.py`.
- **Armadilha do `PPU_WWATCH_LEN`:** o valor é lido com base automática; `CC0` sem `0x` vira 0 e a janela cai para 32 bytes. Use `0xCC0`. Um `memset` inicial pode gastar o limite de `PPU_WWATCH_MAX` antes da escrita que interessa.
- **Símbolos para pilhas e RVAs:** `llvm-nm --defined-only -n MyGameRecomp.exe` e `analysis\tools\rva2sym.py`.
- **Executável experimental sem tocar no build principal:** `analysis\experiments\exp_build.py <saída> --troca … --mais …` recompila só os TUs trocados e liga um exe separado; rode com `boot_seguro.ps1 -Exe <exe>`.

## Medições A/B

Mesma duração (330 s), mesmo `PAD_SCRIPT`, mesmo estado do `cache.dat`, alternando A e B, pelo menos duas rodadas de cada. Compare FPS na janela da cena (depois de 150 s), não no boot. Uma rodada só é anedota: a parada de 23 s, por exemplo, sumiu em 6 boots seguidos.
