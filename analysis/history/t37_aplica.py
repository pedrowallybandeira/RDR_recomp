"""Aplica a instrumentacao passiva da tentativa 37 nos jobs 03B3 e C895.

Roda sobre os spu_recomp.c gerados; lift_jobs.py os devolve ao estado original.
uso: t37_aplica.py <dir_spu_jobs>
"""
import os
import sys

DECL = ("extern void rdr2_t37_hit(spu_context*, int, uint32_t, uint32_t, uint32_t, uint32_t);\n"
        "extern void rdr2_t37_count(int);\n"
        "extern uint32_t rdr2_t37_ls32(const spu_context*, uint32_t);\n\n")


def g(n):
    return f"ctx->gpr[{n}]._u32[0]"


def troca(t, velho, novo, nome):
    if t.count(velho) != 1:
        sys.exit(f"{nome}: {t.count(velho)} ocorrencias")
    return t.replace(velho, novo)


def declara(t, prefixo):
    i = t.find(f"\nvoid {prefixo}spu_func_")
    if i < 0:
        sys.exit("primeira funcao nao encontrada")
    return t[:i + 1] + DECL + t[i + 1:]


def aplica_03b3(p):
    x = "spujob_03B3F699089214AD_12944_"
    t = open(p, encoding="utf-8").read()
    t = declara(t, x)
    # Laco de segmentos: indice, limite, estruturas.
    v = f"        if (ctx->gpr[49]._u32[0] == 0) {{ SPU_DIRECT(ctx, 0x2320, {x}spu_func_00002320); }}\n"
    t = troca(t, v, f"        rdr2_t37_hit(ctx, 1, {g(83)}, {g(2)}, {g(81)}, {g(85)});\n" + v, "21C8")
    # Rotina chamada por ponteiro, a que aparece nas amostras.
    v = f"void {x}spu_func_000000D0(spu_context* ctx) {{\n"
    t = troca(t, v, v + "        rdr2_t37_count(2);\n", "D0")
    # Comparacao do anel: livre, inicio, fim pedido, fim do anel.
    v = ("        ctx->gpr[2] = spu_ls_read128(ctx, 0x3210);\n"
         "        ctx->gpr[4] = spu_rotqbyi(ctx->gpr[2], 8);\n")
    t = troca(t, v, v + f"        rdr2_t37_hit(ctx, 3, {g(4)}, {g(83)}, {g(15)}, {g(86)});\n", "BC0")
    # GET de 4 bytes: endereco consultado e valor lido.
    v = "        ctx->gpr[74] = spu_rotqby(ctx->gpr[76], ctx->gpr[6]);\n"
    t = troca(t, v, v + f"        rdr2_t37_hit(ctx, 4, {g(11)}, {g(74)}, {g(10)}, {g(15)});\n", "CE0")
    # Atraso entre consultas.
    v = f"void {x}spu_func_00000D68(spu_context* ctx) {{\n"
    t = troca(t, v, v + "        rdr2_t37_count(5);\n", "D68")
    # Pedido de espaco no anel.
    v = f"void {x}spu_func_00000D80(spu_context* ctx) {{\n"
    t = troca(t, v, v + f"        rdr2_t37_hit(ctx, 6, {g(3)}, {g(4)}, {g(5)}, {g(6)});\n", "D80")
    # GET da lista: EA, valor usado como contagem, destino em LS, tamanho.
    v = ("        spu_wrch(ctx, MFC_Size, ctx->gpr[31]);\n"
         "        spu_wrch(ctx, MFC_TagID, ctx->gpr[30]);\n"
         "        spu_wrch(ctx, MFC_Cmd, ctx->gpr[29]);\n")
    t = troca(t, v, f"        rdr2_t37_hit(ctx, 11, {g(38)}, {g(36)}, {g(39)}, {g(31)});\n" + v, "2010")
    # Alvo da chamada por ponteiro dentro do laco.
    v = "        ctx->gpr[33] = spu_rotqby(ctx->gpr[34], ctx->gpr[35]);\n"
    t = troca(t, v, v + f"        rdr2_t37_hit(ctx, 8, {g(33)}, {g(85)}, {g(90)}, (uint32_t)ctx->host_depth);\n", "2288")
    # Entrada da rotina principal; host_depth > 0 significa reentrada.
    v = f"void {x}spu_func_00002898(spu_context* ctx) {{\n"
    t = troca(t, v, v + f"        rdr2_t37_hit(ctx, 9, {g(3)}, {g(4)}, {g(1)}, {g(0)});\n", "2898")
    # Reserva GCM sem espaco: begin, end, current, palavras pedidas.
    for fn in ("00001C00", "00001C38"):
        v = f"void {x}spu_func_{fn}(spu_context* ctx) {{\n"
        ls = lambda o: f"rdr2_t37_ls32(ctx, {g(83)} + {o}u)"
        t = troca(t, v, v + f"        rdr2_t37_hit(ctx, 10, {ls(0)}, {ls(4)}, {ls(8)}, {ls(12)});\n", fn)
    open(p, "w", encoding="utf-8", newline="\n").write(t)


def aplica_c895(p):
    x = "spujob_C895B508A51CD2A6_79376_"
    t = open(p, encoding="utf-8").read()
    t = declara(t, x)
    # Retorno da rotina consultada: EA, codigo, mascara em LS.
    v = ("spu_drain_call(ctx, 0x5264); ctx->host_depth--; spu_img_restore(ctx, _si); }\n")
    t = troca(t, v, v + f"        rdr2_t37_hit(ctx, 7, rdr2_t37_ls32(ctx, {g(80)} + 0x40u), {g(3)}, "
                        f"rdr2_t37_ls32(ctx, {g(1)} + 32u), {g(80)});\n", "5264")
    open(p, "w", encoding="utf-8", newline="\n").write(t)


def main():
    base = sys.argv[1]
    aplica_03b3(os.path.join(base, "spujob_03B3F699089214AD_12944", "spu_recomp.c"))
    aplica_c895(os.path.join(base, "spujob_C895B508A51CD2A6_79376", "spu_recomp.c"))
    print("ok")


if __name__ == "__main__":
    main()
