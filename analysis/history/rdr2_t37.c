/* rdr2_t37.c -- temporary, passive observation for attempts 37 and 40.
 *
 * Off unless RDR2_T37_DIR is set. Everything goes to rings in a mapped file, so
 * nothing touches stdio and the data survives the monitor killing the process.
 * Guest memory is only ever read. Removed once the attempt is written up.
 */
#include "spu_context.h"
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

extern uint8_t* vm_base;
extern unsigned cellGcm_flip_request_count(void);
extern unsigned ppu_boot_frames_presented(void);
extern uint32_t gcm_io_offset_to_ea(uint32_t io);
void rdr2_t37_gcm_state(uint32_t* put, uint32_t* get, uint32_t* getoff);

#define RING_RSX  (1u << 17)
#define RING_POLL (1u << 17)
#define RING_SAMP (1u << 15)
#define RING_EV   (1u << 13)
#define N_POINT   16
#define N_IMG     32
#define N_WATCH   8
#define LABEL_BASE 0x20000000u
#define JOB_RETURN 0x3FF00u

/* Attempt 40: the render thread's wait at 0x59B364 on the label 0x90FC50 emits. */
#define RING_T40   (1u << 15)
#define POLL_LR    0x0059B36Cu
#define ADDR_COUNT 0x013DB340u
#define ADDR_IDX   0x016D4EDFu
#define TLS_CTX    0x6E84u
#define IO_SPAN    0x00300000u
#define SCAN_MAX   8
#define N_PARK     16

/* Attempt 42: who touches the start of the ring, and what the render waits on. */
#define RING_PUT   (1u << 17)
#define RING_READ  (1u << 15)
#define RING_CHG   (1u << 16)
#define RING_SEM   (1u << 17)
#define N_SNAP     32
#define N_JOBTAB   8192
#define RING_EA    0x11000000u
#define RING_LEN   0x00300000u
#define REG_LO     0x5000u
#define REG_SIZE   0xD000u
#define TEXT_END   0x01108000u
#define ADDR_WAITN 0x017777E0u
#define ADDR_WAITL 0x017777C0u
#define ADDR_TASKS 0x0168F700u
#define ADDR_FREE  0x0168BA00u
#define IMG_7639   338893180u
#define REPORT_EA  0x10100000u

typedef struct { uint32_t seq, ms, why, get, put, hash, pad[2]; } snap_hdr;
typedef struct { uint32_t ea, img, begins, ends, t_begin, t_end, f8_hi, f8_lo; } job_rec;
void rdr2_t40_gcm_ctx(uint32_t* out_ea, uint32_t* ours);

typedef struct { uint32_t seq, ms, kind, a, b, c, d, e, f, g; } rec;

typedef struct {
    uint32_t image, started, jobs, normal, abnormal, trap, last_pc, last_job;
} img_stat;

typedef struct {
    uint32_t rec_size, cap_rsx, cap_poll, cap_samp, cap_ev, n_img, n_point, pad;
    volatile LONG n_rsx, n_poll, n_samp, n_ev;
    volatile LONG64 point[N_POINT];
    img_stat img[N_IMG];
    rec rsx[RING_RSX];
    rec poll[RING_POLL];
    rec samp[RING_SAMP];
    rec ev[RING_EV];
    volatile LONG n_t40;
    uint32_t cap_t40, pad2[2];
    rec t40[RING_T40];
    volatile LONG n_put, n_read, n_chg, n_sem;
    uint32_t cap_put, cap_read, cap_chg, cap_sem, n_snap, snap_size, n_jobtab, pad3;
    rec put42[RING_PUT];
    rec read42[RING_READ];
    rec chg[RING_CHG];
    rec sem[RING_SEM];
    snap_hdr snap_h[N_SNAP];
    uint8_t snap[N_SNAP][REG_SIZE];
    job_rec jobs[N_JOBTAB];
} t37_map;

typedef struct {
    DWORD cb, PageFaultCount;
    SIZE_T PeakWorkingSetSize, WorkingSetSize, QuotaPeakPagedPoolUsage, QuotaPagedPoolUsage,
           QuotaPeakNonPagedPoolUsage, QuotaNonPagedPoolUsage, PagefileUsage, PeakPagefileUsage,
           PrivateUsage;
} mem_counters;
typedef BOOL (WINAPI *mem_fn)(HANDLE, mem_counters*, DWORD);

static t37_map* s_map;
static volatile LONG s_state;   /* 0 unset, 1 starting, 2 on, 3 off */
static LARGE_INTEGER s_t0, s_freq;
static volatile LONG s_nw;
static uint32_t s_watch[N_WATCH];
static uint32_t s_seen[N_WATCH][4];
static int s_seen_ok[N_WATCH];
static char s_dir[400];

