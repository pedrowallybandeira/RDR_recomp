# Aspectos legais / Legal notes

*Não é aconselhamento jurídico. / Not legal advice.*

## Português

**O que este repositório contém:** só código, patches, scripts e documentação escritos para o port, e mudanças sobre o ps3recomp (MIT).

**O que ele nunca contém, e o `.gitignore` bloqueia:**

- Dados do jogo: ISO, `EBOOT.BIN`, `RDR2.elf` ou qualquer ELF/SELF/PRX do jogo, arquivos `.rpf`, `.sdat`, pacotes de DLC, `PARAM.SFO`, ícones, áudio, vídeo, texturas.
- Código traduzido do jogo: a saída do `ppu_lifter.py` (`ppu_recomp_*.cpp`, `ppu_recomp.h`), qualquer cópia modificada dela (como o `ppu_recomp_023.cpp` com a sonda `[t54]`), os programas SPU extraídos ou traduzidos (`generated_spu/`, `spu_jobs/`, `spu_dsp/`, `image.elf`, `code.bin`) e os objetos e executáveis que os contêm.
- Firmware e arquivos de `dev_flash` (inclusive `flashMP3.pic`), chaves, licenças (`.rap`, `act.dat`, `idps`), credenciais.
- Saídas de execução: dumps de memória ou de LS, quadros capturados (`.ppm`/`.png`), gravações de áudio (`.wav`), logs (`.err`, `.out`, `.mon`, `.pilhas`), `cache.dat` e saves.

**Obra derivada:** o executável recompilado contém o código do jogo traduzido para C++. Ele é uma obra derivada do jogo e **não pode ser distribuído**. Cada pessoa o compila na própria máquina, a partir da própria cópia do jogo, obtida legalmente.

**Proteção:** o repositório não traz chaves, não explica como decriptar o executável ou os dados e não contém código para contornar proteção. O port só lê arquivos que o próprio usuário já tem em forma aberta. O toolkit tem uma rotina para abrir contêineres `NPD`; este port não a usa nem depende dela.

**Capturas:** só um punhado de imagens em `docs/screenshots/`, JPEG 1280×720 de até 300 KB, tiradas da saída do próprio port, para mostrar o estado do projeto. Quadros crus (`.ppm`) e qualquer outra imagem ficam locais; o `.gitignore` e a CI recusam imagens fora dessa pasta.

**Antes de cada commit:** confira `git status` e `git diff --cached --stat`. O `.gitignore` é uma rede de proteção, não substitui a atenção. Na dúvida, não envie.

## English

**This repository contains** only code, patches, scripts and documentation written for the port, plus changes to ps3recomp (MIT).

**It never contains, and `.gitignore` blocks:**

- Game data: ISO, `EBOOT.BIN`, `RDR2.elf` or any game ELF/SELF/PRX, `.rpf` archives, `.sdat`, DLC packs, `PARAM.SFO`, icons, audio, video, textures.
- Lifted game code: `ppu_lifter.py` output (`ppu_recomp_*.cpp`, `ppu_recomp.h`), any modified copy of it (such as `ppu_recomp_023.cpp` with the `[t54]` probe), extracted or lifted SPU programs (`generated_spu/`, `spu_jobs/`, `spu_dsp/`, `image.elf`, `code.bin`) and the objects and executables built from them.
- Firmware and `dev_flash` files (including `flashMP3.pic`), keys, licences (`.rap`, `act.dat`, `idps`), credentials.
- Run output: memory or local-store dumps, captured frames (`.ppm`/`.png`), audio recordings (`.wav`), logs (`.err`, `.out`, `.mon`, `.pilhas`), `cache.dat` and saves.

**Derivative work:** the recompiled executable embeds the game's code translated to C++. It is a derivative of the game and **must not be redistributed**. Everyone builds it locally from their own, legally obtained copy.

**Protection:** there are no keys here, no instructions for decrypting the executable or the data, and no code that circumvents protection. The port only reads files the user already has in plain form. The toolkit ships a routine that opens `NPD` containers; this port neither uses nor depends on it.

**Screenshots:** only a handful of images in `docs/screenshots/`, 1280×720 JPEGs up to 300 KB, captured from the port's own output to show the project's state. Raw frames (`.ppm`) and any other images stay local; `.gitignore` and CI reject images elsewhere.

**Before every commit:** check `git status` and `git diff --cached --stat`. The `.gitignore` is a safety net, not a substitute for judgement. When in doubt, leave it out.
