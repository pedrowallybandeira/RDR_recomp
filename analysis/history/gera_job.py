"""Copia experimental de overlay/spurs_job.c com menos copias de memoria por job.

O LS do job passa a ser montado direto no contexto: spu_context_init ja zera o
contexto inteiro, entao o calloc de 256 KB e a copia para ctx.ls saem. A copia do
LS para s_job_ls, depois do job, so acontece quando o jogo ja pediu o LS de uma
cadeia por sys_spu_thread_read_LS (o caso do Tokyo Jungle).
"""
import os as _os
# Raiz da arvore de trabalho privada (layout original: build_rdr2/, referencias/).
ROOT = _os.environ.get("RDR_ROOT", _os.getcwd())
O = ROOT + "/build_rdr2/work_v3/overlay/spurs_job.c"
S = ROOT + "/build_rdr2/exp_t49/jobs/spurs_job.c"


def troca(txt, velho, novo):
    if "\r\n" in txt:
        velho = velho.replace("\n", "\r\n")
        novo = novo.replace("\n", "\r\n")
    assert txt.count(velho) == 1, velho[:60]
    return txt.replace(velho, novo)


s = open(O, encoding="utf-8", newline="").read()
s = troca(s, """static int      s_job_ls_valid;
uint32_t        g_spurs_job_ls_handle;   /* set by the chain walker */

const uint8_t* spurs_job_ls_for_handle(uint32_t handle)
{
    if (!s_job_ls_valid || !handle || handle != g_spurs_job_ls_handle) return 0;
""", """static int      s_job_ls_valid;
/* Copying 256 KB after every job only pays off for a title that reads it. The
 * first lookup turns retention on; until then no job keeps its store. */
static volatile int s_job_ls_wanted;
uint32_t        g_spurs_job_ls_handle;   /* set by the chain walker */

const uint8_t* spurs_job_ls_for_handle(uint32_t handle)
{
    s_job_ls_wanted = 1;
    if (!s_job_ls_valid || !handle || handle != g_spurs_job_ls_handle) return 0;
""")
s = troca(s, """    uint8_t* ls = (uint8_t*)calloc(1, SPU_LS_SIZE);
    if (!ls) return -1;
""", """    /* The store is built in the context itself. spu_context_init clears all
     * of it, which is the zeroed LS the calloc used to provide, without the
     * calloc and the 256 KB copy into ctx.ls that followed. */
    spu_context ctx;
    spu_context_init(&ctx, 0);
    uint8_t* ls = ctx.ls;
""")
s = troca(s, """    spu_context ctx;
    spu_context_init(&ctx, 0);
    ctx.image_id = image_id;
    memcpy(ctx.ls, ls, SPU_LS_SIZE);
""", """    ctx.image_id = image_id;
""")
s = troca(s, """    memcpy(s_job_ls, ctx.ls, SPU_LS_SIZE);   /* keep the store readable */
""", """    if (s_job_ls_wanted)
        memcpy(s_job_ls, ctx.ls, SPU_LS_SIZE);   /* keep the store readable */
""")
s = troca(s, """    s_job_ls_valid = 1;
""", """    if (s_job_ls_wanted) s_job_ls_valid = 1;
""")
s = troca(s, """    free(ls);
    return 0;
""", """    return 0;
""")
# Contexto por thread, mantido entre jobs, limpando so o que o job anterior usou
# (ideia do Tourline Prologue, MIT: runtime/spu/spurs_job.c do patch deles). O
# job manager do PS3 nao zera o LS entre jobs. SPURS_JOB_FULLCLEAR=1 zera tudo.
s = troca(s, """#include "ps3emu/log_first.h"
""", """#include "ps3emu/log_first.h"
#include <stddef.h>
#include <malloc.h>
#ifdef _WIN32
#include <windows.h>
#endif
""")
s = troca(s, """int spu_run_spurs_job(spu_lifted_entry_fn entry, int image_id,
""", """/* The calling thread's job context, kept between jobs. A chain walker is a
 * thread made per Run, so the context is freed when its thread ends (FLS
 * callback); one leaked per walker would add up to gigabytes. */
static _Thread_local spu_context* t_ctx;
static _Thread_local uint32_t t_dirty;
#ifdef _WIN32
static void WINAPI job_ctx_free(void* p) { if (p) _aligned_free(p); }
#endif
static spu_context* job_ctx_get(void)
{
    if (t_ctx) return t_ctx;
    spu_context* c = (spu_context*)_aligned_malloc(sizeof(spu_context), 64);
    if (!c) return NULL;
#ifdef _WIN32
    static volatile LONG s_fls = -1;
    if (s_fls == -1) {
        DWORD k = FlsAlloc(job_ctx_free);
        if (InterlockedCompareExchange(&s_fls, (LONG)k, -1) != -1) FlsFree(k);
    }
    if (s_fls != -1) FlsSetValue((DWORD)s_fls, c);
#endif
    t_dirty = SPU_LS_SIZE;
    return t_ctx = c;
}

int spu_run_spurs_job(spu_lifted_entry_fn entry, int image_id,
""")
s = troca(s, """    spu_context ctx;
    spu_context_init(&ctx, 0);
    uint8_t* ls = ctx.ls;
""", """    static int fullclear = -1;
    if (fullclear < 0) fullclear = getenv("SPURS_JOB_FULLCLEAR") ? 1 : 0;
    spu_context* const cp = job_ctx_get();
    if (!cp) return -1;
    if (fullclear || t_dirty >= SPU_LS_SIZE - 0x1000u) {
        spu_context_init(cp, 0);
    } else {
        /* What spu_context_init clears, except the store past what the last
         * job was given: the binary's span is overwritten by the copy below,
         * and the top page holds the context and the descriptor. */
        memset(cp->gpr, 0, sizeof(cp->gpr));
        if (t_dirty > size_bin) memset(cp->ls_store + size_bin, 0, t_dirty - size_bin);
        memset(cp->ls_store + SPU_LS_SIZE - 0x1000u, 0, 0x1000u);
        memset((char*)&cp->ls, 0, sizeof(*cp) - offsetof(spu_context, ls));
        cp->ls     = cp->ls_store;
        cp->spu_id = 0;
        cp->status = SPU_STATUS_STOPPED;
    }
#define ctx (*cp)
    uint8_t* ls = ctx.ls;
""")
s = troca(s, """    ctx.image_id = image_id;
""", """    t_dirty = (p + 0x4000u < SPU_LS_SIZE) ? p + 0x4000u : SPU_LS_SIZE;
    ctx.image_id = image_id;
""")
s = troca(s, """      if (getenv("SPURS_JOB_DESCDUMP") && PS3_LOG_FIRST(_d, 4)) {
""", """      static int s_dd = -1; if (s_dd < 0) s_dd = getenv("SPURS_JOB_DESCDUMP") ? 1 : 0;
      if (s_dd && PS3_LOG_FIRST(_d, 4)) {
""")
nl = "\r\n" if "\r\n" in s else "\n"
assert s.count('    if (getenv("SPURS_JOB_DUMP")) {' + nl) == 2
s = troca(s, """    uint32_t dump_cmd = 0;
    if (getenv("SPURS_JOB_DUMP")) {
""", """    uint32_t dump_cmd = 0;
    static int s_jd = -1; if (s_jd < 0) s_jd = getenv("SPURS_JOB_DUMP") ? 1 : 0;
    if (s_jd) {
""")
s = troca(s, """    if (getenv("SPURS_JOB_DUMP")) {
""", """    if (s_jd) {
""")
s = troca(s, """    spu_coh_unregister(&ctx);   /* stack local: out of the reserver set */
    { extern void spu_mfc_release(spu_context*); spu_mfc_release(&ctx); }
    return 0;
""", """    spu_coh_unregister(&ctx);   /* out of the reserver set until the next job */
    { extern void spu_mfc_release(spu_context*); spu_mfc_release(&ctx); }
    return 0;
#undef ctx
""")
open(S, "w", encoding="utf-8", newline="").write(s)
print("gerado", len(s))