/* Every Nth pass of a probe point is kept; a change in `a` or `b` is kept too. */
static const uint32_t s_every[N_POINT] = { 1, 4096, 1, 1024, 256, 1, 1, 256, 4096, 1, 1, 1, 1, 1, 1, 1 };
static uint32_t s_last[N_POINT][2];

static uint32_t now_ms(void)
{
    LARGE_INTEGER t;
    QueryPerformanceCounter(&t);
    return (uint32_t)((t.QuadPart - s_t0.QuadPart) * 1000 / s_freq.QuadPart);
}

static void put(rec* ring, uint32_t cap, volatile LONG* n, uint32_t kind, uint32_t a, uint32_t b,
                uint32_t c, uint32_t d, uint32_t e, uint32_t f, uint32_t g)
{
    const uint32_t seq = (uint32_t)InterlockedIncrement(n) - 1u;
    rec* r = &ring[seq & (cap - 1u)];
    r->ms = now_ms(); r->kind = kind;
    r->a = a; r->b = b; r->c = c; r->d = d; r->e = e; r->f = f; r->g = g;
    r->seq = seq + 1u;
}

static uint32_t be32(uint32_t ea)
{
    return _byteswap_ulong(*(const uint32_t*)(vm_base + ea));
}

static int readable(uint32_t ea)
{
    MEMORY_BASIC_INFORMATION mi;
    if (!VirtualQuery(vm_base + ea, &mi, sizeof mi)) return 0;
    return mi.State == MEM_COMMIT && !(mi.Protect & (PAGE_NOACCESS | PAGE_GUARD));
}

static void watch_add(uint32_t ea)
{
    if (!ea || !readable(ea & ~15u)) return;
    ea &= ~15u;
    for (LONG i = 0; i < s_nw; i++) if (s_watch[i] == ea) return;
    const LONG i = InterlockedIncrement(&s_nw) - 1;
    if (i < N_WATCH) s_watch[i] = ea;
    else InterlockedDecrement(&s_nw);
}

/* Render-thread r13 and the current wait: a wait lasts as long as the counter
 * holds one value. */
static volatile uint32_t s_r13, s_poll_ms, s_ep_ms, s_ep_count;
static volatile LONG s_ep_seq;

/* Parks a jump-park resync gave up on: does the word still change afterwards? */
static struct { volatile uint32_t ea; uint32_t io, word, ms; } s_park[N_PARK];
static volatile LONG s_n_park;

static void watch_parks(void)
{
    for (int i = 0; i < N_PARK; i++) {
        const uint32_t ea = s_park[i].ea;
        if (!ea) continue;
        const uint32_t w = be32(ea);
        if (w == s_park[i].word) continue;
        put(s_map->ev, RING_EV, &s_map->n_ev, 8, s_park[i].io, s_park[i].word, w,
            now_ms() - s_park[i].ms, 0, 0, 0);
        s_park[i].ea = 0;
    }
}

/* counter, label, label index, render context, its current, put, walker get */
static void wait_state(uint32_t* v)
{
    uint32_t pt = 0, gt = 0, gf = 0;
    const uint32_t r13 = s_r13;
    const uint32_t ctx = r13 ? be32(r13 - TLS_CTX) : 0;
    rdr2_t37_gcm_state(&pt, &gt, &gf);
    v[2] = vm_base[ADDR_IDX];
    v[0] = be32(ADDR_COUNT);
    v[1] = be32(LABEL_BASE + v[2] * 0x10u);
    v[3] = ctx;
    v[4] = ctx && readable(ctx) ? be32(ctx + 8u) : 0;
    v[5] = pt;
    v[6] = gf;
}

/* Attempt 42 state. */
static _Thread_local int t_img;
static _Thread_local uint32_t t_job;
static volatile uint32_t s_inwait[256];
static volatile LONG s_snap_n;

static job_rec* job_slot(uint32_t ea, int make)
{
    uint32_t i = ((ea >> 4) * 2654435761u) >> 19;
    for (int k = 0; k < 64; k++, i = (i + 1u) & (N_JOBTAB - 1u)) {
        job_rec* r = &s_map->jobs[i];
        if (r->ea == ea) return r;
        if (r->ea) continue;
        if (!make) return NULL;
        if (InterlockedCompareExchange((volatile LONG*)&r->ea, (LONG)ea, 0) == 0 || r->ea == ea) return r;
    }
    return NULL;
}

