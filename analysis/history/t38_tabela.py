"""Resume descritores.txt da tentativa 38.

uso: t38_tabela.py <dir>
"""
import os
import re
import sys

REGISTRO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "spu_jobs", "jobs_register.c")
IMG = {int(i): n for i, n in re.findall(r"spu_begin_image\((\d+)\); spujob_([0-9A-F]{4})",
                                        open(REGISTRO, encoding="utf-8").read())}
PADRAO = re.compile(r"img=(\d+) n=(\d+) job=(\w+) io=(\d+) in=(\w+) out=(\w+) dma=(\d+) cache=(\d+) "
                    r"obuf=(\w+) iobuf=(\w+) sbuf=(\w+) cont_sem_obuf=(\w+) cont_com_obuf=(\w+) "
                    r"tot\[inout=(\d+) out0=(\d+) ambos=(\d+)\]")


def main():
    linhas = open(os.path.join(sys.argv[1], "descritores.txt")).read().splitlines()
    pri, ult = {}, {}
    for l in linhas:
        m = PADRAO.match(l)
        if m:
            g = m.groups()
            k = int(g[0])
            pri.setdefault(k, g)
            ult[k] = g
    print("job  regist. io    in   out dma cache  obuf  cont_sem cont_com  inout  out0 ambos")
    for k, g in sorted(pri.items(), key=lambda x: IMG.get(x[0], "?")):
        u = ult[k]
        print(f"{IMG.get(k, '?'):4s} {u[1]:>6s}  {g[3]} {g[4]:>6s} {g[5]:>5s} {g[6]:>3s} {g[7]:>4s}  {g[8]:>5s} "
              f"{g[11]:>8s} {g[12]:>8s} {u[13]:>6s} {u[14]:>5s} {u[15]:>5s}")
    for nome in ("03B3", "B25C", "A672"):
        ids = [k for k, v in IMG.items() if v == nome]
        print(f"\n== {nome}")
        vistos = 0
        for i, l in enumerate(linhas):
            m = PADRAO.match(l)
            if m and int(m.group(1)) in ids and int(m.group(2)) <= 2:
                print(l[:150])
                j = i + 1
                while j < len(linhas) and linhas[j].startswith(" "):
                    print(linhas[j][:150])
                    j += 1
                vistos += 1
                if vistos == 2:
                    break


if __name__ == "__main__":
    main()
