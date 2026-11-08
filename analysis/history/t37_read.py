"""Le o anel de overlay/rdr2_t37.c.

uso: t37_read.py <dir>
"""
import collections
import os
import re
import struct
import sys

CAMPOS = "seq ms kind a b c d e f g".split()
REGISTRO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "spu_jobs", "jobs_register.c")
IMG = {int(i): n for i, n in re.findall(r"spu_begin_image\((\d+)\); spujob_([0-9A-F]{4})",
                                        open(REGISTRO, encoding="utf-8").read())}
PONTOS = {1: "03B3 laco 21C8", 2: "03B3 entrada D0", 3: "03B3 compara anel BC0", 4: "03B3 GET CE0",
          5: "03B3 atraso D68", 6: "03B3 pede anel D80", 7: "C895 retorno 5264",
          8: "03B3 ponteiro 2288", 9: "03B3 entrada 2898", 10: "03B3 reserva GCM", 11: "03B3 GET 2010"}


def nome_img(i):
    return IMG.get(i, f"{i:#x}")


def anel(d, ofs, cap, n, tam):
    linhas = []
    for i in range(min(n, cap)):
        c = struct.unpack_from("<10I", d, ofs + i * tam)
        if c[0]:
            linhas.append(dict(zip(CAMPOS, c)))
    linhas.sort(key=lambda r: r["seq"])
    return linhas


