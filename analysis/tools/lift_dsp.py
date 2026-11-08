"""Traduz os plugins DSP do Multistream capturados em LS 0x36800 e gera o registro.

Cada dump ovl_<EA>_<hash>.bin e um slot de 12 KB, sempre carregado em LS 0x36800
a partir do EA do nome. O registro usa spu_overlay_register_verified_region: um
GET desse EA para 0x36800 torna o modulo residente, e o despacho so usa o codigo
traduzido depois de conferir os bytes. Se nao baterem, o interpretador segue.

uso (da raiz do projeto): lift_dsp.py <dir_dumps> <dir_saida>
"""
import glob
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # lift_jobs.py
import lift_jobs  # noqa: E402  (traz debase_includes e wrap do toolkit)

BASE = 0x36800
# Entradas observadas nos logs (destinos de bisl e seus vizinhos), as mesmas para
# todo modulo: separar uma funcao num ponto que nao e entrada so troca a queda
# por uma transferencia direta.
ENTRADAS = [0x368F8, 0x36900, 0x36928, 0x36930, 0x36978, 0x36980, 0x36B28, 0x36D28,
            0x37610, 0x37648, 0x376A8, 0x37D70, 0x38D10, 0x38D60, 0x38F50]
ID_BASE = 0x1D5F0001


def main():
    dumps, saida = sys.argv[1:3]
    os.makedirs(saida, exist_ok=True)
    mods = []
    for i, f in enumerate(sorted(glob.glob(os.path.join(dumps, "ovl_*.bin")))):
        m = re.match(r"ovl_([0-9A-F]{8})_([0-9A-F]{16})\.bin", os.path.basename(f))
        ea = int(m.group(1), 16)
        codigo = open(f, "rb").read()
        nome = f"dsp_{m.group(1)}"
        pasta = os.path.join(saida, nome)
        os.makedirs(pasta, exist_ok=True)
        elf = os.path.join(pasta, nome + ".elf")
        open(elf, "wb").write(lift_jobs.wrap(codigo, base=BASE, entry=BASE))
        prefixo = nome + "_"
        cmd = [sys.executable, "-I", os.path.join(lift_jobs.TOOLS, "spu_lifter.py"), elf, "--auto-functions", elf,
               "--symbol-prefix", prefixo, "-o", pasta, "--return-entries",
               "--extra-funcs", ",".join(f"0x{a:05X}" for a in ENTRADAS)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        open(os.path.join(pasta, "lift.log"), "w", encoding="utf-8").write(r.stdout + r.stderr)
        if r.returncode != 0:
            sys.exit(f"{nome}: lift falhou\n{r.stderr[-800:]}")
        lift_jobs.debase_includes(os.path.join(pasta, "spu_recomp.h"))
        lift_jobs.debase_includes(os.path.join(pasta, "spu_recomp.c"))
        traps = lift_jobs.trata_traps(os.path.join(pasta, "spu_recomp.c"))
        hdr = open(os.path.join(pasta, "spu_recomp.h"), encoding="utf-8", errors="ignore").read()
        print(f"{nome}: EA 0x{ea:08X}, {len(codigo)} B, funcoes={hdr.count('spu_func_')}, traps={traps}")
        mods.append((nome, prefixo, ea, codigo, ID_BASE + i))

    L = ["/* dsp_register.c -- GERADO por exp_t49/dsp/lift_dsp.py. */",
         "#include <stdint.h>", '#include "spu_overlay_residency.h"', "",
         "extern void spu_begin_image(int image_id);"]
    for nome, prefixo, ea, codigo, ident in mods:
        L.append(f"extern void {prefixo}spu_recomp_register(void);")
        L.append(f"static const uint8_t k_{nome}[{len(codigo)}] = {{")
        for j in range(0, len(codigo), 24):
            L.append("    " + ", ".join(f"0x{x:02X}" for x in codigo[j:j + 24]) + ",")
        L.append("};")
    L += ["", "__attribute__((constructor)) static void dsp_register_ctor(void)", "{"]
    for nome, prefixo, ea, codigo, ident in mods:
        L += [f"    spu_begin_image({ident}); {prefixo}spu_recomp_register();",
              f"    {{ const spu_overlay_code_segment s = {{ 0x{BASE:05X}u, {len(codigo)}u, k_{nome} }};",
              f"      spu_overlay_register_verified_region(0x{ea:08X}u, 0x{BASE:05X}u, {len(codigo)}u, {ident}, &s, 1); }}"]
    L += ["    spu_begin_image(0);", "}", ""]
    open(os.path.join(saida, "dsp_register.c"), "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"registro: {len(mods)} modulos")


if __name__ == "__main__":
    main()
