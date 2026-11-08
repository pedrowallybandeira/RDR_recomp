# Red Dead Redemption — Recompiled (PS3 → PC)

*[English below](#english)*

Recompilação estática **pessoal e experimental** de *Red Dead Redemption — Game of the Year Edition* (PS3, EUA; diretório de dados `BLUS30418`) para Windows x64, construída sobre o toolkit [ps3recomp](https://github.com/sp00nznet/ps3recomp).

> **Este repositório não contém o jogo.** Não há aqui executável, ELF, código traduzido do jogo, programas SPU, firmware, chaves, dados do disco, quadros crus nem logs (só as quatro capturas abaixo, da saída do port). Para compilar é preciso ter a sua própria cópia do jogo e produzir localmente os arquivos de entrada. Ver [docs/LEGAL.md](docs/LEGAL.md).

## Estado

> **Pesquisa, longe de ser jogável.** O jogo inicia, passa pelos menus e chega à **primeira cutscene 3D** (cerca de 130 s depois do boot), que roda estável a **~6 FPS** (5,6–6,6). Os menus rodam a 8–10 FPS.
>
> - **Áudio:** praticamente mudo. Em builds experimentais sai um som ambiente muito baixo e esparso; a música da tela título é decodificada, mas não chega à mixagem.
> - **Câmera:** a abertura agora troca de plano (barco ao longe, depois o cais com a multidão) nos builds experimentais mais recentes; antes ficava parada num único plano.
> - **Imagem:** a cena é desenhada com defeitos (cintilação, elementos sumindo).
> - **Entrada:** só XInput; a navegação até a cena é feita por roteiro de botões (`PAD_SCRIPT`).
> - **Estabilidade:** o PC hospedeiro congelou duas vezes em boots longos; por isso o jogo só deve rodar por `scripts\boot_seguro.ps1`. Há uma parada intermitente por volta de 23 s com o cache do jogo já criado.
>
> Detalhes, números e próximos passos: [docs/STATUS.md](docs/STATUS.md).

## O que tem aqui

| Caminho | Conteúdo |
| :--- | :--- |
| `port/` | Projeto CMake do executável (derivado do `templates/project` do ps3recomp), `main.cpp`, `stubs.cpp` e `src/fs_area.c` |
| `patches/` | Mudanças no ps3recomp: `ps3recomp-v0.19.0-rdr.patch` (runtime e bibliotecas HLE) e `ps3recomp-v0.18.0-ppu_lifter.patch` (tabelas de salto do lifter) |
| `scripts/` | Preparação, build, boot protegido e atalhos (PowerShell), com caminhos relativos a `RDR_ROOT` |
| `launcher/` | Janela tkinter: confere a instalação, roda e para o jogo sempre pelo boot protegido |
| `analysis/` | Ferramentas de diagnóstico e análise, experimentos e scripts históricos das tentativas |
| `spu/` | `images.json`: identificadores (hash, tamanho) dos programas SPU, jobs e plugins DSP traduzidos — sem código |
| `docs/` | [BUILDING](docs/BUILDING.md), [STATUS](docs/STATUS.md), [DEBUGGING](docs/DEBUGGING.md), [RELATED_PROJECTS](docs/RELATED_PROJECTS.md), [LEGAL](docs/LEGAL.md); visão geral em [ARCHITECTURE.md](ARCHITECTURE.md) |
| `.github/workflows/` | CI `no-game-files`: falha se algo do jogo for rastreado ou se um arquivo passar de 2 MB |
| `local/` | **Ignorada pelo git.** ELF, lift, SPU traduzido, VFS, build, logs — tudo que vem do jogo |

## Capturas

Saída do próprio port (`LD_FRAME_DUMP`, 1280×720), boot `seg182` de um build experimental (cópias NV0039 ligadas), sem retoque.

| | |
| :---: | :---: |
| ![Tela título](docs/screenshots/title-screen.jpg) | ![Tela de carga](docs/screenshots/loading.jpg) |
| Tela título (~8 FPS) | Carga da primeira missão |
| ![Abertura: barco ao longe](docs/screenshots/cutscene-boat.jpg) | ![Abertura: o cais](docs/screenshots/cutscene-dock.jpg) |
| Primeira cutscene: barco ao longe (~6 FPS) | O plano seguinte, no cais: escuro e com defeitos |

## Início rápido

1. Tenha a sua cópia do jogo e gere você mesmo o ELF decriptado e a árvore de dados (este repositório não explica nem automatiza isso).
2. Clone o ps3recomp na tag `v0.19.0` em `local\ps3recomp`.
3. Traduza o ELF com o `ppu_lifter.py` da v0.18.0 mais `patches/ps3recomp-v0.18.0-ppu_lifter.patch`.
4. `scripts\prepare_overlay.ps1` → aplica o patch da v0.19.0 em cópias, em `local\overlay`.
5. `scripts\build.ps1` → `local\build\MyGameRecomp.exe`.
6. `scripts\boot_seguro.ps1 -Tag teste -Segundos 330`, ou o launcher: `scripts\launch.ps1`.

Passo a passo completo em [docs/BUILDING.md](docs/BUILDING.md).

## Créditos

- **[ps3recomp](https://github.com/sp00nznet/ps3recomp)** — Ned Heller / sp00nznet e colaboradores, licença MIT. Todo o runtime, as bibliotecas HLE, o lifter PPU/SPU e o template do projeto são deles; este port só adiciona patches e scripts. O texto da licença está em [LICENSES/ps3recomp-MIT.txt](LICENSES/ps3recomp-MIT.txt).
- PRs abertos do ps3recomp incorporados ao patch: sp00nznet/ps3recomp#701, sp00nznet/ps3recomp#665 e sp00nznet/ps3recomp#662 (render). Correções deste port enviadas ao toolkit: sp00nznet/ps3recomp#712, sp00nznet/ps3recomp#714 e sp00nznet/ps3recomp#715.
- Estrutura do repositório inspirada em [God of War Ascension Recompiled](https://github.com/MaChInEgUn3/God-of-War-Ascension-Recompiled).
- **Assistência de IA:** grande parte do código, dos scripts e desta documentação foi escrita com assistentes de IA (Claude Code, da Anthropic, e Google Antigravity), sob orientação e revisão do autor. Os testes de boot foram feitos na máquina do autor.

## Licença

O código e a documentação próprios deste repositório estão sob a licença MIT ([LICENSE](LICENSE)). Os patches modificam arquivos do ps3recomp, que continuam sob a licença MIT deles. Nada do jogo, do firmware ou derivado deles está coberto por esta licença, e nada disso pode ser enviado ao repositório.

*Red Dead Redemption* é marca da Take-Two Interactive / Rockstar Games. Este é um projeto de pesquisa de fã, sem afiliação nem endosso da Take-Two, da Rockstar ou da Sony. PlayStation é marca da Sony Interactive Entertainment.

---

## English

A **personal, experimental** static recompilation of *Red Dead Redemption — Game of the Year Edition* (PS3, US; data directory `BLUS30418`) to Windows x64, built on the [ps3recomp](https://github.com/sp00nznet/ps3recomp) toolkit.

> **This repository does not contain the game.** No executable, ELF, lifted game code, SPU programs, firmware, keys, disc data, raw frames or logs (only the four screenshots of the port's output shown here). You need your own copy of the game and must produce the inputs locally. See [docs/LEGAL.md](docs/LEGAL.md).

### Status

> **Research, far from playable.** The game boots, goes through the menus and reaches the **first 3D cutscene** (about 130 s after boot), which runs stably at **~6 FPS** (5.6–6.6). Menus run at 8–10 FPS.
>
> - **Audio:** nearly silent. Experimental builds produce a very quiet, sparse ambient sound; the title-screen music is decoded but never reaches the mixer.
> - **Camera:** the opening now changes shots (boat in the distance, then the crowded dock) in the latest experimental builds; it used to sit on a single shot.
> - **Picture:** the scene renders with defects (flicker, disappearing elements).
> - **Input:** XInput only; menus are driven by a scripted button sequence (`PAD_SCRIPT`).
> - **Stability:** the host PC froze twice during long boots, so only run the game through `scripts\boot_seguro.ps1`. There is an intermittent stall around 23 s when the game cache already exists.
>
> Details and next steps: [docs/STATUS.md](docs/STATUS.md) (Portuguese, with an English summary).

### What lives here

| Path | Contents |
| :--- | :--- |
| `port/` | CMake project for the executable (derived from ps3recomp's `templates/project`), `main.cpp`, `stubs.cpp`, `src/fs_area.c` |
| `patches/` | Changes to ps3recomp: `ps3recomp-v0.19.0-rdr.patch` (runtime and HLE libraries) and `ps3recomp-v0.18.0-ppu_lifter.patch` (lifter jump tables) |
| `scripts/` | Prepare, build, guarded boot and shortcuts (PowerShell), paths relative to `RDR_ROOT` |
| `launcher/` | tkinter window: checks the setup, starts and stops the game, always through the guarded boot |
| `analysis/` | Diagnostic and analysis tools, experiments, historical per-attempt scripts |
| `spu/` | `images.json`: identifiers (hash, size) of the lifted SPU programs, jobs and DSP plugins — no code |
| `docs/` | [BUILDING](docs/BUILDING.md), [STATUS](docs/STATUS.md), [DEBUGGING](docs/DEBUGGING.md), [RELATED_PROJECTS](docs/RELATED_PROJECTS.md), [LEGAL](docs/LEGAL.md); overview in [ARCHITECTURE.md](ARCHITECTURE.md) |
| `.github/workflows/` | `no-game-files` CI: fails if anything from the game is tracked or a file exceeds 2 MB |
| `local/` | **Git-ignored.** ELF, lift, lifted SPU code, VFS, build, logs — everything derived from the game |

### Screenshots

The port's own output (`LD_FRAME_DUMP`, 1280×720), boot `seg182` of an experimental build (NV0039 copies on), untouched: title screen (~8 FPS), first-mission loading screen, and the first cutscene — the boat in the distance (~6 FPS), then the next shot on the dock, dark and with rendering defects. Images are in the table above.

### Quick start

1. Own the game and produce the decrypted ELF and the data tree yourself (this repository neither explains nor automates that).
2. Clone ps3recomp at tag `v0.19.0` into `local\ps3recomp`.
3. Lift the ELF with ps3recomp v0.18.0's `ppu_lifter.py` plus `patches/ps3recomp-v0.18.0-ppu_lifter.patch`.
4. `scripts\prepare_overlay.ps1` applies the v0.19.0 patch to copies in `local\overlay`.
5. `scripts\build.ps1` → `local\build\MyGameRecomp.exe`.
6. `scripts\boot_seguro.ps1 -Tag test -Segundos 330`, or the launcher: `scripts\launch.ps1`.

Full steps in [docs/BUILDING.md](docs/BUILDING.md).

### Credits

- **[ps3recomp](https://github.com/sp00nznet/ps3recomp)** by Ned Heller / sp00nznet and contributors, MIT. The runtime, HLE libraries, PPU/SPU lifters and project template are theirs; this port adds patches and scripts. Licence text: [LICENSES/ps3recomp-MIT.txt](LICENSES/ps3recomp-MIT.txt).
- Open ps3recomp PRs folded into the patch: sp00nznet/ps3recomp#701, sp00nznet/ps3recomp#665, sp00nznet/ps3recomp#662 (rendering). Fixes from this port sent upstream: sp00nznet/ps3recomp#712, sp00nznet/ps3recomp#714, sp00nznet/ps3recomp#715.
- Repository layout modelled on [God of War Ascension Recompiled](https://github.com/MaChInEgUn3/God-of-War-Ascension-Recompiled).
- **AI assistance:** much of the code, scripts and documentation was written with AI assistants (Anthropic's Claude Code and Google Antigravity), directed and reviewed by the author. Boot tests ran on the author's machine.

### License

This repository's own code and documentation are MIT ([LICENSE](LICENSE)). The patches modify ps3recomp files, which remain under ps3recomp's MIT licence. Nothing from the game or firmware, or derived from them, is covered by this licence or may be committed.

*Red Dead Redemption* is a trademark of Take-Two Interactive / Rockstar Games. This is fan research, not affiliated with or endorsed by Take-Two, Rockstar or Sony. PlayStation is a trademark of Sony Interactive Entertainment.