def main():
    pasta = sys.argv[1]
    d = open(os.path.join(pasta, "t37.ring"), "rb").read()
    tam, cr, cp, cs, ce, ni, np, _ = struct.unpack_from("<8I", d, 0)
    nr, npo, ns, nev = struct.unpack_from("<4i", d, 32)
    ofs = 48
    pontos = struct.unpack_from(f"<{np}q", d, ofs)
    ofs += np * 8
    print(f"total: rsx={nr} poll={npo} amostras={ns} eventos={nev}")
    print("\n== pontos de sonda (passagens)")
    for k in sorted(PONTOS):
        print(f"  {k:2d} {PONTOS[k]:24s} {pontos[k]}")
    print("\n== jobs por imagem")
    print("  img   fingerprint  iniciados terminados  normais  anormais  stop3FFF  em_curso  ult_pc")
    tot = 0
    for i in range(ni):
        im, st, jb, no, ab, tr, pc, lj = struct.unpack_from("<8I", d, ofs + i * 32)
        if im:
            tot += jb
            print(f"  {nome_img(im):5s} {im:#010x} {st:9d} {jb:10d} {no:8d} {ab:9d} {tr:9d} {st - jb:9d}  {pc:#07x}")
    print(f"  total de jobs terminados: {tot}")
    ofs += ni * 32
    rsx = anel(d, ofs, cr, nr, tam)
    ofs += cr * tam
    poll = anel(d, ofs, cp, npo, tam)
    ofs += cp * tam
    samp = anel(d, ofs, cs, ns, tam)
    ofs += cs * tam
    ev = anel(d, ofs, ce, nev, tam)

    print("\n== escritas do RSX, por metodo e alvo")
    print("  via  metodo  alvo         ctx_dma      caminho   qtd   primeiro_ms ultimo_ms  ultimo_valor")
    grupos = collections.OrderedDict()
    for r in rsx:
        ch = (r["kind"], r["a"], r["c"], r["e"], r["g"])
        g = grupos.setdefault(ch, [0, r["ms"], r["ms"], 0])
        g[0] += 1
        g[2] = r["ms"]
        g[3] = r["b"]
    for (k, m, alvo, ctx, cam), (q, a, b, v) in sorted(grupos.items(), key=lambda x: (x[0][1], x[0][2])):
        via = "3D" if k == 1 else "406E"
        print(f"  {via:4s} {m:#06x}  {alvo:#010x}  {ctx:#010x}  {'resync' if cam else 'walker':7s} {q:6d} {a:9d} {b:9d}   {v:#010x}")
    alvos = {r["c"] for r in rsx if r["c"]}

    print("\n== sondas SPU")
    for k in sorted({r["kind"] for r in poll}):
        linhas = [r for r in poll if r["kind"] == k]
        print(f"-- {k} {PONTOS.get(k, '?')}: {len(linhas)} registros, {linhas[0]['ms']}..{linhas[-1]['ms']} ms")
        if k == 1:
            p = None
            for r in linhas:
                ch = (r["b"], r["c"], r["d"], r["f"])
                if ch != p:
                    print(f"     t={r['ms']:6d} idx={r['a']:#010x} limite={r['b']:#010x} r81={r['c']:#010x} r85={r['d']:#010x} job={r['f']:#010x} prof={r['g']}")
                p = ch
            continue
        if k == 7:
            p = None
            for r in linhas:
                ch = (r["b"], r["c"], r["f"])
                if ch != p:
                    print(f"     t={r['ms']:6d} ea={r['a']:#010x} rc={r['b']:#010x} mascara={r['c']:#010x} job={r['f']:#010x}")
                p = ch
            continue
        vistos = collections.OrderedDict()
        for r in linhas:
            ch = (r["a"], r["b"]) if k == 8 else (r["a"], r["b"], r["c"], r["d"])
            v = vistos.setdefault(ch, [0, r])
            v[0] += 1
        for ch, (q, r) in list(vistos.items())[:14]:
            print(f"     x{q:5d} t={r['ms']:6d} a={r['a']:#010x} b={r['b']:#010x} c={r['c']:#010x} d={r['d']:#010x} "
                  f"img={nome_img(r['e'])} job={r['f']:#010x} prof={r['g']}")
        u = linhas[-1]
        print(f"     ultimo t={u['ms']} a={u['a']:#010x} b={u['b']:#010x} c={u['c']:#010x} d={u['d']:#010x} job={u['f']:#010x}")

    print("\n== jobs raros: inicio")
    cont = collections.Counter()
    for r in [e for e in ev if e["kind"] == 3]:
        n = nome_img(r["a"])
        cont[n] += 1
        if n in ("03B3", "0D71", "5D35", "338C", "7639", "A672") or cont[n] <= 1:
            print(f"  t={r['ms']:6d} {n} job={r['b']:#010x} n={r['c']} tid={r['g']}")

    print("\n== jobs encerrados fora do retorno normal")
    for r in [e for e in ev if e["kind"] == 1]:
        print(f"  t={r['ms']:6d} img={nome_img(r['a'])} job={r['b']:#010x} pc={r['c']:#07x} stop={r['d']:#06x} "
              f"lr={r['e']:#07x} status={r['f']} sp={r['g']:#07x}")

    print("\n== enderecos observados, por mudanca")
    enderecos = collections.OrderedDict()
    for r in [e for e in ev if e["kind"] == 2]:
        enderecos.setdefault(r["a"], []).append(r)
    for ea, l in enderecos.items():
        print(f"-- {ea:#010x}: {len(l)} valores, {l[0]['ms']}..{l[-1]['ms']} ms; RSX escreve aqui: {any(ea <= x < ea + 16 for x in alvos)}")
        for r in l[:4] + (l[-6:] if len(l) > 10 else l[4:]):
            print(f"     t={r['ms']:6d} {r['b']:08X} {r['c']:08X} {r['d']:08X} {r['e']:08X}")

    print("\n== FIFO por janela de 1 s")
    print("  seg   put        get_guest  get_host   flips/s presents/s jobs/s  get==put  privadoMB")
    janelas = collections.OrderedDict()
    for r in samp:
        janelas.setdefault(r["ms"] // 1000, []).append(r)
    ant = None
    pico = 0
    for s, l in janelas.items():
        u = l[-1]
        pico = max(pico, max(r["g"] for r in l))
        iguais = sum(1 for r in l if r["a"] == r["c"])
        if ant and (s < 3 or 11 <= s <= 34 or s % 10 == 0):
            print(f"  {s:4d}  {u['a']:#010x} {u['b']:#010x} {u['c']:#010x} {u['d'] - ant['d']:7d} {u['e'] - ant['e']:9d} "
                  f"{u['f'] - ant['f']:6d}  {iguais}/{len(l)} {u['g']:9d}")
        ant = u
    print(f"  pico de memoria privada: {pico} MB; jobs no fim: {ant['f']}")


if __name__ == "__main__":
    main()
