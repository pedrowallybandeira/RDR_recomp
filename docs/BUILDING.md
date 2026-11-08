# Compilação / Building

*English summary at the end.*

Só Windows x64: o desenho usa o motor `rsx_live_draw` (Direct3D 12) do ps3recomp. Testado no Windows 11.

## Requisitos

- Sua cópia de *Red Dead Redemption — Game of the Year Edition* (PS3, EUA). O executável usa o diretório de dados `BLUS30418`.
- `git`, CMake ≥ 3.20, Ninja, Python 3.12.
- [llvm-mingw](https://github.com/mstorsjo/llvm-mingw) UCRT x86_64 (testado com `20261020`). O MSVC não foi testado.
- Memória: cada arquivo traduzido chega a ~725 MB ao compilar; com `-j 4`, conte uns 4 GB livres. O executável final tem ~320 MB.

## Layout de `local\`

Tudo que vem do jogo fica em `local\`, que o git ignora. Os scripts leem os caminhos de [`scripts/config.ps1`](../scripts/config.ps1); cada um pode ser trocado por uma variável de ambiente.

| Caminho | Variável | Conteúdo |
| :--- | :--- | :--- |
| `local\` | `RDR_ROOT` | raiz local |
| `local\ps3recomp\` | `PS3RECOMP_DIR` | clone do ps3recomp na tag `v0.19.0` (`ae92407`) |
| `local\ps3recomp-v0.18.0\` | — | clone na tag `v0.18.0` (`4e8f3ca`), só para o lifter |
| `local\game\RDR2.elf` | `RDR_ELF` | executável do jogo **já decriptado por você** |
| `local\lift_in\` | — | listas de funções e imports do `ppu_loader.py` |
| `local\lifted\` | `RDR_LIFTED` | saída do `ppu_lifter.py` |
| `local\overlay\` | `RDR_OVERLAY` | arquivos do toolkit com o patch (`prepare_overlay.ps1`) |
| `local\spu_jobs\`, `local\spu_dsp\` | — | jobs SPU e plugins DSP traduzidos (opcionais) |
| `local\vfs\` | `RDR_VFS` | árvore do jogo: `PS3_GAME\PARAM.SFO`, `PS3_GAME\USRDIR\…`, `game\BLUS30418\USRDIR\…` |
| `local\dev_flash\` | `RDR_DEV_FLASH` | opcional: `sys\external\flashMP3.pic` do seu firmware (decodificador MP3) |
| `local\build\`, `local\boots\` | `RDR_BUILD`, `RDR_BOOTS` | build e saídas dos boots |

Os arquivos de dados precisam estar em forma aberta (os `.rpf`, `rdr2_ult.sdat` e os pacotes de DLC em `dlcPack\`). Este repositório não explica nem automatiza a extração ou a decriptação.

Toolchain: defina `LLVM_MINGW_BIN` (pasta `bin` do llvm-mingw) e, se o Python não estiver no PATH, `PYTHON_DIR`.

## 1. ps3recomp

```powershell
git clone https://github.com/sp00nznet/ps3recomp local\ps3recomp
git -C local\ps3recomp checkout v0.19.0
git clone https://github.com/sp00nznet/ps3recomp local\ps3recomp-v0.18.0
git -C local\ps3recomp-v0.18.0 checkout v0.18.0
git -C local\ps3recomp-v0.18.0 apply ..\..\patches\ps3recomp-v0.18.0-ppu_lifter.patch
```

O patch do lifter faz o `discover_jump_tables` reconhecer a base constante (`lis` + `addic`) dos dois interpretadores de bytecode do jogo e preferir o `lwzx` que alimenta o `mtctr`: sem ele, 180 de 192 despachos ficam sem resolução. O lift testado foi feito com o lifter da v0.18.0; o da v0.19.0 não foi testado com este patch.

## 2. Lift do PPU

```powershell
python local\ps3recomp-v0.18.0\tools\ppu_loader.py local\game\RDR2.elf -o local\lift_in
python scripts\prep_lift.py local\lift_in
python -I -u local\ps3recomp-v0.18.0\tools\ppu_lifter.py local\game\RDR2.elf --output local\lifted `
    --functions local\lift_in\RDR2.functions.clamped.json --hle-stubs local\lift_in\RDR2.imports.json `
    --code-end 0x1107288 --chunks 64 --jobs 4
```

`prep_lift.py` corta a última função, que o loader estende sobre o `.rodata`. Resultado esperado: 192 despachos, 255 destinos, ~68 mil funções em 66 arquivos.

Opcional, mas recomendado: a sonda `[t54]`, que tira o jogo de um laço infinito na lista de vozes durante o `Loading...`:

```powershell
python scripts\gera_voz.py local\lifted\ppu_recomp_023.cpp local\overlay\ppu_recomp_023.cpp
```

(rode depois do passo 3, ou o `prepare_overlay.ps1` reclama da pasta existente; com `-Force` ele preserva esse arquivo).

## 3. Overlay e build

```powershell
scripts\prepare_overlay.ps1
scripts\build.ps1 -Jobs 4
```

`prepare_overlay.ps1` extrai 15 arquivos da v0.19.0 e aplica `patches\ps3recomp-v0.19.0-rdr.patch` neles, sem mexer no clone. `build.ps1` configura com `PORT_SPU_INPUTS=RDR2.elf`, que faz o toolkit achar e traduzir os programas SPU embutidos no ELF (em `local\build\generated_spu\`), e compila. A primeira compilação leva cerca de 15–20 min.

## 4. Boot

```powershell
$env:PAD_SCRIPT = '24:0x0008,44:0x4000,64:0x4000,84:0x8000,104:0x4000'
scripts\boot_seguro.ps1 -Tag teste -Segundos 330
```

Sempre por `boot_seguro.ps1`: ele limita núcleos, memória, threads e tempo, grava um monitor em disco e inicia um vigia independente que mata o jogo depois de `Segundos + 45`. Um boot sem essas travas já congelou o PC. `-Visivel` mostra a janela.

O `PAD_SCRIPT` acima aperta START, X, X, □ e X e chega à cena 3D por volta de 130 s. Os logs ficam em `local\boots\<tag>.err`/`.out`/`.mon`.

Padrões que o `boot_seguro.ps1` liga (variáveis do ps3recomp ou do patch): `RSX_LIVE_DRAW=1`, `PS3_VERBOSE=0`, `SPURS_JC_PARALLEL=1`, `PS3_USLEEP_WAIT_US=500`, `SPU_INTERP_UNLIFTED=1`, `GCM_PARK_GRACE_MS=2000`, `PS3_AUDIO_OUT_CH=2`, `PS3_DEV_FLASH` (se existir).

## 5. Jobs SPU carregados dos dados (opcional)

Parte dos jobs SPU vem dos arquivos de dados, não do ELF. Sem tradução eles rodam no interpretador ou aparecem como `dispatch MISS` no `.err`. Ciclo:

1. Boot com `SPU_DUMP_MISS=<pasta>` (e `SPU_DUMP_OVL=<pasta>,0x36800` para os plugins DSP do Multistream).
2. `python analysis\tools\lift_jobs.py <pasta> local\spu_jobs` e `python analysis\tools\lift_dsp.py <pasta> local\spu_dsp` (com `RDR_ELF` e `PS3RECOMP_TOOLS=local\ps3recomp-v0.18.0\tools`).
3. Reconfigure (`cmake` relê `local\spu_jobs` e `local\spu_dsp`) e compile.

Os dumps e as traduções são código do jogo: ficam em `local\`.

---

## English summary

Windows x64 only (the `rsx_live_draw` Direct3D 12 engine). Needs your own copy of the game, git, CMake ≥ 3.20, Ninja, Python 3.12 and llvm-mingw UCRT (tested `20261020`).

1. Put everything derived from the game under `local\` (git-ignored; see the table above): the decrypted `RDR2.elf` you produced yourself, the plain data tree under `local\vfs`, optionally `flashMP3.pic` from your own firmware. This repository does not explain or automate extraction or decryption.
2. Clone ps3recomp at `v0.19.0` into `local\ps3recomp`, and at `v0.18.0` into `local\ps3recomp-v0.18.0` with `patches\ps3recomp-v0.18.0-ppu_lifter.patch` applied (jump-table discovery for the game's two bytecode interpreters).
3. Run `ppu_loader.py`, `scripts\prep_lift.py` (clamps the last function out of `.rodata`) and `ppu_lifter.py` with the arguments shown above. Optionally `scripts\gera_voz.py` for the `[t54]` voice-list probe.
4. `scripts\prepare_overlay.ps1` (applies `patches\ps3recomp-v0.19.0-rdr.patch` to copies of 15 toolkit files in `local\overlay`), then `scripts\build.ps1`.
5. Boot only through `scripts\boot_seguro.ps1` (resource limits, on-disk monitor, independent watchdog); an unguarded run once froze the host. With the `PAD_SCRIPT` shown above the game reaches the 3D cutscene after about 130 s.
6. Optional: capture runtime-loaded SPU jobs with `SPU_DUMP_MISS`, lift them with `analysis\tools\lift_jobs.py`/`lift_dsp.py` into `local\spu_jobs`/`local\spu_dsp`, reconfigure and rebuild.
