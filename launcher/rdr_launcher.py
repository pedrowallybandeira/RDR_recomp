"""Lancador do port: confere a instalacao e roda o jogo SEMPRE por scripts/boot_seguro.ps1.

So biblioteca padrao (tkinter). Nao contem nada do jogo. As configuracoes ficam em
launcher/settings.json (ignorado pelo git) e cada sessao grava em local/boots.

Port launcher: checks the setup and always runs the game through
scripts/boot_seguro.ps1 (resource limits + watchdog). Standard library only.

uso: python launcher/rdr_launcher.py        (ou scripts\\launch.ps1)
"""
import json
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS = os.path.join(REPO, "launcher", "settings.json")
BOOT = os.path.join(REPO, "scripts", "boot_seguro.ps1")
# START, X (Normal), X (sem save), quadrado (autosave desligado), X: chega a cena 3D.
PAD_ATE_A_CENA = "24:0x0008,44:0x4000,64:0x4000,84:0x8000,104:0x4000"

PADRAO = {
    "local": os.path.join(REPO, "local"),
    "exe": "",          # vazio = <local>/build/MyGameRecomp.exe
    "elf": "",          # vazio = <local>/game/RDR2.elf
    "vfs": "",          # vazio = <local>/vfs
    "dev_flash": "",    # vazio = <local>/dev_flash
    "segundos": 1800,
    "visivel": True,
    "pad_script": False,
    "verbose": False,
    "extra_env": "",    # linhas NOME=valor, aplicadas por ultimo
}


def carrega():
    s = dict(PADRAO)
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            s.update({k: v for k, v in json.load(f).items() if k in PADRAO})
    except (OSError, ValueError):
        pass
    return s


def salva(s):
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=1)


def caminhos(s):
    loc = s["local"]
    return {
        "exe": s["exe"] or os.path.join(loc, "build", "MyGameRecomp.exe"),
        "elf": s["elf"] or os.path.join(loc, "game", "RDR2.elf"),
        "vfs": s["vfs"] or os.path.join(loc, "vfs"),
        "dev_flash": s["dev_flash"] or os.path.join(loc, "dev_flash"),
        "boots": os.path.join(loc, "boots"),
        "overlay": os.path.join(loc, "overlay"),
    }


def confere(s):
    """Lista de (ok, mensagem). Nunca executa o jogo."""
    c = caminhos(s)
    r = []

    def item(ok, msg):
        r.append((bool(ok), msg))

    item(os.path.isfile(c["exe"]), "executavel: " + c["exe"])
    item(os.path.isfile(c["elf"]), "ELF decriptado (seu): " + c["elf"])
    sfo = os.path.join(c["vfs"], "PS3_GAME", "PARAM.SFO")
    item(os.path.isfile(sfo), "PARAM.SFO no VFS: " + sfo)
    usr = os.path.join(c["vfs"], "game", "BLUS30418", "USRDIR")
    item(os.path.isdir(usr), "dados do jogo: " + usr)
    if os.path.isdir(usr):
        rpf = [n for n in os.listdir(usr) if n.lower().endswith(".rpf")]
        item(rpf, f"{len(rpf)} arquivo(s) .rpf em USRDIR")
        item(os.path.isdir(os.path.join(usr, "dlcPack")), "pacotes de DLC em USRDIR/dlcPack (o menu exige)")
    item(os.path.isfile(os.path.join(c["overlay"], "cellSpurs.c")), "overlay do toolkit (scripts/prepare_overlay.ps1)")
    mp3 = os.path.join(c["dev_flash"], "sys", "external", "flashMP3.pic")
    r.append((True, ("ok" if os.path.isfile(mp3) else "ausente (opcional, sem ele o MP3 nao decodifica)") + ": " + mp3))
    item(os.path.isfile(BOOT), "scripts/boot_seguro.ps1")
    return r


def ambiente(s, base=None):
    """Variaveis passadas ao boot_seguro.ps1."""
    c = caminhos(s)
    env = dict(os.environ if base is None else base)
    env["RDR_ROOT"] = s["local"]
    env["RDR_ELF"] = c["elf"]
    env["RDR_VFS"] = c["vfs"]
    env["RDR_DEV_FLASH"] = c["dev_flash"]
    env["RDR_BOOTS"] = c["boots"]
    env["RDR_BUILD"] = os.path.dirname(c["exe"])
    env["PS3_VERBOSE"] = "1" if s["verbose"] else "0"
    if s["pad_script"]:
        env["PAD_SCRIPT"] = PAD_ATE_A_CENA
    else:
        env.pop("PAD_SCRIPT", None)
    for linha in s["extra_env"].splitlines():
        if "=" in linha and not linha.lstrip().startswith("#"):
            k, v = linha.split("=", 1)
            if k.strip():
                env[k.strip()] = v.strip()
    return env