static void snap_take(uint32_t why)
{
    uint32_t pt = 0, gt = 0, gf = 0, h = 2166136261u;
    const LONG i = InterlockedIncrement(&s_snap_n) - 1;
    uint8_t* d = s_map->snap[i % N_SNAP];
    memcpy(d, vm_base + RING_EA + REG_LO, REG_SIZE);
    for (uint32_t k = 0; k < REG_SIZE; k++) h = (h ^ d[k]) * 16777619u;
    rdr2_t37_gcm_state(&pt, &gt, &gf);
    snap_hdr* s = &s_map->snap_h[i % N_SNAP];
    s->ms = now_ms(); s->why = why; s->get = gf; s->put = pt; s->hash = h;
    s->seq = (uint32_t)i + 1u;
}

/* Every millisecond: which 256-byte blocks of the watched region changed, whoever
 * wrote them. Host writes the store watch cannot see land here too. */
static DWORD WINAPI watcher(LPVOID p)
{
    static uint8_t prev[REG_SIZE], cur[REG_SIZE];
    const uint32_t base = RING_EA + REG_LO;
    (void)p;
    while (!readable(base) || !readable(base + REG_SIZE - 4u)) Sleep(5);
    memcpy(prev, vm_base + base, REG_SIZE);
    int inside = 0;
    for (;;) {
        uint32_t pt = 0, gt = 0, gf = 0;
        memcpy(cur, vm_base + base, REG_SIZE);
        rdr2_t37_gcm_state(&pt, &gt, &gf);
        if (memcmp(cur, prev, REG_SIZE)) {
            for (uint32_t b = 0; b < REG_SIZE; b += 0x100u) {
                if (!memcmp(cur + b, prev + b, 0x100u)) continue;
                uint32_t first = 0xFFFFFFFFu, n = 0;
                for (uint32_t o = 0; o < 0x100u; o += 4u) {
                    if (memcmp(cur + b + o, prev + b + o, 4u)) { if (first == 0xFFFFFFFFu) first = o; n++; }
                }
                uint32_t a = 0, c = 0;
                if (first != 0xFFFFFFFFu) {
                    a = _byteswap_ulong(*(const uint32_t*)(prev + b + first));
                    c = _byteswap_ulong(*(const uint32_t*)(cur + b + first));
                    first += b;
                }
                put(s_map->chg, RING_CHG, &s_map->n_chg, 1, REG_LO + b, REG_LO + first, a, c, n, gf, pt);
            }
            memcpy(prev, cur, REG_SIZE);
        }
        const int in = gf - REG_LO < REG_SIZE;
        if (inside && !in) snap_take(1);
        inside = in;
        Sleep(1);
    }
}

static void dump_waits(FILE* f)
{
    fprintf(f, "\nem espera de semaforo:");
    for (uint32_t i = 0; i < 256u; i++)
        if (s_inwait[i]) fprintf(f, " tid%u=sem%u", i, s_inwait[i] - 1u);
    fprintf(f, "\n");
}

static void dump_tasks(FILE* f)
{
    uint8_t livre[256] = { 0 };
    uint32_t h = vm_base[ADDR_FREE];
    for (int k = 0; k < 256 && !livre[h]; k++) { livre[h] = 1; h = vm_base[ADDR_FREE + 1u + h]; }
    fprintf(f, "\nlista_espera contagem=%u:", be32(ADDR_WAITN));
    for (uint32_t i = 0; i < 8u; i++) fprintf(f, " %08X", be32(ADDR_WAITL + i * 4u));
    fprintf(f, "\ntarefas ocupadas ou pendentes (+0xF8 zerado):\n");
    for (uint32_t i = 0; i < 256u; i++) {
        const uint32_t ea = ADDR_TASKS + i * 0x100u;
        if (!readable(ea)) break;
        const uint32_t f8h = be32(ea + 0xF8u), f8l = be32(ea + 0xFCu), w0 = be32(ea), w1 = be32(ea + 4u);
        if ((f8h | f8l) || !(w0 | w1)) continue;
        const job_rec* r = job_slot(ea, 0);
        fprintf(f, "  slot=%3u ea=%08X livre=%d w0=%08X w1=%08X w2=%08X w3=%08X", i, ea, livre[i], w0, w1,
                be32(ea + 8u), be32(ea + 12u));
        if (r) fprintf(f, " img=%u inicios=%u fins=%u t_ini=%u t_fim=%u f8=%08X%08X\n", r->img, r->begins,
                       r->ends, r->t_begin, r->t_end, r->f8_hi, r->f8_lo);
        else fprintf(f, " nunca_despachada\n");
    }
    if (readable(REPORT_EA) && readable(REPORT_EA + 0x10FFCu)) {
        uint32_t nz = 0;
        for (uint32_t o = 0; o < 0x11000u; o += 4u) nz += be32(REPORT_EA + o) != 0;
        fprintf(f, "relatorios em %08X: %u palavras nao nulas em 0x11000 B\n", REPORT_EA, nz);
    }
}

