# Contribuindo / Contributing

Projeto pessoal; issues e sugestões são bem-vindas, PRs são revisados à mão.

*A personal project; issues and suggestions are welcome, PRs are reviewed by hand.*

## Regras / Rules

1. Leia [docs/LEGAL.md](docs/LEGAL.md). Nada do jogo, do firmware ou traduzido deles: nem ELF, nem `ppu_recomp_*.cpp`, nem SPU traduzido, nem dumps, quadros crus, WAVs, logs ou saves (capturas só em `docs/screenshots/`, JPEG 1280×720 até 300 KB). Confira `git status` antes de cada commit. / Nothing from the game or firmware, or lifted from them. Check `git status` before every commit.
2. Mudanças no ps3recomp vão em `patches/ps3recomp-v0.19.0-rdr.patch` (base `v0.19.0`). Correções genéricas devem ir também para o [ps3recomp](https://github.com/sp00nznet/ps3recomp), um PR pequeno por mudança, seguindo o `CONTRIBUTING.md` de lá. / Toolkit changes go in the patch; generic fixes also go upstream as small PRs.
3. Diagnóstico ou experimento novo fica atrás de uma variável de ambiente, desligado por padrão. Mudar um padrão exige medição (boots A/B pelo `boot_seguro.ps1`, mesma duração, números citados no PR). / New diagnostics sit behind an env var, off by default; changing a default needs an A/B measurement.
4. Atualize [docs/STATUS.md](docs/STATUS.md) na mesma mudança quando o comportamento mudar, e [docs/DEBUGGING.md](docs/DEBUGGING.md) quando entrar uma variável nova. / Update STATUS.md in the same change, and DEBUGGING.md for new switches.
5. A CI `no-game-files` (`.github/workflows/guard.yml`) recusa arquivos do jogo, binários e arquivos acima de 2 MB. Ela é rede de proteção, não revisão. / The `no-game-files` CI rejects game files, binaries and files over 2 MB; it is a safety net, not a review.
6. Código de projeto com licença incompatível com MIT não entra. Vale também para código escrito com IA: se parecer reproduzir outro projeto, confira a origem antes. / No code from MIT-incompatible projects; the same applies to AI-assisted code.
7. Commits: assunto no imperativo com prefixo `port:`, `patch:`, `analysis:`, `scripts:` ou `docs:`, e corpo explicando o porquê. / Imperative subject with a prefix, body explaining why.

## Assistência de IA / AI assistance

Boa parte deste repositório foi escrita com assistentes de IA, sob orientação e revisão do autor. Contribuições feitas com IA são aceitas nas mesmas condições: diga no PR, revise o que enviar e teste. / Much of this repository was written with AI assistants under the author's direction and review. AI-assisted contributions are welcome on the same terms: say so in the PR, review what you send, and test it.
