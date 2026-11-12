"""Tentativa 70: traduz o decodificador MP3 do Multistream (flashMP3.pic) e gera o registro.

O Multistream (imagem 517498422) copia o segmento de codigo do flashMP3.pic (offset
0x100 do arquivo, vaddr 0x80) para LS 0x1A100, a partir do EA 0x11E4BE80 (seg224:
os primeiros 16 KB do LS batem byte a byte com o arquivo). Traduz so .SpuGUID+.text
(vaddr 0x80..0x9430 -> LS 0x1A100..0x234B0) com base 0x1A100 e registra com
spu_overlay_register_verified_region: o despacho so usa o codigo traduzido depois
de conferir os bytes; se nao baterem, o interpretador segue.

O flashMP3.pic vem do firmware do proprio usuario: o codigo gerado fica so local
(local/spu_mp3), nunca no repositorio.

uso: lift_mp3.py <flashMP3.pic> <dir_saida>   (com PS3RECOMP_TOOLS, como o lift_jobs.py)
"""
import os
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # lift_jobs.py
import lift_jobs  # noqa: E402

BASE = 0x1A100          # LS de carga do vaddr 0x80
VBASE = 0x80
EA = 0x11E4BE80         # origem do GET para LS 0x1A100 (seg224)
IDENT = 0x1D5F0010


def le_elf(f):
    """Bytes de .SpuGUID+.text e os enderecos (vaddr) das funcoes da .symtab."""
    shoff, = struct.unpack_from(">I", f, 0x20)
    shentsize, shnum, shstrndx = struct.unpack_from(">HHH", f, 0x2E)
    sec = [struct.unpack_from(">IIIIIIIIII", f, shoff + i * shentsize) for i in range(shnum)]
    nomes = sec[shstrndx][4]
    nome = lambda s: f[nomes + s[0]:f.index(b"\0", nomes + s[0])].decode()
    por = {nome(s): s for s in sec}
    txt = por[".text"]
    fim_codigo = txt[3] + txt[5]                       # vaddr do fim de .text
    codigo = f[0x100:0x100 + (fim_codigo - VBASE)]
    st, ss = por[".symtab"], por[".strtab"]
    funcs = []
    for o in range(st[4], st[4] + st[5], 16):
        nm, val, tam, info, _, shndx = struct.unpack_from(">IIIBBH", f, o)
        if info & 0xF == 2 and val:
            n = f[ss[4] + nm:f.index(b"\0", ss[4] + nm)].decode()
            funcs.append((val, n))
    entry, = struct.unpack_from(">I", f, 0x18)
    return codigo, sorted(funcs), entry


def main():
    if len(sys.argv) != 3:
        sys.exit("uso: lift_mp3.py <flashMP3.pic> <dir_saida>")
    pic, saida = sys.argv[1:3]
    f = open(pic, "rb").read()
    codigo, funcs, entry = le_elf(f)
    ls = lambda v: v - VBASE + BASE
    entradas = sorted({ls(v) for v, _ in funcs} | {ls(entry)})
    pasta = os.path.join(saida, "mp3_1A100")
    os.makedirs(pasta, exist_ok=True)
    elf = os.path.join(pasta, "mp3_1A100.elf")
    open(elf, "wb").write(lift_jobs.wrap(codigo, base=BASE, entry=ls(entry)))
    prefixo = "mp3_1A100_"
    cmd = [sys.executable, "-I", os.path.join(lift_jobs.TOOLS, "spu_lifter.py"), elf, "--auto-functions", elf,
           "--symbol-prefix", prefixo, "-o", pasta, "--return-entries",
           "--extra-funcs", ",".join(f"0x{a:05X}" for a in entradas)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    open(os.path.join(pasta, "lift.log"), "w", encoding="utf-8").write(r.stdout + r.stderr)
    if r.returncode != 0:
        sys.exit(f"lift falhou\n{r.stderr[-1500:]}")
    lift_jobs.debase_includes(os.path.join(pasta, "spu_recomp.h"))
    lift_jobs.debase_includes(os.path.join(pasta, "spu_recomp.c"))
    traps = lift_jobs.trata_traps(os.path.join(pasta, "spu_recomp.c"))
    hdr = open(os.path.join(pasta, "spu_recomp.h"), encoding="utf-8", errors="ignore").read()
    print(f"mp3: {len(codigo)} B em LS 0x{BASE:05X}..0x{BASE + len(codigo):05X}, "
          f"{len(funcs)} simbolos, funcoes={hdr.count('spu_func_')}, traps={traps}")
    for v, n in funcs:
        print(f"  LS 0x{ls(v):05X} {n}")

    L = ["/* mp3_register.c -- GERADO por analysis/tools/lift_mp3.py. Codigo de firmware: so local. */",
         "#include <stdint.h>", '#include "spu_overlay_residency.h"', "",
         "extern void spu_begin_image(int image_id);",
         f"extern void {prefixo}spu_recomp_register(void);",
         f"static const uint8_t k_mp3[{len(codigo)}] = {{"]
    for j in range(0, len(codigo), 24):
        L.append("    " + ", ".join(f"0x{x:02X}" for x in codigo[j:j + 24]) + ",")
    L += ["};", "", "__attribute__((constructor)) static void mp3_register_ctor(void)", "{",
          f"    spu_begin_image({IDENT}); {prefixo}spu_recomp_register();",
          f"    {{ const spu_overlay_code_segment s = {{ 0x{BASE:05X}u, {len(codigo)}u, k_mp3 }};",
          f"      spu_overlay_register_verified_region(0x{EA:08X}u, 0x{BASE:05X}u, {len(codigo)}u, {IDENT}, &s, 1); }}",
          "    spu_begin_image(0);", "}", ""]
    open(os.path.join(saida, "mp3_register.c"), "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print("registro gerado")


if __name__ == "__main__":
    main()
