# Análise / Analysis

Ferramentas escritas durante o port. Nenhuma contém dados do jogo; todas leem arquivos que ficam na sua pasta local. Nenhuma decripta nada.

*Tools written during the port. None contains game data; all of them read files that stay in your local tree, and none decrypts anything. Most docstrings are in Portuguese.*

**Layout esperado / expected layout:** a maioria foi escrita para a árvore de trabalho original do autor e procura os arquivos a partir de `RDR_ROOT` (padrão: a pasta atual):

| Caminho sob `RDR_ROOT` | Conteúdo |
| :--- | :--- |
| `referencias/ps3recomp-v0.18.0/tools/` | ferramentas do ps3recomp (`ppu_disasm`, `spu_lifter`, `wrap_spu_elf`…) |
| `build_rdr2/baseline_v1/entradas/RDR2.elf` (+ `.imports.json`) | ELF e listas do `ppu_loader.py` |
| `build_rdr2/work_v3/` | build, `boots/`, overlay |

`lift_jobs.py` também aceita `RDR_ELF` e `PS3RECOMP_TOOLS`. Ajuste os caminhos ou crie esse layout com links.

## `tools/` — em uso

| Ferramenta | Para quê |
| :--- | :--- |
| `lift_jobs.py` | traduz jobs SPURS capturados com `SPU_DUMP_MISS` e gera `jobs_register.c` (inclui as imagens compostas e as pontes de jobs específicos) |
| `lift_dsp.py` | traduz os plugins DSP do Multistream capturados com `SPU_DUMP_OVL` (`dsp_register.c`) |
| `fpbusca.c` | acha no ELF o trecho cujo fingerprint FNV-1a bate com o de um job |
| `nid_spurs.py`, `nid_call.py` | nomeia os NIDs de `cellSpurs` importados; mostra as chamadas a um import |
| `boot_resumo.py` | resume um boot: mensagens do jogo, imports sem handler, SPU pedido |
| `pilhas.ps1`, `pilhas_resumo.py`, `pilhas_de.py`, `rva2sym.py` | lê as pilhas capturadas com `boot_seguro.ps1 -Sonda` (`hsamp_tudo.exe`) |
| `hsamp.c`, `hsamp_todas.c`, `hsamp_tudo.c` | amostradores de pilha externos (só leem o processo; compile com o clang do llvm-mingw) |
| `ppm2png.py` | converte quadros de `LD_FRAME_DUMP` (os quadros ficam locais) |
| `ppu_view.py`, `spu_view.py`, `xref.py`, `ref_find.py`, `disp_find.py`, `find_imm.py`, `find_oris.py`, `str_peek.py`, `bindiff.py` | leitura estática do ELF e de dumps: desmontagem, referências, constantes |
| `ls_inspect.py`, `probe_read.py` | lê cópias do LS e anéis das sondas |
| `vfs_fill.py` | copia os seus dados abertos para o VFS com SHA-256 e manifesto |
| `xinput_teste.py` | lista os controles XInput |

## `experiments/` — tentativa 67 (áudio), fora do build adotado

| Arquivo | Para quê |
| :--- | :--- |
| `exp_build.py` | recompila só alguns TUs e liga um executável separado reaproveitando o `build.ninja` (`RDR_BUILD`, `LLVM_MINGW_BIN`) |
| `gera_m2mf.py` | cópia do `cellGcmSys.c` com NV0039 (memória a memória) no subcanal 1, `GCM_SUBCH1_M2MF=1` |
| `audit.c`, `gera_audit.py` | sonda de DMA do SPU (`SPU_AUDIT_*`) |
| `gera_ww.py` | `PPU_WWATCH_STACKFN`: pilha do jogo quando a escrita vigiada vem de uma função |

## `history/` — tentativas anteriores

Geradores e sondas já incorporados ao patch ou abandonados, guardados como registro: `gera.py`, `gera_cadeia.py`, `gera_job.py`, `gera_v14a.py` (geraram mudanças hoje em `patches/`), `rdr2_t37.c`, `rdr2_t38.c`, `spu_probe.c`, `t37_*`, `t38_tabela.py`, `t40_read.py`, `t42_read.py`, `t44_*` (sondas das tentativas 31–44), `lift_7639_composite.py` (imagem composta do job `7639`, tentativa 45). Usam o layout original e podem não rodar como estão.