static void dump_words(FILE* f, const char* name, uint32_t ea, uint32_t n)
{
    fprintf(f, "\n%s ea=%08X", name, ea);
    for (uint32_t i = 0; i < n; i++) {
        const uint32_t a = ea + i * 4u;
        if (!(i % 8u)) fprintf(f, "\n  %08X:", a);
        if (readable(a)) fprintf(f, " %08X", be32(a));
        else fprintf(f, " --------");
    }
    fprintf(f, "\n");
}

static void dump_ctx(FILE* f, const char* name, uint32_t ctx)
{
    if (!ctx || !readable(ctx)) { fprintf(f, "%s=%08X sem leitura\n", name, ctx); return; }
    const uint32_t cb = be32(ctx + 12u);
    fprintf(f, "%s=%08X begin=%08X end=%08X current=%08X callback=%08X codigo=%08X\n", name, ctx,
            be32(ctx), be32(ctx + 4u), be32(ctx + 8u), cb, cb && readable(cb) ? be32(cb) : 0u);
}

/* Read-only, on the sampler thread: state of a wait that has stood for a while,
 * and every write of this label still in mapped IO. */
static void stall_scan(void)
{
    static int n;
    if (n >= SCAN_MAX) return;
    char path[460];
    snprintf(path, sizeof path, "%s\\t40_scan_%d.txt", s_dir, n++);
    FILE* f = fopen(path, "w");
    if (!f) return;
    uint32_t v[7], pt = 0, gt = 0, gf = 0, out_ea = 0, ours = 0;
    wait_state(v);
    rdr2_t37_gcm_state(&pt, &gt, &gf);
    rdr2_t40_gcm_ctx(&out_ea, &ours);
    const uint32_t now = now_ms();
    fprintf(f, "ms=%u espera_ms=%u r13=%08X\n", now, now - s_ep_ms, s_r13);
    fprintf(f, "contador=%08X rotulo=%08X idx=%02X\n", v[0], v[1], v[2]);
    fprintf(f, "put=%08X get=%08X getoff=%08X\n", pt, gt, gf);
    dump_ctx(f, "ctx_render", v[3]);
    fprintf(f, "ctx_global_ea=%08X valor=%08X\n", out_ea, out_ea ? be32(out_ea) : 0u);
    dump_ctx(f, "ctx_runtime", ours);
    fprintf(f, "\nrotulos 0x40..0x4F:");
    for (uint32_t i = 0x40u; i < 0x50u; i++) fprintf(f, " %08X", be32(LABEL_BASE + i * 0x10u));
    fprintf(f, "\n");

    enum { KEEP = 32 };
    uint32_t hit[KEEP][2], total = 0;
    const uint32_t want = (v[2] << 4) & 0xFF0u;
    for (uint32_t io = 0; io < IO_SPAN; io += 0x1000u) {
        const uint32_t ea = gcm_io_offset_to_ea(io);
        if (!ea || !readable(ea)) continue;
        for (uint32_t o = 0; o < 0x1000u; o += 4u) {
            if (be32(ea + o) != 0x00041D6Cu || !readable(ea + o + 12u)) continue;
            if (be32(ea + o + 4u) != want || be32(ea + o + 8u) != 0x00041D74u) continue;
            hit[total % KEEP][0] = io + o;
            hit[total % KEEP][1] = be32(ea + o + 12u);
            total++;
        }
    }
    fprintf(f, "\nescritas do rotulo no IO: %u; ultimas em ordem de deslocamento:\n", total);
    for (uint32_t i = total > KEEP ? total - KEEP : 0; i < total; i++)
        fprintf(f, "  io=%08X valor=%08X\n", hit[i % KEEP][0], hit[i % KEEP][1]);

    if (v[3] && v[4]) dump_words(f, "antes de current", (v[4] & ~3u) - 0x80u, 40);
    if (gcm_io_offset_to_ea(pt)) dump_words(f, "em put", gcm_io_offset_to_ea(pt) - 0x40u, 32);
    if (gcm_io_offset_to_ea(gf)) dump_words(f, "em getoff", gcm_io_offset_to_ea(gf) - 0x40u, 32);
    dump_waits(f);
    dump_tasks(f);
    fclose(f);
}

