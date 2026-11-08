"""Linha do tempo da tentativa 42, a partir do anel de overlay/rdr2_t37.c.

uso: t42_read.py <dir_sonda> <arquivo.err>
"""
import collections
import glob
import os
import re
import struct
import sys

CAMPOS = "seq ms kind a b c d e f g".split()
REG_LO, REG_SIZE = 0x5000, 0xD000
REGISTRO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "spu_jobs", "jobs_register.c")
IMG = {int(i): n for i, n in re.findall(r"spu_begin_image\((\d+)\); spujob_([0-9A-F]{4})",
                                        open(REGISTRO, encoding="utf-8").read())}
OPS = {1: "espera", 2: "acorda", 3: "post  "}


def nome_img(i):
    return IMG.get(i, "tarefa" if i == 0 else f"{i:#x}")


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


def nomes_threads(err):
    tids = {}
    for l in open(err, encoding="utf-8", errors="replace"):
        m = re.search(r'sys_ppu_thread_create tid=(\d+) name="([^"]*)"', l)
        if m:
            tids[int(m.group(1))] = m.group(2)
    return tids


def le_tudo(pasta):
    d = open(os.path.join(pasta, "t37.ring"), "rb").read()
    tam, cr, cp, cs, ce, ni, np, _ = struct.unpack_from("<8I", d, 0)
    _, _, _, nev = struct.unpack_from("<4i", d, 32)
    ofs = 48
    pontos = struct.unpack_from(f"<{np}q", d, ofs)
    ofs += np * 8 + ni * 32 + (cr + cp + cs) * tam
    ev = anel(d, ofs, ce, nev, tam)
    ofs += ce * tam
    nt, ct = struct.unpack_from("<iI", d, ofs)
    t40 = anel(d, ofs + 16, ct, nt, tam)
    ofs += 16 + ct * tam
    npu, nre, nch, nse = struct.unpack_from("<4i", d, ofs)
    cpu, cre, cch, cse, nsn, tsn, njt, _ = struct.unpack_from("<8I", d, ofs + 16)
    ofs += 48
    puts = anel(d, ofs, cpu, npu, tam)
    ofs += cpu * tam
    reads = anel(d, ofs, cre, nre, tam)
    ofs += cre * tam
    chg = anel(d, ofs, cch, nch, tam)
    ofs += cch * tam
    sem = anel(d, ofs, cse, nse, tam)
    ofs += cse * tam
    snaps = []
    for i in range(nsn):
        s = struct.unpack_from("<8I", d, ofs + i * 32)
        if s[0]:
            snaps.append((s, ofs + nsn * 32 + i * tsn))
    snaps.sort()
    return d, pontos, ev, t40, puts, reads, chg, sem, snaps, (npu, nre, nch, nse)


def palavra(d, base, io):
    return struct.unpack_from(">I", d, base + io - REG_LO)[0]