def comando(s, tag):
    c = caminhos(s)
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", BOOT,
           "-Tag", tag, "-Segundos", str(int(s["segundos"])), "-Exe", c["exe"]]
    if s["visivel"]:
        cmd.append("-Visivel")
    return cmd


def main():
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext

    s = carrega()
    proc = {"p": None, "tag": ""}
    raiz = tk.Tk()
    raiz.title("RDR Recompiled — launcher")

    campos = {}
    for i, (k, rot) in enumerate([("local", "Pasta local"), ("exe", "Executavel"), ("elf", "RDR2.elf"),
                                  ("vfs", "VFS"), ("dev_flash", "dev_flash")]):
        tk.Label(raiz, text=rot).grid(row=i, column=0, sticky="w", padx=4)
        v = tk.StringVar(value=s[k])
        tk.Entry(raiz, textvariable=v, width=70).grid(row=i, column=1, padx=4, pady=1)

        def escolhe(v=v, k=k):
            p = filedialog.askopenfilename() if k in ("exe", "elf") else filedialog.askdirectory()
            if p:
                v.set(p)
        tk.Button(raiz, text="...", command=escolhe).grid(row=i, column=2)
        campos[k] = v

    linha = 5
    seg = tk.IntVar(value=s["segundos"])
    tk.Label(raiz, text="Limite (s)").grid(row=linha, column=0, sticky="w", padx=4)
    tk.Spinbox(raiz, from_=60, to=7200, increment=60, textvariable=seg, width=8).grid(row=linha, column=1, sticky="w")
    opc = {k: tk.BooleanVar(value=s[k]) for k in ("visivel", "pad_script", "verbose")}
    f = tk.Frame(raiz)
    f.grid(row=linha + 1, column=0, columnspan=3, sticky="w", padx=4)
    tk.Checkbutton(f, text="janela visivel", variable=opc["visivel"]).pack(side="left")
    tk.Checkbutton(f, text="PAD_SCRIPT ate a cena", variable=opc["pad_script"]).pack(side="left")
    tk.Checkbutton(f, text="log detalhado (lento!)", variable=opc["verbose"]).pack(side="left")
    tk.Label(raiz, text="Variaveis extras (NOME=valor)").grid(row=linha + 2, column=0, columnspan=3, sticky="w", padx=4)
    extra = tk.Text(raiz, height=3, width=80)
    extra.insert("1.0", s["extra_env"])
    extra.grid(row=linha + 3, column=0, columnspan=3, padx=4)
    saida = scrolledtext.ScrolledText(raiz, height=12, width=90)
    saida.grid(row=linha + 5, column=0, columnspan=3, padx=4, pady=4)

    def atual():
        for k, v in campos.items():
            s[k] = v.get().strip()
        s["segundos"] = int(seg.get())
        for k, v in opc.items():
            s[k] = bool(v.get())
        s["extra_env"] = extra.get("1.0", "end").strip()
        salva(s)
        return s

    def escreve(t):
        saida.insert("end", t + "\n")
        saida.see("end")

    def conferir():
        for ok, msg in confere(atual()):
            escreve(("OK    " if ok else "FALTA ") + msg)

    def jogar():
        if proc["p"] and proc["p"].poll() is None:
            messagebox.showinfo("RDR", "Ja ha uma sessao rodando.")
            return
        faltas = [m for ok, m in confere(atual()) if not ok]
        if faltas:
            messagebox.showerror("RDR", "Instalacao incompleta:\n" + "\n".join(faltas))
            return
        tag = time.strftime("jogar_%Y%m%d_%H%M%S")
        os.makedirs(caminhos(s)["boots"], exist_ok=True)
        log = open(os.path.join(caminhos(s)["boots"], tag + ".launcher.log"), "w", encoding="utf-8")
        proc["p"] = subprocess.Popen(comando(s, tag), env=ambiente(s), stdout=log, stderr=subprocess.STDOUT,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        proc["tag"] = tag
        escreve(f"iniciado {tag} (boot_seguro.ps1, limite {s['segundos']} s); logs em {caminhos(s)['boots']}")

    def parar():
        p = proc["p"]
        if not p or p.poll() is not None:
            escreve("nenhuma sessao deste launcher rodando")
            return
        # /T derruba a arvore iniciada por este launcher: boot_seguro, o jogo e o vigia.
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        escreve(f"sessao {proc['tag']} encerrada")

    def logs():
        d = caminhos(atual())["boots"]
        os.makedirs(d, exist_ok=True)
        os.startfile(d)  # noqa: S606 -- abre a pasta no Explorer

    b = tk.Frame(raiz)
    b.grid(row=linha + 4, column=0, columnspan=3, pady=4)
    for t, fn in (("Conferir instalacao", conferir), ("Jogar", jogar), ("Parar", parar), ("Abrir logs", logs)):
        tk.Button(b, text=t, command=fn, width=18).pack(side="left", padx=3)
    raiz.mainloop()


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("so Windows")
    main()
