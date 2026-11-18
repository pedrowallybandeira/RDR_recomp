# Red Dead Redemption — Recompiled (PS3 → PC)

*[English below](#english)*

Recompilação estática **pessoal e experimental** de *Red Dead Redemption — Game of the Year Edition* (PS3, EUA; diretório de dados `BLUS30418`) para Windows x64, construída sobre o toolkit [ps3recomp](https://github.com/sp00nznet/ps3recomp).

> **Este repositório não contém o jogo.** Não há aqui executável, ELF, código traduzido do jogo, programas SPU, firmware, chaves, dados do disco, quadros crus nem logs (só as capturas abaixo, da saída do port). Para compilar é preciso ter a sua própria cópia do jogo e produzir localmente os arquivos de entrada. Ver [docs/LEGAL.md](docs/LEGAL.md).

## Estado

> **Experimental, mas já jogável na primeira cidade.** O jogo passa pela abertura (vídeos com som, tela título, cutscene do trem a 20–30 FPS) e chega a **Armadillo**, onde dá para andar, correr, escalar, pular de telhados, atirar, brigar e salvar; a **primeira missão** começa (entrar no saloon). Na rua o jogo roda a **4–10 FPS**.
>
> - **Áudio:** funcionando: música, efeitos e os vídeos da abertura.
> - **Desempenho:** limitado pela CPU; a thread que traduz os comandos do RSX para o Direct3D 12 fica ~90% ocupada.
> - **Imagem:** sem pisca de cor desde a v19. No build adotado a cena só tem luz ambiente; em experimento o sol, a névoa e os reflexos já voltaram, e a sombra projetada está em diagnóstico. Vegetação ao longe em blocos e chão borrado.
> - **Entrada:** controle de Xbox (XInput).
> - **Estabilidade:** às vezes a carga de uma cutscene para. O PC hospedeiro já congelou em sessões longas de boots seguidos; por isso o jogo só deve rodar por `scripts\boot_seguro.ps1`.
>
> Detalhes, números e próximos passos: [docs/STATUS.md](docs/STATUS.md).

## O que tem aqui

| Caminho | Conteúdo |
| :--- | :--- |
| `port/` | Projeto CMake do executável (derivado do `templates/project` do ps3recomp), `main.cpp`, `stubs.cpp`, `src/fs_area.c` e `src/audio_float/` |
| `patches/` | Mudanças no ps3recomp: `ps3recomp-v0.19.0-upstream-prs.patch` (12 PRs abertos do toolkit), `ps3recomp-v0.19.0-rdr.patch` (runtime e bibliotecas HLE) e `ps3recomp-v0.18.0-ppu_lifter.patch` (tabelas de salto do lifter) |
| `scripts/` | Preparação, build, boot protegido e atalhos (PowerShell), com caminhos relativos a `RDR_ROOT` |
| `launcher/` | Janela tkinter: confere a instalação, roda e para o jogo sempre pelo boot protegido |
| `analysis/` | Ferramentas de diagnóstico e análise, experimentos e scripts históricos das tentativas |
| `spu/` | `images.json`: identificadores (hash, tamanho) dos programas SPU, jobs e plugins DSP traduzidos — sem código |
| `docs/` | [BUILDING](docs/BUILDING.md), [STATUS](docs/STATUS.md), [DEBUGGING](docs/DEBUGGING.md), [RELATED_PROJECTS](docs/RELATED_PROJECTS.md), [LEGAL](docs/LEGAL.md); visão geral em [ARCHITECTURE.md](ARCHITECTURE.md) |
| `.github/workflows/` | CI `no-game-files`: falha se algo do jogo for rastreado ou se um arquivo passar de 2 MB |
| `local/` | **Ignorada pelo git.** ELF, lift, SPU traduzido, VFS, build, logs — tudo que vem do jogo |

## Capturas

Saída do próprio port (`LD_FRAME_DUMP`, 1280×720), sem retoque. As seis primeiras são do boot `seg346`, de 2026-11-17, num build **experimental**: a v19 mais a correção da luz das tentativas 134–135, que ainda não está no build adotado. A sombra projetada ainda falta, e os arbustos ao longe saem em blocos.

| | |
| :---: | :---: |
| ![Plataforma da estação](docs/screenshots/station-platform.jpg) | ![Rua de Armadillo](docs/screenshots/armadillo-street.jpg) |
| Plataforma da estação de Armadillo | A rua principal de Armadillo |
| ![Pôr do sol na estação](docs/screenshots/sunset-station.jpg) | ![O trem ao pôr do sol](docs/screenshots/sunset-train.jpg) |
| Pôr do sol na estação | O trem ao pôr do sol |
| ![Menu de pausa](docs/screenshots/pause-map.jpg) | ![Tela título](docs/screenshots/title-screen.jpg) |
| Menu de pausa | Tela título (boot `seg182`, 2026-11-08) |

Antes: a primeira cutscene em 2026-11-08 (boot `seg182`), escura e com defeitos.

| | |
| :---: | :---: |
| ![Abertura: barco ao longe](docs/screenshots/cutscene-boat.jpg) | ![Abertura: o cais](docs/screenshots/cutscene-dock.jpg) |
| Barco ao longe (~6 FPS) | O plano seguinte, no cais |

## Início rápido

1. Tenha a sua cópia do jogo e gere você mesmo o ELF decriptado e a árvore de dados (este repositório não explica nem automatiza isso).
2. Clone o ps3recomp na tag `v0.19.0` em `local\ps3recomp` e rode `scripts\prepare_toolkit.ps1` (aplica os 12 PRs em `local\ps3recomp-rdr`).
3. Traduza o ELF com o `ppu_lifter.py` da v0.18.0 mais `patches/ps3recomp-v0.18.0-ppu_lifter.patch`; para ter música, traduza também o `flashMP3.pic` do seu firmware com `analysis\tools\lift_mp3.py`.
4. `scripts\prepare_overlay.ps1` → aplica o patch do RDR em cópias, em `local\overlay`.
5. `scripts\build.ps1` → `local\build\MyGameRecomp.exe`.
6. `scripts\boot_seguro.ps1 -Tag teste -Segundos 330`, ou o launcher: `scripts\launch.ps1`.

Passo a passo completo em [docs/BUILDING.md](docs/BUILDING.md).

## Créditos

- **[ps3recomp](https://github.com/sp00nznet/ps3recomp)** — Ned Heller / sp00nznet e colaboradores, licença MIT. Todo o runtime, as bibliotecas HLE, o lifter PPU/SPU e o template do projeto são deles; este port só adiciona patches e scripts. O texto da licença está em [LICENSES/ps3recomp-MIT.txt](LICENSES/ps3recomp-MIT.txt).
- PRs abertos do ps3recomp usados na base: sp00nznet/ps3recomp#746, sp00nznet/ps3recomp#754, sp00nznet/ps3recomp#702, sp00nznet/ps3recomp#736, sp00nznet/ps3recomp#738 (Vulkan), sp00nznet/ps3recomp#764, sp00nznet/ps3recomp#713, sp00nznet/ps3recomp#759, sp00nznet/ps3recomp#758, sp00nznet/ps3recomp#760, sp00nznet/ps3recomp#761, sp00nznet/ps3recomp#601 (estabilidade), mais sp00nznet/ps3recomp#701, sp00nznet/ps3recomp#665 e sp00nznet/ps3recomp#662 (render) dentro do patch do RDR. Correções deste port enviadas ao toolkit: sp00nznet/ps3recomp#712, sp00nznet/ps3recomp#714 e sp00nznet/ps3recomp#715.
- Estrutura do repositório inspirada em [God of War Ascension Recompiled](https://github.com/MaChInEgUn3/God-of-War-Ascension-Recompiled).
- **Assistência de IA:** grande parte do código, dos scripts e desta documentação foi escrita com assistentes de IA (Claude Code, da Anthropic, e Google Antigravity), sob orientação e revisão do autor. Os testes de boot foram feitos na máquina do autor.

## Licença

O código e a documentação próprios deste repositório estão sob a licença MIT ([LICENSE](LICENSE)). Os patches modificam arquivos do ps3recomp, que continuam sob a licença MIT deles. Nada do jogo, do firmware ou derivado deles está coberto por esta licença, e nada disso pode ser enviado ao repositório.

*Red Dead Redemption* é marca da Take-Two Interactive / Rockstar Games. Este é um projeto de pesquisa de fã, sem afiliação nem endosso da Take-Two, da Rockstar ou da Sony. PlayStation é marca da Sony Interactive Entertainment.

---

## English

A **personal, experimental** static recompilation of *Red Dead Redemption — Game of the Year Edition* (PS3, US; data directory `BLUS30418`) to Windows x64, built on the [ps3recomp](https://github.com/sp00nznet/ps3recomp) toolkit.

> **This repository does not contain the game.** No executable, ELF, lifted game code, SPU programs, firmware, keys, disc data, raw frames or logs (only the screenshots of the port's output shown here). You need your own copy of the game and must produce the inputs locally. See [docs/LEGAL.md](docs/LEGAL.md).

### Status

> **Experimental, but already playable in the first town.** The game goes through the intro (videos with sound, title screen, the train cutscene at 20–30 FPS) and reaches **Armadillo**, where you can walk, run, climb, jump off roofs, shoot, fight and save; the **first mission** starts (go to the saloon). Town runs at **4–10 FPS**.
>
> - **Audio:** working: music, effects and the intro videos.
> - **Performance:** CPU-bound; the thread that turns RSX commands into Direct3D 12 calls is ~90% busy.
> - **Picture:** no color flicker since v19. In the adopted build the scene has ambient light only; in an experiment the sun, fog and reflections are back, and cast shadows are under investigation. Distant vegetation renders as blocks and the ground is blurry.
> - **Input:** Xbox controller (XInput).
> - **Stability:** loading a cutscene sometimes hangs. The host PC has frozen during long series of boots, so only run the game through `scripts\boot_seguro.ps1`.
>
> Details and next steps: [docs/STATUS.md](docs/STATUS.md) (Portuguese, with an English summary).

### What lives here

| Path | Contents |
| :--- | :--- |
| `port/` | CMake project for the executable (derived from ps3recomp's `templates/project`), `main.cpp`, `stubs.cpp`, `src/fs_area.c`, `src/audio_float/` |
| `patches/` | Changes to ps3recomp: `ps3recomp-v0.19.0-upstream-prs.patch` (12 open toolkit PRs), `ps3recomp-v0.19.0-rdr.patch` (runtime and HLE libraries) and `ps3recomp-v0.18.0-ppu_lifter.patch` (lifter jump tables) |
| `scripts/` | Prepare, build, guarded boot and shortcuts (PowerShell), paths relative to `RDR_ROOT` |
| `launcher/` | tkinter window: checks the setup, starts and stops the game, always through the guarded boot |
| `analysis/` | Diagnostic and analysis tools, experiments, historical per-attempt scripts |
| `spu/` | `images.json`: identifiers (hash, size) of the lifted SPU programs, jobs and DSP plugins — no code |
| `docs/` | [BUILDING](docs/BUILDING.md), [STATUS](docs/STATUS.md), [DEBUGGING](docs/DEBUGGING.md), [RELATED_PROJECTS](docs/RELATED_PROJECTS.md), [LEGAL](docs/LEGAL.md); overview in [ARCHITECTURE.md](ARCHITECTURE.md) |
| `.github/workflows/` | `no-game-files` CI: fails if anything from the game is tracked or a file exceeds 2 MB |
| `local/` | **Git-ignored.** ELF, lift, lifted SPU code, VFS, build, logs — everything derived from the game |

### Screenshots

The port's own output (`LD_FRAME_DUMP`, 1280×720), untouched. The first six come from boot `seg346` on 2026-11-17, an **experimental** build: v19 plus the lighting fix from attempts 134–135, which is not in the adopted build yet. Cast shadows are still missing and distant bushes render as blocks. They show the Armadillo station platform, the main street, the station and the train at sunset, the pause menu, and the title screen (boot `seg182`, 2026-11-08). The last row is the first cutscene as it looked on 2026-11-08: dark and with rendering defects. Images are in the tables above.

### Quick start

1. Own the game and produce the decrypted ELF and the data tree yourself (this repository neither explains nor automates that).
2. Clone ps3recomp at tag `v0.19.0` into `local\ps3recomp` and run `scripts\prepare_toolkit.ps1` (applies the 12 PRs into `local\ps3recomp-rdr`).
3. Lift the ELF with ps3recomp v0.18.0's `ppu_lifter.py` plus `patches/ps3recomp-v0.18.0-ppu_lifter.patch`; for music, also lift your own firmware's `flashMP3.pic` with `analysis\tools\lift_mp3.py`.
4. `scripts\prepare_overlay.ps1` applies the RDR patch to copies in `local\overlay`.
5. `scripts\build.ps1` → `local\build\MyGameRecomp.exe`.
6. `scripts\boot_seguro.ps1 -Tag test -Segundos 330`, or the launcher: `scripts\launch.ps1`.

Full steps in [docs/BUILDING.md](docs/BUILDING.md).

### Credits

- **[ps3recomp](https://github.com/sp00nznet/ps3recomp)** by Ned Heller / sp00nznet and contributors, MIT. The runtime, HLE libraries, PPU/SPU lifters and project template are theirs; this port adds patches and scripts. Licence text: [LICENSES/ps3recomp-MIT.txt](LICENSES/ps3recomp-MIT.txt).
- Open ps3recomp PRs in the base: sp00nznet/ps3recomp#746, sp00nznet/ps3recomp#754, sp00nznet/ps3recomp#702, sp00nznet/ps3recomp#736, sp00nznet/ps3recomp#738 (Vulkan), sp00nznet/ps3recomp#764, sp00nznet/ps3recomp#713, sp00nznet/ps3recomp#759, sp00nznet/ps3recomp#758, sp00nznet/ps3recomp#760, sp00nznet/ps3recomp#761, sp00nznet/ps3recomp#601 (stability), plus sp00nznet/ps3recomp#701, sp00nznet/ps3recomp#665 and sp00nznet/ps3recomp#662 (rendering) inside the RDR patch. Fixes from this port sent upstream: sp00nznet/ps3recomp#712, sp00nznet/ps3recomp#714, sp00nznet/ps3recomp#715.
- Repository layout modelled on [God of War Ascension Recompiled](https://github.com/MaChInEgUn3/God-of-War-Ascension-Recompiled).
- **AI assistance:** much of the code, scripts and documentation was written with AI assistants (Anthropic's Claude Code and Google Antigravity), directed and reviewed by the author. Boot tests ran on the author's machine.

### License

This repository's own code and documentation are MIT ([LICENSE](LICENSE)). The patches modify ps3recomp files, which remain under ps3recomp's MIT licence. Nothing from the game or firmware, or derived from them, is covered by this licence or may be committed.

*Red Dead Redemption* is a trademark of Take-Two Interactive / Rockstar Games. This is fan research, not affiliated with or endorsed by Take-Two, Rockstar or Sony. PlayStation is a trademark of Sony Interactive Entertainment.
