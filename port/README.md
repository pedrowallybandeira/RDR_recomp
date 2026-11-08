# port/

Projeto CMake do executável `MyGameRecomp.exe`, derivado do `templates/project` do ps3recomp (MIT).

*CMake project for `MyGameRecomp.exe`, derived from ps3recomp's `templates/project` (MIT).*

| Arquivo | Origem | Mudanças |
| :--- | :--- | :--- |
| `CMakeLists.txt` | template | troca fontes do runtime pelos de `PORT_OVERLAY_DIR`; lê jobs SPU e plugins DSP de `PORT_LOCAL_DIR`; `ppu_recomp_023.cpp` com a sonda `[t54]` opcional; flags do MinGW |
| `main.cpp` | template da v0.18.0 | motor `rsx_live_draw` (D3D12) com `RSX_LIVE_DRAW=1`; `PARAM.SFO` lido no boot; registro de `cellSpursQueuePopBody`, `_cellSpursSemaphoreInitialize` e `cellKbRead`; amostrador `PS3_SAMPLE` |
| `stubs.cpp` | template | nenhuma |
| `src/fs_area.c` | próprio | `host_extend_file`, usado por `cellFsAllocateFileAreaWithoutZeroFill` |

Variáveis de CMake: `PS3RECOMP_DIR`, `RECOMP_DIR` (o lift), `PORT_LOCAL_DIR` (padrão `../local`), `PORT_OVERLAY_DIR` (padrão `PORT_LOCAL_DIR/overlay`), `PORT_SPU_INPUTS` (o ELF, para traduzir os SPUs embutidos). Use `scripts/build.ps1`.
