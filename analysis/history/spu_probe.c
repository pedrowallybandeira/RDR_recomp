/* spu_probe.c -- temporary diagnostic for the job 2CFF stall (attempt 31).
 *
 * Records every pass through the job's switch at LS 0x2C10 into a ring backed by
 * a mapped file, so nothing touches stdio and the data survives the monitor
 * killing the process. Off unless RDR2_PROBE_DIR is set. The first time the
 * table entry reads back zero, the whole local store is saved once for a
 * byte-for-byte comparison with the job binary.
 */
#include "spu_context.h"
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define PROBE_RECS (1u << 18)

extern uint8_t* vm_base;

typedef struct {
    uint32_t seq, tid, lr, r9, r5, r79, r4, r2;
    uint32_t q[4];
    uint32_t pc, tick, r3, pad;
} probe_rec;

typedef struct {
    uint32_t jc_ea, walks, jobs, reruns, changed, changed_rerun, last_jobs, pad;
} chain_stat;

typedef struct {
    volatile LONG total;
    uint32_t rec_size, recs, pad[13];
    probe_rec r[PROBE_RECS];
    chain_stat chains[16];
} probe_map;

/* What the walker read before dispatching, kept for the job on this thread. */
typedef struct { uint32_t jc_ea, idx, rerun, job_ea, ea_bin, size_bin; } job_note;
static __thread job_note t_job;

#define DIAG_MARK 0xC0DE0001u

static probe_map* s_map;
static volatile LONG s_state;   /* 0 unset, 1 starting, 2 on, 3 off */
static volatile LONG s_ls_saved;
static char s_dir[400];

static void probe_open(void)
{
    if (InterlockedCompareExchange(&s_state, 1, 0) != 0) return;
    const char* d = getenv("RDR2_PROBE_DIR");
    if (!d || !*d) { s_state = 3; return; }
    snprintf(s_dir, sizeof s_dir, "%s", d);
    char path[460];
    snprintf(path, sizeof path, "%s\\probe_2c10.ring", s_dir);
    HANDLE f = CreateFileA(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, NULL,
                           CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (f == INVALID_HANDLE_VALUE) { s_state = 3; return; }
    HANDLE m = CreateFileMappingA(f, NULL, PAGE_READWRITE, 0, (DWORD)sizeof(probe_map), NULL);
    probe_map* v = m ? (probe_map*)MapViewOfFile(m, FILE_MAP_ALL_ACCESS, 0, 0, 0) : NULL;
    if (!v) { s_state = 3; return; }
    v->rec_size = sizeof(probe_rec);
    v->recs = PROBE_RECS;
    s_map = v;
    s_state = 2;
}

static void probe_save_ls(const spu_context* ctx, uint32_t seq)
{
    if (InterlockedCompareExchange(&s_ls_saved, 1, 0) != 0) return;
    char path[460];
    snprintf(path, sizeof path, "%s\\probe_ls_seq%u.bin", s_dir, seq);
    HANDLE f = CreateFileA(path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (f == INVALID_HANDLE_VALUE) return;
    DWORD n = 0;
    WriteFile(f, ctx->ls, SPU_LS_SIZE, &n, NULL);
    CloseHandle(f);
    snprintf(path, sizeof path, "%s\\probe_meta_seq%u.txt", s_dir, seq);
    FILE* m = fopen(path, "w");
    if (!m) return;
    const uint8_t* d = vm_base + t_job.job_ea;
    fprintf(m, "chain=0x%08X idx=%u rerun=%u job=0x%08X ea_bin_lido=0x%08X size_lido=%u\n",
            t_job.jc_ea, t_job.idx, t_job.rerun, t_job.job_ea, t_job.ea_bin, t_job.size_bin);
    fprintf(m, "descritor agora: ea_bin=0x%02X%02X%02X%02X size=%u\n",
            d[4], d[5], d[6], d[7], (unsigned)(((d[8] << 8) | d[9]) << 4));
    fclose(m);
}

static chain_stat* chain_for(uint32_t jc_ea)
{
    if (s_state != 2) {
        if (s_state == 0) probe_open();
        if (s_state != 2) return NULL;
    }
    for (int i = 0; i < 16; i++) {
        LONG cur = InterlockedCompareExchange((volatile LONG*)&s_map->chains[i].jc_ea,
                                              (LONG)jc_ea, 0);
        if (cur == 0 || (uint32_t)cur == jc_ea) return &s_map->chains[i];
    }
    return NULL;
}

void rdr2_diag_job_begin(uint32_t jc_ea, int idx, uint32_t job_ea,
                         uint32_t ea_bin, uint32_t size_bin)
{
    chain_stat* c = chain_for(jc_ea);
    if (!c) return;
    t_job.jc_ea = jc_ea; t_job.idx = (uint32_t)idx; t_job.job_ea = job_ea;
    t_job.ea_bin = ea_bin; t_job.size_bin = size_bin;
    t_job.rerun = (uint32_t)idx < c->last_jobs;
    c->jobs++;
    c->reruns += t_job.rerun;
}

void rdr2_diag_job_end(uint32_t ea_after)
{
    chain_stat* c = chain_for(t_job.jc_ea);
    if (!c || ea_after == t_job.ea_bin) return;
    c->changed++;
    c->changed_rerun += t_job.rerun;
    const uint32_t seq = (uint32_t)InterlockedIncrement(&s_map->total) - 1u;
    probe_rec* r = &s_map->r[seq & (PROBE_RECS - 1u)];
    r->tid = GetCurrentThreadId();
    r->lr  = DIAG_MARK;
    r->r9  = t_job.idx;
    r->r5  = t_job.ea_bin;
    r->r2  = ea_after;
    r->r4  = t_job.job_ea;
    r->r79 = t_job.jc_ea;
    r->r3  = t_job.rerun;
    r->seq = seq + 1u;
}

void rdr2_diag_walk_end(uint32_t jc_ea, int jobs)
{
    chain_stat* c = chain_for(jc_ea);
    if (!c) return;
    c->walks++;
    c->last_jobs = (uint32_t)jobs;
}

void rdr2_probe_2c10(spu_context* ctx)
{
    if (s_state != 2) {
        if (s_state == 0) probe_open();
        if (s_state != 2) return;
    }
    LARGE_INTEGER t;
    QueryPerformanceCounter(&t);
    const uint32_t seq = (uint32_t)InterlockedIncrement(&s_map->total) - 1u;
    probe_rec* r = &s_map->r[seq & (PROBE_RECS - 1u)];
    r->tid = GetCurrentThreadId();
    r->lr  = ctx->gpr[0]._u32[0];
    r->r9  = ctx->gpr[9]._u32[0];
    r->r5  = ctx->gpr[5]._u32[0];
    r->r79 = ctx->gpr[79]._u32[0];
    r->r4  = ctx->gpr[4]._u32[0];
    r->r2  = ctx->gpr[2]._u32[0];
    for (int i = 0; i < 4; i++) r->q[i] = ctx->gpr[7]._u32[i];
    r->pc   = (uint32_t)ctx->pc;
    r->tick = (uint32_t)(t.QuadPart >> 10);
    r->r3   = ctx->gpr[3]._u32[0];
    r->seq  = seq + 1u;
    if (r->r2 == r->r5) probe_save_ls(ctx, seq);
}
