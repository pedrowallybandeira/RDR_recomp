"""Le o anel de overlay/spu_probe.c e compara a memoria local salva com o job original.

uso: probe_read.py <dir_sonda> <job.bin>
"""
import collections
import glob
import os
import struct
import sys

CAMPOS = "seq tid lr r9 r5 r79 r4 r2 q0 q1 q2 q3 pc tick r3 pad".split()
DIAG_MARK = 0xC0DE0001


def main():
    pasta, job = sys.argv[1:3]
    d = open(os.path.join(pasta, "probe_2c10.ring"), "rb").read()
    total, tam, recs = struct.unpack_from("<iII", d, 0)
    print(f"total={total} registro={tam} anel={recs}")
    print("--- cadeias: voltas, jobs, reexecutados, descritor mudou, mudou em reexecucao")
    for i in range(16):
        jc, walks, jobs, re, ch, chr_, last, _ = struct.unpack_from("<8I", d, 64 + recs * tam + i * 32)
        if jc:
            pct = 100 * re / jobs if jobs else 0
            print(f"  {jc:#010x} voltas={walks} jobs={jobs} reexec={re} ({pct:.1f}%) mudou={ch} mudou_reexec={chr_}")
    linhas = []
    mudancas = []
    for i in range(min(total, recs)):
        c = struct.unpack_from("<16I", d, 64 + i * tam)
        if not c[0]:
            continue
        r = dict(zip(CAMPOS, c))
        (mudancas if r["lr"] == DIAG_MARK else linhas).append(r)
    mudancas.sort(key=lambda r: r["seq"])
    print(f"--- descritores trocados durante o job: {len(mudancas)}")
    for r in mudancas[:16]:
        print(f"  cadeia={r['r79']:#010x} idx={r['r9']} job={r['r4']:#010x} "
              f"bin {r['r5']:#010x} -> {r['r2']:#010x} reexec={r['r3']} tid={r['tid']}")
    linhas.sort(key=lambda r: r["seq"])
    print(f"registros validos={len(linhas)}")
    if not linhas:
        return
    print("indice >26:", sum(1 for r in linhas if r["r9"] > 26))
    print("entrada zero (r2==r5):", sum(1 for r in linhas if r["r2"] == r["r5"]))
    print("threads:", collections.Counter(r["tid"] for r in linhas).most_common(6))
    print("r5:", collections.Counter(hex(r["r5"]) for r in linhas).most_common(4))
    print("r79:", collections.Counter(hex(r["r79"]) for r in linhas).most_common(4))
    print("--- (indice, destino) mais comuns")
    for (i, a), n in collections.Counter((r["r9"], r["r2"]) for r in linhas).most_common(14):
        print(f"  {n:8d} indice={i} destino={a:#x}")
    print("--- ultimos registros")
    for r in linhas[-8:]:
        print(f"  seq={r['seq']} tid={r['tid']} lr={r['lr']:#x} r9={r['r9']} r5={r['r5']:#x} "
              f"r2={r['r2']:#x} pc={r['pc']:#x} q={r['q0']:08x} {r['q1']:08x} {r['q2']:08x} {r['q3']:08x}")
    if len(linhas) > 1:
        dt = (linhas[-1]["tick"] - linhas[0]["tick"]) & 0xFFFFFFFF
        print(f"janela: {len(linhas)} registros em {dt} ticks")

    original = open(job, "rb").read()
    for caminho in sorted(glob.glob(os.path.join(pasta, "probe_ls_seq*.bin"))):
        ls = open(caminho, "rb").read()
        n = len(original)
        dif = [i for i in range(0, n, 4) if ls[i:i + 4] != original[i:i + 4]]
        print(f"\n{os.path.basename(caminho)}: {len(ls)} B; palavras diferentes do binario: {len(dif)} de {n // 4}")
        faixas = []
        for i in dif:
            if faixas and i - faixas[-1][1] <= 16:
                faixas[-1][1] = i
            else:
                faixas.append([i, i])
        for a, b in faixas[:24]:
            print(f"  {a:#07x}-{b + 3:#07x} ({b + 4 - a} B) ls={ls[a:a + 4].hex()} bin={original[a:a + 4].hex()}")
        if len(faixas) > 24:
            print(f"  ... mais {len(faixas) - 24} faixas")
        print("  tabela LS 0x2C4C:", ls[0x2C4C:0x2C5C].hex(), "binario:", original[0x2C4C:0x2C5C].hex())


if __name__ == "__main__":
    main()
