"""Traduz binarios de job SPURS capturados com SPU_DUMP_MISS e gera o registro.

spu_run_spurs_job carrega o binario em LS 0 e entra em 0, entao cada dump vira um
ELF SPU com base 0 e passa pelo spu_lifter do toolkit. O registro usa o fingerprint
dos bytes crus, que e o que spu_workload_dispatch_job calcula.

uso: lift_jobs.py <dir_dumps> <dir_saida>
"""
import glob
import os
import re
import struct
import subprocess
import sys

# PS3RECOMP_TOOLS: tools/ do ps3recomp (spu_lifter, wrap_spu_elf, build_spu_workloads).
ROOT = os.environ.get("RDR_ROOT", os.getcwd())
TOOLS = os.environ.get("PS3RECOMP_TOOLS", os.path.join(ROOT, "referencias", "ps3recomp-v0.18.0", "tools"))
ELF_JOGO = os.environ.get("RDR_ELF", os.path.join(ROOT, "build_rdr2", "baseline_v1", "entradas", "RDR2.elf"))
sys.path.insert(0, TOOLS)
from build_spu_workloads import debase_includes, fnv1a64  # noqa: E402
from wrap_spu_elf import wrap  # noqa: E402


# Rotinas da biblioteca SPU embutida no job que mexem em estado SPURS que o runtime
# guarda no host. grcore/edge_jobs.cpp, dentro do C895, chama estas duas para tocar a
# cadeia EDGE/GFX; o corpo traduzido falharia em cima das estruturas do jogo.
PONTES = {
    "spujob_C895B508A51CD2A6_79376": {
        0xF440: "rdr2_spu_job_guard_notify",
        0xF678: "rdr2_spu_run_job_chain",
    },
}


# Trechos que o job copia do ELF para o proprio scratch a cada execucao e chama por
# ponteiro: (lsa, ea, tamanho), como nos GETs. Interpretados, o retorno de uma funcao
# traduzida cai no meio do trecho e a pilha do host se perde (tentativas 44 e 45). As
# instrucoes e os enderecos de LS sao fixos, entao entram na imagem do proprio job. O
# fingerprint continua sendo o dos bytes do job.
COMPOSTOS = {
    "spujob_763921CDE433197C_22496": [
        (0x060B0, 0x012FFE00, 544), (0x062D0, 0x01300080, 64), (0x06310, 0x01300D80, 1312),
        (0x06830, 0x01301300, 160), (0x068D0, 0x012FFA00, 672), (0x06B70, 0x012FFD00, 192),
        (0x06C30, 0x01304180, 80), (0x06C80, 0x01304200, 64), (0x06CC0, 0x01303600, 1072),
        (0x070F0, 0x01303A80, 336), (0x07240, 0x01300900, 816), (0x07570, 0x01300C80, 192),
        (0x07630, 0x012E4B00, 544), (0x07850, 0x012E4D80, 1120), (0x07CB0, 0x01300100, 1744),
        (0x08380, 0x01300800, 160), (0x08420, 0x01303C00, 1056), (0x08840, 0x01304080, 192),
        (0x08900, 0x012FE980, 3952), (0x09870, 0x012FF900, 208),
    ],
}


def ler_ea(elf, ea, tam):
    ph = struct.unpack_from(">Q", elf, 32)[0]
    for k in range(struct.unpack_from(">H", elf, 56)[0]):
        t, _, o, va, _, fs = struct.unpack_from(">IIQQQQ", elf, ph + k * 56)
        if t == 1 and va <= ea and ea + tam <= va + fs:
            return elf[o + ea - va:o + ea - va + tam]
    sys.exit(f"EA {ea:#x} fora dos segmentos do ELF")


def imagem_composta(codigo, trechos):
    elf = open(ELF_JOGO, "rb").read()
    imagem = bytearray(codigo)
    for lsa, ea, tam in trechos:
        if lsa < len(imagem):
            sys.exit(f"trecho em LS {lsa:#x} sobrepoe a imagem")
        imagem += bytes(lsa - len(imagem)) + ler_ea(elf, ea, tam)
    return bytes(imagem)


# stop 0x3FFF e o __builtin_trap do GCC do SPU: nao ha retomada. Como retorno comum, o
# drain volta ao mesmo pc e o job fica preso para sempre, segurando a thread da cadeia.
TRAP = "ctx->stop_code = 0x3FFFu; ctx->status = SPU_STATUS_STOPPED_BY_STOP; spu_stop(ctx); return;"
TRAP_NOVO = "ctx->stop_code = 0x3FFFu; ctx->status = SPU_STATUS_STOPPED_BY_HALT; spu_halt(ctx); return;"


