"""Compila os TUs SPU com flags extras e liga um executavel separado.

Le o build.ninja de work_v3 sem alterar nada ali: os objetos dos demais TUs sao
reaproveitados, e os novos ficam em <saida>/obj. Assim work_v3 e as baselines
continuam iguais.

uso: exp_build.py <saida> [--flags "-mavx2 ..."] [--troca velho=novo ...] [--mais fonte.c ...]
  --troca  objeto reaproveitado no link que deve vir de outro fonte: <sufixo do obj>=<fonte .c/.cpp>
  --mais   fonte novo, compilado com as opcoes dos jobs e acrescentado ao link
"""
import os as _os
# Raiz da arvore de trabalho privada (layout original: build_rdr2/, referencias/).
ROOT = _os.environ.get("RDR_ROOT", _os.getcwd())
import argparse
import concurrent.futures
import hashlib
import os
import re
import subprocess
import time

W = ROOT + r"\build_rdr2\work_v3"
B = _os.environ.get("RDR_BUILD", W + r"\build")
LLVM = _os.environ.get("LLVM_MINGW_BIN", "")


def arestas():
    """Devolve as arestas de compilacao e a de link do build.ninja."""
    txt = open(B + r"\build.ninja", encoding="utf-8", errors="replace").read().replace("$\n", "")
    comp, link = {}, None
    linhas = txt.split("\n")
    for i, l in enumerate(linhas):
        if not l.startswith("build "):
            continue
        m = re.match(r"build (\S+): (\S+) (.*)", l)
        if not m:
            continue
        saida, regra, resto = m.groups()
        v = {}
        for x in linhas[i + 1:]:
            mv = re.match(r"  (\w+) = (.*)", x)
            if not mv:
                break
            v[mv.group(1)] = mv.group(2)
        if regra == "CXX_EXECUTABLE_LINKER__MyGameRecomp_":
            link = (resto.split(" | ")[0].split(" || ")[0].split(), v)
        elif regra.startswith(("C_COMPILER__MyGameRecomp", "C_COMPILER__ps3recomp_runtime")):
            comp[saida] = (resto.split(" || ")[0].split(" | ")[0].split()[0].replace("$:", ":"), v)
        elif regra.startswith("CXX_COMPILER__MyGameRecomp"):
            comp[saida] = (resto.split(" || ")[0].split(" | ")[0].split()[0].replace("$:", ":"), v)
    return comp, link


def compila(job):
    cmd, obj = job
    t0 = time.time()
    r = subprocess.run(cmd, cwd=B, capture_output=True, text=True, shell=True)
    return obj, r.returncode, time.time() - t0, r.stderr[-1500:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("saida")
    ap.add_argument("--flags", default="")
    ap.add_argument("--troca", action="append", default=[])
    ap.add_argument("--mais", action="append", default=[])
    ap.add_argument("--rt", action="append", default=[],
                    help="<sufixo do obj do runtime>=<fonte>: substitui um membro de libps3recomp_runtime.a")
    ap.add_argument("--inc-first", default="",
                    help="pasta de cabecalhos buscada antes das do toolkit nos fontes SPU")
    ap.add_argument("-j", type=int, default=6)
    a = ap.parse_args()
    os.environ["PATH"] = LLVM + ";" + os.environ["PATH"]
    comp, (objs, lv) = arestas()
    alvo = {o: c for o, c in comp.items() if re.search(r"(spu_jobs/spujob_|generated_spu/spu_)[^/]+/spu_recomp\.c\.obj$", o)}
    print(f"{len(alvo)} TUs SPU, flags extras: {a.flags or '(nenhuma)'}", flush=True)
    os.makedirs(a.saida + r"\obj", exist_ok=True)
    trabalhos, troca = [], {}
    modelo = next(iter(alvo.values()))[1]
    pri = f'-I"{a.inc_first}"' if a.inc_first else ""
    for o, (fonte, v) in alvo.items():
        nome = re.search(r"(spujob_[^/]+|spu_[0-9a-f]{64})/spu_recomp", o).group(1)
        novo = fr"{a.saida}\obj\{nome}.obj"
        troca[o] = novo
        trabalhos.append((f'clang.exe {v["DEFINES"]} {pri} {v["INCLUDES"]} {v["FLAGS"]} {a.flags} -c "{fonte}" -o "{novo}"', novo))
    for t in a.troca:
        suf, fonte = t.split("=", 1)
        o = next(x for x in comp if x.endswith(suf))
        v = comp[o][1]
        cc = "clang++.exe" if fonte.endswith(".cpp") else "clang.exe"
        novo = fr"{a.saida}\obj\{os.path.basename(fonte)}.obj"
        troca[o] = novo
        extra = "" if "spu" not in suf else a.flags
        trabalhos.append((f'{cc} {v.get("DEFINES", "")} {v.get("INCLUDES", "")} {v["FLAGS"]} {extra} -c "{fonte}" -o "{novo}"', novo))
    mais = []
    for fonte in a.mais:
        novo = fr"{a.saida}\obj\{hashlib.md5(fonte.encode()).hexdigest()[:8]}_{os.path.basename(os.path.dirname(fonte))}.obj"
        mais.append(novo)
        trabalhos.append((f'clang.exe {modelo["DEFINES"]} {pri} {modelo["INCLUDES"]} {modelo["FLAGS"]} {a.flags} -c "{fonte}" -o "{novo}"', novo))
    for t in a.rt:
        suf, fonte = t.split("=", 1)
        o = next(x for x in comp if x.endswith(suf))
        v = comp[o][1]
        novo = fr"{a.saida}\obj\rt_{os.path.basename(fonte)}.obj"
        mais.append(novo)
        trabalhos.append((f'clang.exe {v.get("DEFINES", "")} {v.get("INCLUDES", "")} {v["FLAGS"]} -w -c "{fonte}" -o "{novo}"', novo))
    t0 = time.time()
    falhas = 0
    with concurrent.futures.ThreadPoolExecutor(a.j) as ex:
        for obj, rc, dt, err in ex.map(compila, trabalhos):
            if rc:
                falhas += 1
                print("FALHOU", obj, err)
    print(f"compilacao: {time.time() - t0:.0f} s, falhas {falhas}", flush=True)
    if falhas:
        raise SystemExit(1)
    lista = [troca.get(o, o) for o in objs] + mais
    rsp = a.saida + r"\link.rsp"
    with open(rsp, "w", encoding="utf-8") as f:
        f.write(" ".join('"' + x.replace("\\", "/") + '"' for x in lista) + " " + lv.get("LINK_PATH", "") + " " + lv["LINK_LIBRARIES"])
    exe = a.saida + r"\MyGameRecomp.exe"
    t0 = time.time()
    r = subprocess.run(f'clang++.exe {lv.get("FLAGS", "")} {lv.get("LINK_FLAGS", "")} @"{rsp}" -o "{exe}"',
                       cwd=B, capture_output=True, text=True, shell=True)
    print(f"link: {time.time() - t0:.0f} s, rc={r.returncode}", r.stderr[-1500:], flush=True)
    if r.returncode:
        raise SystemExit(1)
    print("exe", os.path.getsize(exe), hashlib.sha256(open(exe, "rb").read()).hexdigest())


if __name__ == "__main__":
    main()