def main():
    pasta, err = sys.argv[1:3]
    d, pontos, ev, t40, puts, reads, chg, sem, snaps, totais = le_tudo(pasta)
    tids = nomes_threads(err)
    tnome = lambda t: tids.get(t, f"tid{t}")
    print(f"PUTs no anel={totais[0]} leituras={totais[1]} mudancas={totais[2]} semaforos={totais[3]} "
          f"voltas_laco={pontos[12]}")

    amostras = [r for r in t40 if r["kind"] == 1]
    ult = amostras[-1]
    t_put = next(r["ms"] for r in amostras if r["f"] == ult["f"])
    resyncs = [e for e in ev if e["kind"] == 4]
    fins = [e for e in ev if e["kind"] == 6]
    print(f"\n== resumo\n  contador={ult['a']:#x} rotulo={ult['b']:#x} put_final={ult['f']:#x} put_parou t={t_put}")
    print(f"  ressincronizacoes={len(resyncs)}" + (f", primeira t={resyncs[0]['ms']}" if resyncs else ""))
    if resyncs:
        ordem = "ANTES" if t_put < resyncs[0]["ms"] else "depois"
        print(f"  put parou {ordem} da primeira ressincronizacao ({resyncs[0]['ms'] - t_put} ms)")
    for r in resyncs[:4]:
        print(f"  t={r['ms']:6d} {texto(r['a'], r['b']):9s} get={r['c']:#010x} put={r['d']:#010x}")

    print("\n== Q1: quem escreve o trecho da primeira ressincronizacao")
    if not fins:
        print("  sem ressincronizacao nesta execucao")
    else:
        x = fins[0]["a"]
        if resyncs[0]["c"] - REG_LO < REG_SIZE:
            x = resyncs[0]["c"]
        blk = x & ~0xFF
        tr = resyncs[0]["ms"]
        print(f"  endereco x={x:#x}, bloco {blk:#x}, palavra na parada {fins[0]['d']:#010x}")
        print("  leituras do bloco:")
        for r in [r for r in reads if r["a"] & ~0xFF == blk][-8:]:
            print(f"    t={r['ms']:6d} volta={r['c']} io={r['a']:#x} palavra={r['b']:#010x}")
        print("  PUTs que cobrem x (ultimos 10):")
        cob = [p for p in puts if p["a"] - 0x11000000 <= x < p["a"] - 0x11000000 + p["b"]]
        for p in cob[-10:]:
            print(f"    t={p['ms']:6d} ea={p['a']:#010x} tam={p['b']:5d} job={nome_img(p['c'])} desc={p['d']:#010x} "
                  f"primeira={p['e']:#010x} ultima={p['f']:#010x} host={p['g']}")
        print("  mudancas no bloco (ultimas 10):")
        mud = [c for c in chg if c["a"] == blk]
        for c in mud[-10:]:
            print(f"    t={c['ms']:6d} io={c['b']:#x} {c['c']:#010x} -> {c['d']:#010x} palavras={c['e']} getoff={c['f']:#x}")
        lidas = [r["ms"] for r in reads if r["a"] & ~0xFF == blk and r["ms"] <= tr]
        if len(lidas) >= 1:
            ant = max([t for t in lidas if t < lidas[-1] - 250] or [0])
            janela = [c for c in mud if ant < c["ms"] <= lidas[-1]]
            pjan = [p for p in cob if ant < p["ms"] <= lidas[-1]]
            print(f"  entre a leitura anterior (t={ant}) e a ultima (t={lidas[-1]}): {len(janela)} mudancas, {len(pjan)} PUTs")
            if pjan:
                print(f"  -> ultimo escritor SPU: {nome_img(pjan[-1]['c'])} em t={pjan[-1]['ms']}")
            elif janela:
                print("  -> houve mudanca sem PUT de SPU: escritor fora do gancho")
            else:
                print("  -> ninguem escreveu entre as voltas: conteudo velho")
        print("  instantaneos da palavra em x:")
        for s, base in snaps[-10:]:
            if REG_LO <= x < REG_LO + REG_SIZE:
                print(f"    t={s[1]:6d} {'resync' if s[2] == 2 else 'saida '} get={s[3]:#x} hash={s[5]:#010x} "
                      f"[{palavra(d, base, x & ~3):08X}]")
        print("  PUTs na regiao por job (toda a execucao):")
        por = collections.Counter(nome_img(p["c"]) for p in puts
                                  if REG_LO <= p["a"] - 0x11000000 + p["b"] and p["a"] - 0x11000000 < REG_LO + REG_SIZE)
        print("   ", dict(por))

    print("\n== Q2: execucoes do job 7639")
    for r in ev:
        if r["kind"] == 9:
            print(f"  t={r['ms']:6d} fim desc={r['a']:#010x} f8={r['b']:08X}{r['c']:08X} halted={r['d']} pc={r['e']:#07x} "
                  f"stop={r['f']:#x} r0={r['g']:#x}")
        elif r["kind"] == 10:
            print(f"  t={r['ms']:6d}   PUT ea={r['a']:#010x} tam={r['b']} desc={r['c']:#010x} primeira={r['d']:#010x}")

    print("\n== Q2 e Q3: varredura de parada")
    scans = sorted(glob.glob(os.path.join(pasta, "t40_scan_*.txt")), key=os.path.getmtime)
    sem_render = None
    render_tid = next((t for t, n in tids.items() if "Render Thread" in n), None)
    if scans:
        txt = open(scans[-1], encoding="utf-8", errors="replace").read()
        print("  arquivo:", os.path.basename(scans[-1]))
        print("\n".join("  " + l for l in txt.splitlines()[:3]))
        i = txt.find("\nem espera de semaforo")
        print("\n".join("  " + l[:150] for l in txt[i:].splitlines()[:40]))
        m = re.search(rf"tid{render_tid}=sem(\d+)", txt) if render_tid is not None else None
        if m:
            sem_render = int(m.group(1))

    print(f"\n== Q3: semaforo da render (tid={render_tid}): {sem_render}")
    if sem_render is not None:
        lista = [s for s in sem if s["a"] == sem_render]
        print(f"  operacoes registradas: {len(lista)}")
        posts = collections.Counter((tnome(s["b"]), s["c"], s["d"], s["e"]) for s in lista if s["kind"] == 3)
        for (n, lr, c0, c1), q in posts.most_common(6):
            print(f"  post x{q:5d} {n:30s} lr={lr:#x} pilha={c0:#x},{c1:#x}")
        for s in lista[-12:]:
            print(f"    t={s['ms']:6d} {OPS[s['kind']]} {tnome(s['b']):30s} lr={s['c']:#x} pilha={s['d']:#x},{s['e']:#x} extra={s['f']}")

    print("\n== linha do tempo")
    t0 = (resyncs[0]["ms"] if resyncs else t_put) - 1500
    t1 = max(t_put, resyncs[-1]["ms"] if resyncs else 0) + 600
    lin = []
    for r in t40:
        if r["kind"] == 2 and t0 <= r["ms"] <= t1:
            lin.append((r["ms"], f"render: quadro contador={r['a']:#x} rotulo={r['b']:#x} put={r['f']:#x} get={r['g']:#x}"))
    for r in resyncs:
        if t0 <= r["ms"] <= t1:
            lin.append((r["ms"], f"RESSINCRONIZACAO {texto(r['a'], r['b'])} get={r['c']:#x} -> put={r['d']:#x}"))
    for r in ev:
        if r["kind"] == 8 and t0 <= r["ms"] <= t1:
            lin.append((r["ms"], f"park {r['a']:#x} preenchido {r['d']} ms depois"))
    if sem_render is not None:
        for s in sem:
            if s["a"] == sem_render and t0 <= s["ms"] <= t1:
                lin.append((s["ms"], f"sem{sem_render} {OPS[s['kind']]} {tnome(s['b'])}"))
    lin.append((t_put, "PUT PAROU DE ANDAR"))
    jan = collections.Counter(p["ms"] // 200 * 200 for p in puts if t0 <= p["ms"] <= t1)
    for m, q in jan.items():
        lin.append((m, f"[{q} PUTs de SPU no anel em 200 ms]"))
    for m, q in sorted(lin, key=lambda x: x[0]):
        print(f"  t={m:6d} {q}")


if __name__ == "__main__":
    main()
