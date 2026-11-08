"""Copias experimentais de spu_channels.c e spu_drain.c, sem tocar no toolkit.

Com SPU_INTERP_UNLIFTED, o codigo carregado em tempo de execucao passa a rodar como
uma chamada: o interpretador para no endereco de retorno, e uma funcao traduzida que
volte para dentro do modulo continua no interpretador, sem derrubar a pilha do host.
"""
import os as _os
# Raiz da arvore de trabalho privada (layout original: build_rdr2/, referencias/).
ROOT = _os.environ.get("RDR_ROOT", _os.getcwd())
import os

T = ROOT + "/referencias/ps3recomp-v0.18.0/runtime/spu"
S = ROOT + "/build_rdr2/exp_t49/interp"


def le(n):
    return open(f"{T}/{n}", encoding="utf-8", newline="").read()


def troca(txt, velho, novo):
    if "\r\n" in txt:
        velho = velho.replace("\n", "\r\n")
        novo = novo.replace("\n", "\r\n")
    assert txt.count(velho) == 1, velho[:60]
    return txt.replace(velho, novo)


c = le("spu_channels.c")
c = troca(c, """                  fprintf(stderr, "[spu] img=%d interpreting unlifted LS 0x%05X "
                          "(runtime-loaded code)\\n", ctx->image_id, p);
              spu_interp_run(ctx, p);
              return;
          } }
""", """                  fprintf(stderr, "[spu] img=%d interpreting unlifted LS 0x%05X "
                          "(runtime-loaded code)\\n", ctx->image_id, p);
              /* The module is entered by bisl, so its return is r0. Without this
               * stop the interpreter walks past it into the caller's lifted code,
               * and the C frames of that caller are never returned to. */
              const uint32_t ret = ctx->gpr[0]._u32[0] & SPU_LS_MASK;
              spu_interp_run_until(ctx, p, ret);
              if (ctx->image_id >= 0 && (ctx->status & SPU_STATUS_RUNNING) &&
                  (ctx->pc & SPU_LS_MASK) != ret && spu_lifted_lookup(ctx, ctx->pc))
                  g_spu_trampoline_fn = spu_indirect_branch;
              return;
          } }
""")
c = troca(c, """void spu_indirect_branch(spu_context* ctx)
{
    /* Real SPU bi/bisl mask the target to the 256 KB local store; the high bits
""", """/* Is the pc inside runtime-loaded code the interpreter should run? */
int spu_interp_unlifted_pc(const spu_context* ctx)
{
    static int s_on = -1;
    if (s_on < 0) s_on = getenv("SPU_INTERP_UNLIFTED") ? 1 : 0;
    const uint32_t p = ctx->pc & SPU_LS_MASK;
    if (!s_on || ctx->policy_mode || p < SPU_JM2_KERNEL_BASE || p + 3 >= SPU_LS_SIZE) return 0;
    return (ctx->ls[p] | ctx->ls[p + 1] | ctx->ls[p + 2] | ctx->ls[p + 3]) != 0;
}

void spu_indirect_branch(spu_context* ctx)
{
    /* Real SPU bi/bisl mask the target to the 256 KB local store; the high bits
""")
c = troca(c, """     * masking is a no-op for already-valid targets. */
    ctx->pc &= SPU_LS_MASK;
""", """     * masking is a no-op for already-valid targets. */
    ctx->pc &= SPU_LS_MASK;
    /* Diagnostico: SPU_MP3_STUB=<r3>. O decodificador MP3 do Multistream fica em
     * LS 0x1A100 e vem de flashMP3.pic, ausente aqui. Retorna direto com esse r3
     * para separar "o audio trava a carga" de outras causas. */
    { static long s_stub = -2;
      if (s_stub == -2) { const char* e = getenv("SPU_MP3_STUB"); s_stub = e ? atol(e) : -3; }
      if (s_stub != -3 && ctx->pc == 0x1A100u && !ctx->ls[0x1A100] && !ctx->ls[0x1A101]) {
          static int _n = 0;
          if (PS3_LOG_FIRST(_n, 12))
              fprintf(stderr, "[mp3-stub] img=%d r0=0x%05X r3=0x%08X r4=0x%05X r5=0x%05X r7=0x%08X r8=0x%08X -> %ld\\n",
                      ctx->image_id, ctx->gpr[0]._u32[0] & SPU_LS_MASK, ctx->gpr[3]._u32[0], ctx->gpr[4]._u32[0],
                      ctx->gpr[5]._u32[0], ctx->gpr[7]._u32[0], ctx->gpr[8]._u32[0], s_stub);
          memset(&ctx->gpr[3], 0, sizeof ctx->gpr[3]);
          ctx->gpr[3]._u32[0] = (uint32_t)s_stub;
          ctx->pc = ctx->gpr[0]._u32[0] & SPU_LS_MASK;
          return;
      } }
""")
c = troca(c, """    spu_ovl_dump(ctx, ea, lsa, ls, size);
""", """    spu_ovl_dump(ctx, ea, lsa, ls, size);
    { extern void spu_ovl_dump_all(spu_context*, uint32_t, uint32_t, const uint8_t*, uint32_t);
      spu_ovl_dump_all(ctx, ea, lsa, ls, size); }
""")
c = troca(c, """void spu_overlay_note_get(spu_context* ctx, uint32_t ea, const uint8_t* ls, uint32_t size)
{""", """/* Experimento: SPU_DUMP_OVL_ALL=<dir>,<lsa> grava cada par distinto (EA, conteudo)
 * de um GET de pelo menos 4 KB para <lsa>. SPU_DUMP_OVL guarda so o primeiro
 * conteudo de cada EA, que para um slot ainda vazio sai zerado. */
void spu_ovl_dump_all(spu_context* ctx, uint32_t ea, uint32_t lsa, const uint8_t* ls, uint32_t size)
{
    static int s_on = -1; static char s_dir[400]; static uint32_t s_lsa;
    if (s_on < 0) { const char* e = getenv("SPU_DUMP_OVL_ALL"); s_on = e && *e;
        if (s_on) { snprintf(s_dir, sizeof s_dir, "%s", e);
                    char* c = strchr(s_dir, ','); if (c) { *c = 0; s_lsa = (uint32_t)strtoul(c + 1, 0, 0); } } }
    if (!s_on || lsa != s_lsa || size < 4096) return;
    uint64_t h = 1469598103934665603ULL; int nz = 0;
    for (uint32_t i = 0; i < size; i++) { h ^= ls[i]; h *= 1099511628211ULL; nz |= ls[i]; }
    if (!nz) return;
    static uint64_t s_seen[256]; static unsigned s_n; static SRWLOCK s_lk = SRWLOCK_INIT;
    AcquireSRWLockExclusive(&s_lk);
    for (unsigned i = 0; i < s_n; i++) if (s_seen[i] == (h ^ ea)) { ReleaseSRWLockExclusive(&s_lk); return; }
    if (s_n < 256) s_seen[s_n++] = h ^ ea;
    ReleaseSRWLockExclusive(&s_lk);
    char path[512];
    snprintf(path, sizeof path, "%s/ovl_%08X_%016llX.bin", s_dir, ea, (unsigned long long)h);
    FILE* f = fopen(path, "wb");
    if (f) { fwrite(ls, 1, size, f); fclose(f); }
    fprintf(stderr, "[spu-ovl-all] img=%d ea=0x%08X lsa=0x%05X size=%u hash=%016llX\\n",
            ctx->image_id, ea, lsa, size, (unsigned long long)h);
}

void spu_overlay_note_get(spu_context* ctx, uint32_t ea, const uint8_t* ls, uint32_t size)
{""")
d = le("spu_drain.c")
d = troca(d, """        {
            extern void spu_restart_dispatch(spu_context*);
            SPU_DRAIN_POP_IRQ();
            spu_restart_dispatch(ctx);
            return;
        }
""", """        /* A lifted helper returned into a runtime-loaded module. There is no
         * lifted entry there, and restarting dispatch would drop the C frames of
         * the code that called the module: finish the module here instead. */
        {
            extern int spu_interp_unlifted_pc(const spu_context*);
            extern uint32_t spu_interp_run_until(spu_context*, uint32_t, uint32_t);
            extern void (*spu_lifted_lookup(const spu_context*, uint32_t))(spu_context*);
            const uint32_t ret = return_pc & SPU_LS_MASK;
            if (spu_interp_unlifted_pc(ctx)) {
                ctx->drain_ret_pc = ret;
                spu_interp_run_until(ctx, ctx->pc & SPU_LS_MASK, ret);
                if (ctx->status & SPU_STATUS_RUNNING) {
                    if ((ctx->pc & SPU_LS_MASK) != ret && spu_lifted_lookup(ctx, ctx->pc))
                        *tramp = spu_indirect_branch;
                    continue;
                }
            }
        }
        {
            extern void spu_restart_dispatch(spu_context*);
            SPU_DRAIN_POP_IRQ();
            spu_restart_dispatch(ctx);
            return;
        }
""")
# A tabela de 64 enche no boot, com alvos pequenos, e os alvos do mundo sao descartados.
r = open(ROOT + "/referencias/ps3recomp-v0.18.0/libs/video/rsx_live_draw.c",
         encoding="utf-8", newline="").read()
assert r.count("#define MAX_SURFACES     64") == 1
r = r.replace("#define MAX_SURFACES     64", "#define MAX_SURFACES     512")
os.makedirs(S, exist_ok=True)
open(f"{S}/rsx_live_draw.c", "w", encoding="utf-8", newline="").write(r)
open(f"{S}/spu_channels.c", "w", encoding="utf-8", newline="").write(c)
open(f"{S}/spu_drain.c", "w", encoding="utf-8", newline="").write(d)
print("gerado", len(c), len(d))