static DWORD WINAPI sampler(LPVOID p)
{
    (void)p;
    mem_fn mem = (mem_fn)GetProcAddress(GetModuleHandleA("kernel32.dll"), "K32GetProcessMemoryInfo");
    for (;;) {
        uint32_t pt = 0, gt = 0, gf = 0, jobs = 0, priv = 0;
        mem_counters mc;
        mc.cb = sizeof mc;
        if (mem && mem(GetCurrentProcess(), &mc, sizeof mc)) priv = (uint32_t)(mc.PrivateUsage >> 20);
        rdr2_t37_gcm_state(&pt, &gt, &gf);
        for (int i = 0; i < N_IMG; i++) jobs += s_map->img[i].jobs;
        put(s_map->samp, RING_SAMP, &s_map->n_samp, 1, pt, gt, gf, cellGcm_flip_request_count(),
            ppu_boot_frames_presented(), jobs, priv);
        for (LONG i = 0; i < s_nw; i++) {
            const uint32_t ea = s_watch[i];
            uint32_t w[4];
            for (int k = 0; k < 4; k++) w[k] = be32(ea + (uint32_t)k * 4u);
            if (!s_seen_ok[i] || memcmp(w, s_seen[i], sizeof w)) {
                s_seen_ok[i] = 1;
                memcpy(s_seen[i], w, sizeof w);
                put(s_map->ev, RING_EV, &s_map->n_ev, 2, ea, w[0], w[1], w[2], w[3], 0, 0);
            }
        }
        {
            /* The trigger is `put` standing still: the render may be stopped outside
             * the label loop, where it never polls. */
            static const uint32_t after[2] = { 3000u, 15000u };
            static uint32_t last_put, put_ms;
            static int scans;
            uint32_t v[7];
            watch_parks();
            wait_state(v);
            put(s_map->t40, RING_T40, &s_map->n_t40, 1, v[0], v[1], v[2], v[3], v[4], v[5], v[6]);
            const uint32_t t = now_ms();
            if (v[5] != last_put) { last_put = v[5]; put_ms = t; scans = 0; }
            if (scans < 2 && t - put_ms >= after[scans]) {
                scans++;
                stall_scan();
            }
        }
        Sleep(10);
    }
}

