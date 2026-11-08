"""Le a observacao da tentativa 44: comandos MFC e chamadas indiretas do job 7639.

uso: t44_read.py <dir_sonda>
"""
import collections
import sys

import t42_read as T

MFC = {0x20: "PUT", 0x40: "GET", 0x24: "PUTL", 0x44: "GETL", 0xD0: "GETLLAR", 0xB4: "PUTLLC", 0xB0: "PUTLLUC"}


def main():
    pasta = sys.argv[1]
    _, _, ev, *_ = T.le_tudo(pasta)
    corridas = []
    atual = collections.defaultdict(list)
    for r in ev:
        k = r["kind"]
        if k == 11:
            atual[r["e"]].append(r)
        elif k == 12:
            atual[r["d"]].append(r)
        elif k == 13:
            atual[r["c"]].append(r)
        elif k == 9:
            corridas.append((r, atual.pop(r["a"], [])))
        elif k == 14:
            corridas[-1][1].append(r)
        elif k == 15:
            corridas[-1][1].append(r)
    falhas = [c for c in corridas if c[0]["e"] != 0x3FF00]
    print(f"execucoes do 7639: {len(corridas)}; paradas fora do retorno: {len(falhas)}")
    origem = collections.Counter()
    for fim, lista in corridas:
        for r in lista:
            if r["kind"] == 11 and 0x5800 <= r["b"] < 0x40000 and r["a"] in (0x40, 0x44):
                origem[(MFC.get(r["a"], hex(r["a"])), r["b"], r["c"], r["d"])] += 1
    print("\n== GETs para LS 0x5800 ou acima (cmd, lsa, ea, tam, quantas)")
    for (c, l, e, s), q in sorted(origem.items(), key=lambda x: x[0][1])[:40]:
        print(f"  {c:5s} lsa={l:#07x} ea={e:#010x} tam={s:6d} x{q}")
    escolha = ([corridas[0]] if corridas else []) + falhas[-2:]
    for fim, lista in escolha:
        print(f"\n== execucao desc={fim['a']:#010x} t={fim['ms']} fim pc={fim['e']:#07x} halted={fim['d']} f8={fim['b']:08X}{fim['c']:08X}")
        for r in lista:
            k = r["kind"]
            if k == 11:
                print(f"  t={r['ms']:6d} MFC {MFC.get(r['a'], hex(r['a'])):8s} lsa={r['b']:#07x} ea={r['c']:#010x} tam={r['d']}")
            elif k == 12:
                print(f"           lista[{r['a']}] tam={r['b']:#x} ea={r['c']:#010x}")
            elif k == 13:
                g = r["g"]
                print(f"  t={r['ms']:6d} CHAMADA etapa={r['a']} ret={r['b']:#x} pc={r['d']:#07x} r0={r['e']:#x} r1={r['f']:#x} "
                      f"drain_ret={g >> 13:#x} prof={(g >> 1) & 0xFFF} trampolim={g & 1}")
            elif k == 14:
                print("  pcs finais:", " ".join(hex(r[c]) for c in "abcdefg"), end="")
            elif k == 15:
                print(f" {r['a']:#x}\n  n={r['b']} drain_ret={r['d']:#x} prof={r['e']} status={r['f']}")


if __name__ == "__main__":
    main()