def trata_traps(caminho):
    texto = open(caminho, encoding="utf-8").read()
    open(caminho, "w", encoding="utf-8", newline="\n").write(texto.replace(TRAP, TRAP_NOVO))
    return texto.count(TRAP)


def aplica_pontes(caminho, prefixo, pontes):
    texto = open(caminho, encoding="utf-8").read()
    for pc, destino in pontes.items():
        cabeca = f"void {prefixo}spu_func_{pc:08X}(spu_context* ctx) {{\n"
        ini = texto.find(cabeca)
        fim = texto.find("\n}\n", ini)
        if ini < 0 or fim < 0:
            sys.exit(f"{prefixo}: funcao {pc:#x} nao encontrada para a ponte")
        corpo = (f"        extern void {destino}(spu_context*);\n"
                 f"        {destino}(ctx);\n"
                 f"        SPU_RET(ctx);")
        texto = texto[:ini + len(cabeca)] + corpo + texto[fim:]
    open(caminho, "w", encoding="utf-8", newline="\n").write(texto)


def main():
    dumps, saida = sys.argv[1:3]
    os.makedirs(saida, exist_ok=True)
    jobs = []
    for bin_path in sorted(glob.glob(os.path.join(dumps, "spujob_*.bin"))):
        nome = os.path.splitext(os.path.basename(bin_path))[0]
        codigo = open(bin_path, "rb").read()
        fp = int(re.match(r"spujob_([0-9A-F]{16})_", nome).group(1), 16)
        if fnv1a64(codigo) != fp:
            sys.exit(f"{nome}: fingerprint nao confere ({fnv1a64(codigo):016X})")
        pasta = os.path.join(saida, nome)
        os.makedirs(pasta, exist_ok=True)
        elf = os.path.join(pasta, nome + ".elf")
        trechos = COMPOSTOS.get(nome)
        open(elf, "wb").write(wrap(imagem_composta(codigo, trechos) if trechos else codigo, base=0, entry=0))
        prefixo = nome + "_"
        cmd = [sys.executable, "-I", os.path.join(TOOLS, "spu_lifter.py"), elf, "--auto-functions", elf,
               "--symbol-prefix", prefixo, "-o", pasta]
        if trechos:
            entradas = [f"0x{a:04X}" for lsa, _, _ in trechos for a in (lsa, lsa + 4)]
            cmd += ["--extra-funcs", ",".join(entradas), "--return-entries"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        open(os.path.join(pasta, "lift.log"), "w", encoding="utf-8").write(r.stdout + r.stderr)
        if r.returncode != 0:
            sys.exit(f"{nome}: lift falhou\n{r.stderr[-800:]}")
        debase_includes(os.path.join(pasta, "spu_recomp.h"))
        debase_includes(os.path.join(pasta, "spu_recomp.c"))
        if nome in PONTES:
            aplica_pontes(os.path.join(pasta, "spu_recomp.c"), prefixo, PONTES[nome])
        traps = trata_traps(os.path.join(pasta, "spu_recomp.c"))
        hdr = open(os.path.join(pasta, "spu_recomp.h"), encoding="utf-8", errors="ignore").read()
        if f"{prefixo}spu_func_00000000(" not in hdr:
            sys.exit(f"{nome}: entrada em LS 0 nao traduzida")
        print(f"{nome}: {len(codigo)} B, funcoes={hdr.count('spu_func_') // 1}, traps={traps}")
        jobs.append((nome, prefixo, fp))

    L = ["/* jobs_register.c -- GENERATED by tools/lift_jobs.py. */", '#include "spu_workload.h"', "",
         "extern void spu_begin_image(int image_id);", ""]
    for nome, prefixo, fp in jobs:
        L += [f"extern void {prefixo}spu_func_00000000(spu_context*);",
              f"extern void {prefixo}spu_recomp_register(void);"]
    L += ["", "__attribute__((constructor)) static void jobs_register_ctor(void)", "{"]
    for nome, prefixo, fp in jobs:
        i = (fp & 0x0FFFFFFF) | 0x10000000
        L += [f"    spu_begin_image({i}); {prefixo}spu_recomp_register();",
              f"    spu_workload_register_img(0x{fp:016X}ULL, {prefixo}spu_func_00000000, {i}, \"{nome}\");"]
    L += ["    spu_begin_image(0);", "}", ""]
    open(os.path.join(saida, "jobs_register.c"), "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"registro: {len(jobs)} jobs")


if __name__ == "__main__":
    main()
