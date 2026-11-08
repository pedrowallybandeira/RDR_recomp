# Launcher

Janela simples (tkinter, só biblioteca padrão) para rodar o seu build local. Não contém nada do jogo.

*A small tkinter window for running your local build. Standard library only; contains nothing from the game.*

- **Caminhos:** pasta `local`, executável, `RDR2.elf`, VFS e `dev_flash` (vazios = padrões de `local\`).
- **Conferir instalação** (não executa o jogo): executável, ELF, `PARAM.SFO`, `USRDIR` com os `.rpf` e `dlcPack`, overlay do toolkit, `flashMP3.pic` (opcional).
- **Jogar:** sempre por `scripts\boot_seguro.ps1`, com limite de tempo, travas de memória/threads e o vigia independente. Opções: janela visível, `PAD_SCRIPT` até a cena, log detalhado e variáveis extras (`NOME=valor`, aplicadas por último).
- **Parar:** encerra só a árvore de processos que o launcher iniciou (boot seguro, jogo e vigia).
- **Abrir logs:** `local\boots`, onde cada sessão grava `.err`, `.out`, `.mon` e `<tag>.launcher.log`.

Abrir: `scripts\launch.ps1` ou `python launcher\rdr_launcher.py`. Testes: `python launcher\test_launcher.py`.

Guarda `launcher\settings.json` (ignorado pelo git).

*Open with `scripts\launch.ps1`. Setup checks never start the game; Play always goes through the guarded boot script; Stop kills only the process tree the launcher started. Settings live in the git-ignored `launcher\settings.json`.*