static int on(void)
{
    if (s_state == 2) return 1;
    if (s_state == 3) return 0;
    if (InterlockedCompareExchange(&s_state, 1, 0) != 0) return s_state == 2;
    char path[460];
    const char* d = getenv("RDR2_T37_DIR");
    if (!d || !*d) { s_state = 3; return 0; }
    snprintf(s_dir, sizeof s_dir, "%s", d);
    snprintf(path, sizeof path, "%s\\t37.ring", s_dir);
    HANDLE f = CreateFileA(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, NULL,
                           CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (f == INVALID_HANDLE_VALUE) { s_state = 3; return 0; }
    HANDLE m = CreateFileMappingA(f, NULL, PAGE_READWRITE, 0, (DWORD)sizeof(t37_map), NULL);
    t37_map* v = m ? (t37_map*)MapViewOfFile(m, FILE_MAP_ALL_ACCESS, 0, 0, 0) : NULL;
    if (!v) { s_state = 3; return 0; }
    QueryPerformanceFrequency(&s_freq);
    QueryPerformanceCounter(&s_t0);
    v->rec_size = sizeof(rec); v->cap_rsx = RING_RSX; v->cap_poll = RING_POLL;
    v->cap_samp = RING_SAMP; v->cap_ev = RING_EV; v->n_img = N_IMG; v->n_point = N_POINT;
    v->cap_t40 = RING_T40;
    v->cap_put = RING_PUT; v->cap_read = RING_READ; v->cap_chg = RING_CHG; v->cap_sem = RING_SEM;
    v->n_snap = N_SNAP; v->snap_size = REG_SIZE; v->n_jobtab = N_JOBTAB;
    s_map = v;
    s_state = 2;
    HANDLE th = CreateThread(NULL, 0, sampler, NULL, 0, NULL);
    if (th) CloseHandle(th);
    th = CreateThread(NULL, 0, watcher, NULL, 0, NULL);
    if (th) CloseHandle(th);
    return 1;
}

/* One copy of the local store and registers per tag. */
static void dump_once(const spu_context* ctx, const char* tag)
{
    static volatile LONG seen[8];
    const int i = tag[0] & 7;
    if (InterlockedExchange(&seen[i], 1)) return;
    char path[460];
    snprintf(path, sizeof path, "%s\\ls_%s.bin", s_dir, tag);
    FILE* f = fopen(path, "wb");
    if (f) { fwrite(ctx->ls, 1, SPU_LS_SIZE, f); fclose(f); }
    snprintf(path, sizeof path, "%s\\ls_%s.txt", s_dir, tag);
    f = fopen(path, "w");
    if (!f) return;
    fprintf(f, "ms=%u pc=%05X status=%X stop=%X depth=%d\n", now_ms(), ctx->pc, ctx->status,
            ctx->stop_code, (int)ctx->host_depth);
    for (int r = 0; r < 128; r++)
        fprintf(f, "r%d %08X %08X %08X %08X\n", r, ctx->gpr[r]._u32[0], ctx->gpr[r]._u32[1],
                ctx->gpr[r]._u32[2], ctx->gpr[r]._u32[3]);
    fclose(f);
}

void rdr2_t37_count(int k)
{
    if (on()) s_map->point[k]++;
}

uint32_t rdr2_t37_ls32(const spu_context* ctx, uint32_t lsa)
{
    const uint8_t* p = ctx->ls + (lsa & 0x3FFFCu);
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

void rdr2_t37_hit(spu_context* ctx, int k, uint32_t a, uint32_t b, uint32_t c, uint32_t d)
{
    if (!on()) return;
    const LONG64 n = InterlockedIncrement64(&s_map->point[k]);
    int want = ((uint64_t)n & (s_every[k] - 1u)) == 0;
    if (k != 1 && (s_last[k][0] != a || s_last[k][1] != b)) want = 1;
    if (k == 1 && s_last[k][1] != b) want = 1;
    if (k == 9 && ctx->host_depth) dump_once(ctx, "aninhado");
    if (k == 1 && b != s_last[k][1] && rdr2_t37_ls32(ctx, 0x3FBC0u + 0x2Cu) == 0)
        dump_once(ctx, "zerado");
    if (!want) return;
    s_last[k][0] = a; s_last[k][1] = b;
    if (k == 4) watch_add(a);
    if (k == 7)
        for (uint32_t o = 0; o < 0x40u; o += 0x10u) watch_add(a + o);
    put(s_map->poll, RING_POLL, &s_map->n_poll, (uint32_t)k, a, b, c, d, (uint32_t)ctx->image_id,
        rdr2_t37_ls32(ctx, 0x3FBC0u + 0x2Cu), (uint32_t)ctx->host_depth);
}

static img_stat* img_for(int image_id)
{
    for (int i = 0; i < N_IMG; i++) {
        const LONG cur = InterlockedCompareExchange((volatile LONG*)&s_map->img[i].image,
                                                    (LONG)image_id, 0);
        if (cur == 0 || cur == image_id) return &s_map->img[i];
    }
    return NULL;
}

void rdr2_t37_job_begin(int image_id, uint32_t job_ea)
{
    if (!on()) return;
    t_img = image_id;
    t_job = job_ea;
    job_rec* jr = job_slot(job_ea, 1);
    if (jr) { jr->img = (uint32_t)image_id; jr->begins++; jr->t_begin = now_ms(); }
    img_stat* s = img_for(image_id);
    if (!s) return;
    const LONG n = InterlockedIncrement((volatile LONG*)&s->started);
    s->last_job = job_ea;
    if (n <= 16)
        put(s_map->ev, RING_EV, &s_map->n_ev, 3, (uint32_t)image_id, job_ea, (uint32_t)n, 0, 0, 0,
            GetCurrentThreadId());
}

void rdr2_t37_job_end(int image_id, uint32_t job_ea, int halted, const spu_context* c)
{
    if (!on()) return;
    t_img = 0;
    t_job = 0;
    job_rec* jr = job_slot(job_ea, 1);
    if (jr) {
        jr->ends++; jr->t_end = now_ms();
        jr->f8_hi = be32(job_ea + 0xF8u); jr->f8_lo = be32(job_ea + 0xFCu);
    }
    if ((uint32_t)image_id == IMG_7639) {
        const uint32_t hi = be32(job_ea + 0xF8u), lo = be32(job_ea + 0xFCu);
        put(s_map->ev, RING_EV, &s_map->n_ev, 9, job_ea, hi, lo, (uint32_t)halted, c->pc, c->stop_code,
            c->gpr[0]._u32[0]);
        dump_once(c, (hi | lo) ? "k7639" : "p7639");
        const unsigned n = g_spu_pch_n;
        put(s_map->ev, RING_EV, &s_map->n_ev, 14, g_spu_pch[n & 7u], g_spu_pch[(n + 1u) & 7u],
            g_spu_pch[(n + 2u) & 7u], g_spu_pch[(n + 3u) & 7u], g_spu_pch[(n + 4u) & 7u],
            g_spu_pch[(n + 5u) & 7u], g_spu_pch[(n + 6u) & 7u]);
        put(s_map->ev, RING_EV, &s_map->n_ev, 15, g_spu_pch[(n + 7u) & 7u], n, job_ea, c->drain_ret_pc,
            (uint32_t)c->host_depth, c->status, 0);
    }
    img_stat* s = img_for(image_id);
    if (!s) return;
    InterlockedIncrement((volatile LONG*)&s->jobs);
    if (!halted || c->pc == JOB_RETURN) {
        InterlockedIncrement((volatile LONG*)&s->normal);
        return;
    }
    InterlockedIncrement((volatile LONG*)&s->abnormal);
    if (c->stop_code == 0x3FFFu) {
        InterlockedIncrement((volatile LONG*)&s->trap);
        dump_once(c, "trap");
    }
    s->last_pc = c->pc;
    put(s_map->ev, RING_EV, &s_map->n_ev, 1, (uint32_t)image_id, job_ea, c->pc, c->stop_code,
        c->gpr[0]._u32[0], c->status, c->gpr[1]._u32[0]);
}

/* path: 0 walker, 1 replayed by a resync. */
void rdr2_t37_rsx(uint32_t m, uint32_t v, uint32_t getoff, int path)
{
    static uint32_t ctx_dma, off;
    if (!on()) return;
    uint32_t target = 0, val = v;
    if (m == 0x01A4u) ctx_dma = v;
    else if (m == 0x1D6Cu) off = v;
    else if (m == 0x1D70u || m == 0x1D74u) {
        target = ctx_dma == 0xFEED0001u ? gcm_io_offset_to_ea(off) : LABEL_BASE + (off & 0x00FFFFFFu);
        if (m == 0x1D70u) val = (v & 0xFF00FF00u) | ((v >> 16) & 0xFFu) | ((v & 0xFFu) << 16);
    }
    put(s_map->rsx, RING_RSX, &s_map->n_rsx, 1, m, val, target, off, ctx_dma, getoff, (uint32_t)path);
}

void rdr2_t37_nv406e(uint32_t m, uint32_t v, uint32_t sema_off, uint32_t getoff, int path)
{
    if (!on()) return;
    put(s_map->rsx, RING_RSX, &s_map->n_rsx, 2, m, v,
        m == 0x6Cu ? LABEL_BASE + (sema_off & 0xFFFFu) : 0u, sema_off, 0, getoff, (uint32_t)path);
}

/* From cellGcmGetLabelAddress, on the calling guest thread. */
void rdr2_t40_poll(uint32_t r13, uint32_t lr)
{
    static uint32_t seen[32][2];
    static volatile LONG n_seen;
    if (!on()) return;
    int known = 0;
    for (LONG i = 0; i < n_seen && i < 32 && !known; i++)
        known = seen[i][0] == r13 && seen[i][1] == lr;
    if (!known) {
        const LONG i = InterlockedIncrement(&n_seen) - 1;
        if (i < 32) {
            seen[i][0] = r13; seen[i][1] = lr;
            put(s_map->ev, RING_EV, &s_map->n_ev, 5, r13, lr, (uint32_t)i, 0, 0, 0, GetCurrentThreadId());
        }
    }
    if (lr != POLL_LR) return;
    s_map->point[12]++;
    const uint32_t t = now_ms(), c = be32(ADDR_COUNT);
    s_r13 = r13;
    s_poll_ms = t;
    if (c != s_ep_count || !s_ep_ms) {
        uint32_t v[7];
        wait_state(v);
        s_ep_count = c;
        s_ep_ms = t;
        InterlockedIncrement(&s_ep_seq);
        put(s_map->t40, RING_T40, &s_map->n_t40, 2, v[0], v[1], v[2], v[3], v[4], v[5], v[6]);
    }
}

void rdr2_t40_resync(const char* why, uint32_t from, uint32_t put_off, uint32_t land)
{
    if (!on()) return;
    char tag[8] = { 0 };
    for (int i = 0; i < 8 && why[i]; i++) tag[i] = why[i];
    const uint32_t ea = gcm_io_offset_to_ea(from);
    const LONG i = why[0] == 'j' && ea ? InterlockedIncrement(&s_n_park) - 1 : N_PARK;
    if (i < N_PARK) {
        s_park[i].io = from; s_park[i].word = be32(ea); s_park[i].ms = now_ms();
        s_park[i].ea = ea;
    }
    put(s_map->ev, RING_EV, &s_map->n_ev, 4, *(const uint32_t*)tag, *(const uint32_t*)(tag + 4),
        from, put_off, land, 0, 0);
    snap_take(2);
}

/* stop: where the replay of the skipped range ended. */
void rdr2_t40_resync_end(uint32_t from, uint32_t land, uint32_t stop, unsigned fences, unsigned labels)
{
    if (!on()) return;
    const uint32_t ea = gcm_io_offset_to_ea(stop);
    put(s_map->ev, RING_EV, &s_map->n_ev, 6, from, land, stop, ea ? be32(ea) : 0u, fences, labels, 0);
}

void rdr2_t40_recycle(uint32_t ctx, uint32_t begin, uint32_t current)
{
    uint32_t pt = 0, gt = 0, gf = 0;
    if (!on()) return;
    s_map->point[13]++;
    rdr2_t37_gcm_state(&pt, &gt, &gf);
    put(s_map->ev, RING_EV, &s_map->n_ev, 7, ctx, begin, current, pt, gf, 0, GetCurrentThreadId());
}

/* From gcm_note_spu_put: an SPU PUT that touches the ring. */
void rdr2_t42_put(uint32_t ea, uint32_t size)
{
    if ((uint32_t)t_img == IMG_7639)
        put(s_map->ev, RING_EV, &s_map->n_ev, 10, ea, size, t_job, be32(ea), 0, 0, 0);
    if (ea >= RING_EA + RING_LEN || ea + size <= RING_EA || !on()) return;
    put(s_map->put42, RING_PUT, &s_map->n_put, 1, ea, size, (uint32_t)t_img, t_job, be32(ea),
        size >= 4u ? be32(ea + (size & ~3u) - 4u) : 0u, GetCurrentThreadId());
}

/* From the walker, per word inside the watched region: first read of each block. */
void rdr2_t42_read(uint32_t io, uint32_t w)
{
    static uint32_t last_blk = 0xFFFFFFFFu, last_ms, lap;
    const uint32_t blk = io >> 8;
    if (blk == last_blk || !on()) return;
    const uint32_t t = now_ms();
    if (t - last_ms > 250u) lap++;
    last_ms = t;
    last_blk = blk;
    put(s_map->read42, RING_READ, &s_map->n_read, 1, io, w, lap, 0, 0, 0, 0);
}

/* op: 1 wait begins, 2 wait ends, 3 post. The two nearest code pointers on the
 * guest stack stand in for a call chain, since back-chain LR slots are empty. */
void rdr2_t42_sema(uint32_t op, uint32_t id, uint32_t tid, uint32_t lr, uint32_t sp, uint32_t extra)
{
    if (!on()) return;
    uint32_t c[2] = { 0, 0 };
    int n = 0;
    if (readable(sp) && readable(sp + 0x3FCu))
        for (uint32_t o = 0; o < 0x400u && n < 2; o += 4u) {
            const uint32_t v = be32(sp + o);
            if (v >= 0x10000u && v < TEXT_END && !(v & 3u) && v != lr && v != c[0]) c[n++] = v;
        }
    if (tid < 256u) {
        if (op == 1u) s_inwait[tid] = id + 1u;
        else if (op == 2u) s_inwait[tid] = 0;
    }
    put(s_map->sem, RING_SEM, &s_map->n_sem, op, id, tid, lr, c[0], c[1], extra, GetCurrentThreadId());
}

/* Attempt 44: job 7639 only, from its lifted source. MFC commands as issued, and
 * each indirect call around the bracket that should bring it back. */
static _Thread_local uint32_t t_mfc[4];   /* LSA, EAH, EAL, Size */

void rdr2_t44_wrch(spu_context* ctx, uint32_t ch, u128 v)
{
    if (ch >= MFC_LSA && ch <= MFC_Size) { t_mfc[ch - MFC_LSA] = v._u32[0]; return; }
    if (ch != MFC_Cmd || !on()) return;
    const uint32_t cmd = v._u32[0] & 0xFFu;
    put(s_map->ev, RING_EV, &s_map->n_ev, 11, cmd, t_mfc[0], t_mfc[2], t_mfc[3], t_job, t_mfc[1], 0);
    if (cmd == 0x44u || cmd == 0x24u) {
        for (uint32_t i = 0; i < 40u && i * 8u < t_mfc[3]; i++)
            put(s_map->ev, RING_EV, &s_map->n_ev, 12, i, rdr2_t37_ls32(ctx, t_mfc[2] + i * 8u),
                rdr2_t37_ls32(ctx, t_mfc[2] + i * 8u + 4u), t_job, 0, 0, 0);
    }
}

void rdr2_t44_call(spu_context* ctx, uint32_t stage, uint32_t ret)
{
    if (!on()) return;
    put(s_map->ev, RING_EV, &s_map->n_ev, 13, stage, ret, t_job, ctx->pc, ctx->gpr[0]._u32[0],
        ctx->gpr[1]._u32[0], (ctx->drain_ret_pc << 13) | (((uint32_t)ctx->host_depth & 0xFFFu) << 1) |
        (g_spu_trampoline_fn != 0));
}
