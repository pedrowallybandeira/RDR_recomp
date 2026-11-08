#!/usr/bin/env python3
"""Gera a imagem composta do job 7639 com os 20 trechos de overlay carregados

no Local Store (0x60B0 a 0x9940) e traduz para C++ usando o spu_lifter.
"""
import os
import shutil
import subprocess
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TOOLS_DIR = os.path.join(BASE_DIR, "referencias", "ps3recomp-v0.18.0", "tools")
sys.path.insert(0, TOOLS_DIR)

from wrap_spu_elf import wrap
from build_spu_workloads import debase_includes

TRAP = "ctx->stop_code = 0x3FFFu; ctx->status = SPU_STATUS_STOPPED_BY_STOP; spu_stop(ctx); return;"
TRAP_NOVO = "ctx->stop_code = 0x3FFFu; ctx->status = SPU_STATUS_STOPPED_BY_HALT; spu_halt(ctx); return;"


def trata_traps(caminho):
    texto = open(caminho, encoding="utf-8").read()
    open(caminho, "w", encoding="utf-8", newline="\n").write(texto.replace(TRAP, TRAP_NOVO))
    return texto.count(TRAP)


def main():
    job_dir = os.path.join(BASE_DIR, "build_rdr2", "work_v3", "spu_jobs", "spujob_763921CDE433197C_22496")
    orig_bin_path = os.path.join(BASE_DIR, "build_rdr2", "spu_dumps_t42", "spujob_763921CDE433197C_22496.bin")
    ls_dump_path = os.path.join(BASE_DIR, "build_rdr2", "sonda44a", "ls_k7639.bin")

    print(f"[lift_7639_composite] Lendo binario base: {orig_bin_path}")
    with open(orig_bin_path, "rb") as f:
        orig = f.read()
    assert len(orig) == 22496, f"Tamanho inesperado do job base: {len(orig)}"

    print(f"[lift_7639_composite] Lendo trechos de overlay: {ls_dump_path}")
    with open(ls_dump_path, "rb") as f:
        f.seek(0x60B0)
        chunks = f.read(0x9940 - 0x60B0)
    assert len(chunks) == (0x9940 - 0x60B0), f"Tamanho inesperado dos chunks: {len(chunks)}"

    padding = b"\x00" * (0x60B0 - len(orig))
    composite = orig + padding + chunks
    print(f"[lift_7639_composite] Imagem composta montada: {len(composite)} bytes (LS 0x0000 a 0x{len(composite):05X})")

    elf_path = os.path.join(job_dir, "spujob_763921CDE433197C_22496.elf")
    open(elf_path, "wb").write(wrap(composite, base=0, entry=0))

    # 20 pontos de entrada dos trechos (lsa e lsa+4)
    lsas = [
        0x060B0, 0x062D0, 0x06310, 0x06830, 0x068D0,
        0x06B70, 0x06C30, 0x06C80, 0x06CC0, 0x070F0,
        0x07240, 0x07570, 0x07630, 0x07850, 0x07CB0,
        0x08380, 0x08420, 0x08840, 0x08900, 0x09870,
    ]
    entries = []
    for lsa in lsas:
        entries.append(f"0x{lsa:04X}")
        entries.append(f"0x{lsa+4:04X}")
    extra_funcs = ",".join(entries)

    prefixo = "spujob_763921CDE433197C_22496_"
    cmd = [
        sys.executable, "-I", os.path.join(TOOLS_DIR, "spu_lifter.py"),
        elf_path,
        "--auto-functions", elf_path,
        "--extra-funcs", extra_funcs,
        "--return-entries",
        "--symbol-prefix", prefixo,
        "-o", job_dir,
    ]

    print("[lift_7639_composite] Executando spu_lifter...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    with open(os.path.join(job_dir, "lift.log"), "w", encoding="utf-8") as f:
        f.write(r.stdout + r.stderr)

    if r.returncode != 0:
        print(f"[lift_7639_composite] ERRO no spu_lifter:\n{r.stderr[-800:]}")
        sys.exit(1)

    c_path = os.path.join(job_dir, "spu_recomp.c")
    h_path = os.path.join(job_dir, "spu_recomp.h")
    debase_includes(h_path)
    debase_includes(c_path)
    traps = trata_traps(c_path)

    hdr = open(h_path, encoding="utf-8", errors="ignore").read()
    func_count = hdr.count("spu_func_")
    print(f"[lift_7639_composite] Concluido com sucesso!")
    print(f"  - Arquivo C: {c_path} ({os.path.getsize(c_path)} bytes)")
    print(f"  - Funcoes geradas: {func_count}")
    print(f"  - Traps tratados: {traps}")


if __name__ == "__main__":
    main()
