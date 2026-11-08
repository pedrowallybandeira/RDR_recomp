"""Le a parte da tentativa 40 no anel de overlay/rdr2_t37.c.

uso: t40_read.py <dir>
"""
import collections
import os
import struct
import sys

CAMPOS = "seq ms kind a b c d e f g".split()
LABEL_BASE = 0x20000000


def anel(d, ofs, cap, n, tam):
    linhas = []
    for i in range(min(n, cap)):
        c = struct.unpack_from("<10I", d, ofs + i * tam)
        if c[0]:
            linhas.append(dict(zip(CAMPOS, c)))
    linhas.sort(key=lambda r: r["seq"])
    return linhas


def texto(a, b):
    return struct.pack("<II", a, b).split(b"\0")[0].decode("ascii", "replace")


def linha_estado(r):
    return (f"t={r['ms']:6d} contador={r['a']:#010x} rotulo={r['b']:#010x} idx={r['c']:#04x} "
            f"ctx={r['d']:#010x} current={r['e']:#010x} put={r['f']:#010x} getoff={r['g']:#010x}")


def main():
    pasta = sys.argv[1]
    d = open(os.path.join(pasta, "t37.ring"), "rb").read()
    tam, cr, cp, cs, ce, ni, np, _ = struct.unpack_from("<8I", d, 0)
    nr, _, _, nev = struct.unpack_from("<4i", d, 32)
    ofs = 48
    pontos = struct.unpack_from(f"<{np}q", d, ofs)
    ofs += np * 8 + ni * 32
    rsx = anel(d, ofs, cr, nr, tam)
    ofs += (cr + cp + cs) * tam
    ev = anel(d, ofs, ce, nev, tam)
    ofs += ce * tam
    nt, ct = struct.unpack_from("<iI", d, ofs)
    t40 = anel(d, ofs + 16, ct, nt, tam)

    print(f"voltas do laco 0x59B364: {pontos[12]}; chamadas de recycle: {pontos[13]}")
    print("\n== quem chama cellGcmGetLabelAddress")
    for r in [e for e in ev if e["kind"] == 5]:
        print(f"  t={r['ms']:6d} r13={r['a']:#010x} lr={r['b']:#010x} tid={r['g']}")

    esperas = [r for r in t40 if r["kind"] == 2]
    amostras = [r for r in t40 if r["kind"] == 1]
    print(f"\n== esperas da render: {len(esperas)}; ultimas 12")
    for r in esperas[-12:]:
        print("  " + linha_estado(r))
    print("\n== amostras, so quando contador, rotulo, current ou put mudam (ultimas 24)")
    mudas, p = [], None
    for r in amostras:
        ch = (r["a"], r["b"], r["c"], r["e"], r["f"])
        if ch != p:
            mudas.append(r)
        p = ch
    for r in mudas[-24:]:
        print("  " + linha_estado(r))
    if amostras:
        print("  ultima " + linha_estado(amostras[-1]))

    print("\n== ressincronizacoes")
    for r in ev:
        if r["kind"] == 4:
            print(f"  t={r['ms']:6d} {texto(r['a'], r['b']):9s} get={r['c']:#010x} put={r['d']:#010x} pouso={r['e']:#010x}")
        elif r["kind"] == 6:
            print(f"      fim from={r['a']:#010x} pouso={r['b']:#010x} parou={r['c']:#010x} palavra={r['d']:#010x} "
                  f"cercas={r['e']} rotulos={r['f']}")

    print("\n== parks abandonados que mudaram depois")
    for r in [e for e in ev if e["kind"] == 8]:
        print(f"  t={r['ms']:6d} io={r['a']:#010x} {r['b']:#010x} -> {r['c']:#010x} {r['d']} ms depois do resync")

    print("\n== recycle (primeiros 6 e ultimos 6)")
    rec = [e for e in ev if e["kind"] == 7]
    for r in rec[:6] + (rec[-6:] if len(rec) > 12 else rec[6:]):
        print(f"  t={r['ms']:6d} ctx={r['a']:#010x} begin={r['b']:#010x} current={r['c']:#010x} put={r['d']:#010x} "
              f"getoff={r['e']:#010x} tid={r['g']}")

    idx = amostras[-1]["c"] if amostras else 0
    alvo = LABEL_BASE + idx * 0x10
    print(f"\n== escritas no rotulo {alvo:#010x}, por metodo e caminho")
    grupos = collections.OrderedDict()
    for r in rsx:
        if r["c"] == alvo:
            ch = (r["kind"], r["a"], r["g"])
            g = grupos.setdefault(ch, [0, r["ms"], r["ms"], 0, 0])
            g[0] += 1
            g[2] = r["ms"]
            g[3] = r["b"]
            g[4] = r["f"]
    for (k, m, cam), (q, a, b, v, io) in grupos.items():
        print(f"  {'3D' if k == 1 else '406E':4s} {m:#06x} {'resync' if cam else 'walker':7s} {q:6d} {a:7d}..{b:7d} "
              f"ultimo={v:#010x} io={io:#010x}")
    print("  ultimas 8:")
    for r in [r for r in rsx if r["c"] == alvo][-8:]:
        print(f"    t={r['ms']:6d} metodo={r['a']:#06x} valor={r['b']:#010x} io={r['f']:#010x} "
              f"{'resync' if r['g'] else 'walker'}")


if __name__ == "__main__":
    main()
