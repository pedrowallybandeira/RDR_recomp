"""Copia experimental de overlay/cellSpurs.c com jobs paralelos dentro de uma cadeia.

No PS3, cada SPU que a cadeia pode usar (maxContention) pega o proximo comando JOB,
entao jobs sem SYNC entre si rodam ao mesmo tempo. O runtime percorre cada cadeia
numa thread so, um job por vez. Com SPURS_JC_PARALLEL=1, os JOBs de uma cadeia com
maxContention > 1 vao para um conjunto de threads, e a caminhada espera por eles
onde a cadeia pede (SYNC, GUARD, END, FLUSH, JOBLIST) e antes de parar.
Sem a variavel, o comportamento e o de antes.
"""
import os as _os
# Raiz da arvore de trabalho privada (layout original: build_rdr2/, referencias/).
ROOT = _os.environ.get("RDR_ROOT", _os.getcwd())
O = ROOT + "/build_rdr2/work_v3/overlay/cellSpurs.c"
S = ROOT + "/build_rdr2/exp_t49/jobs/cellSpurs.c"


def troca(txt, velho, novo):
    if "\r\n" in txt:
        velho = velho.replace("\n", "\r\n")
        novo = novo.replace("\n", "\r\n")
    assert txt.count(velho) == 1, velho[:60]
    return txt.replace(velho, novo)


s = open(O, encoding="utf-8", newline="").read()

s = troca(s, """    u16 size_desc;
    u16 max_grab;
    int run_count;
""", """    u16 size_desc;
    u16 max_grab;
    u32 max_cont;     /* maxContention: SPUs that may work on the chain at once */
    long inflight;    /* jobs handed to the pool and not finished (s_jcq_lock) */
    int run_count;
""")

s = troca(s, """    return jc_register((u32)jc_ea, entry, (u16)(sd_mg >> 16), (u16)(sd_mg & 0xFFFFu),
                       "CreateJobChainWithAttribute");
}
""", """    s32 rc = jc_register((u32)jc_ea, entry, (u16)(sd_mg >> 16), (u16)(sd_mg & 0xFFFFu),
                         "CreateJobChainWithAttribute");
    jc_set_max_cont((u32)jc_ea, vm_read32((u32)attr_ea + JCATTR_MAX_CONT));
    return rc;
}
""")

s = troca(s, """    return jc_register((u32)jc_ea, (u32)entry_ea, (u16)sizeJobDescriptor,
                       (u16)maxGrabbedJob, "CreateJobChain");
}
""", """    s32 rc = jc_register((u32)jc_ea, (u32)entry_ea, (u16)sizeJobDescriptor,
                         (u16)maxGrabbedJob, "CreateJobChain");
    jc_set_max_cont((u32)jc_ea, maxContention);
    return rc;
}
""")

s = troca(s, """/* Register (or re-register) a job chain handle. Shared by both Create forms. */
""", """static void jc_set_max_cont(u32 jc_ea, u32 max_cont)
{
    for (int i = 0; i < MAX_JOBCHAINS; i++)
        if (s_jobchains[i].jc_ea == jc_ea) { s_jobchains[i].max_cont = max_cont; return; }
}

/* Register (or re-register) a job chain handle. Shared by both Create forms. */
""")

s = troca(s, """/* The walk resumes where it stopped. CellSpursJobChain.pc is set at creation
""", """/* Jobs of one chain in parallel (SPURS_JC_PARALLEL=1).
 *
 * On hardware every SPU the chain may use grabs the next JOB command, so jobs
 * that no SYNC separates overlap, up to the chain's maxContention. The walk here
 * hands those jobs to a pool of host threads and waits for them where the stream
 * asks for it. Each job still claims its own SPU number (jc_claim_spu), and the
 * thread that ran it pushes its completion, so the mailbox it posted stays paired
 * with it. */
#define JC_POOL JC_SPUS
typedef struct { u32 jc_ea, job_ea, size_desc; int idx, slot; } jc_work;
static SRWLOCK s_jcq_lock = SRWLOCK_INIT;
static CONDITION_VARIABLE s_jcq_work = CONDITION_VARIABLE_INIT;
static CONDITION_VARIABLE s_jcq_done = CONDITION_VARIABLE_INIT;
static jc_work  s_jcq[256];     /* at most JC_SPUS per chain in flight */
static unsigned s_jcq_head, s_jcq_tail;
static volatile long s_jcq_started;

static u32 jc_parallel(int slot)
{
    static int s_on = -1;
    if (s_on < 0) s_on = getenv("SPURS_JC_PARALLEL") ? 1 : 0;
    u32 n = s_jobchains[slot].max_cont;
    if (!s_on || n <= 1) return 1;
    return n > JC_SPUS ? JC_SPUS : n;
}

static DWORD WINAPI jc_worker(LPVOID p)
{
    ps3_thread_name("spurs jcw %d", (int)(intptr_t)p);
    for (;;) {
        AcquireSRWLockExclusive(&s_jcq_lock);
        while (s_jcq_head == s_jcq_tail)
            SleepConditionVariableSRW(&s_jcq_work, &s_jcq_lock, INFINITE, 0);
        const jc_work w = s_jcq[s_jcq_head++ & 255u];
        ReleaseSRWLockExclusive(&s_jcq_lock);

        { extern u32 g_spurs_job_ls_handle; g_spurs_job_ls_handle = w.jc_ea; }
        jc_run_one_job(w.job_ea, w.idx, w.size_desc);
        jc_signal_done(w.jc_ea, w.idx);

        AcquireSRWLockExclusive(&s_jcq_lock);
        s_jobchains[w.slot].inflight--;
        ReleaseSRWLockExclusive(&s_jcq_lock);
        WakeAllConditionVariable(&s_jcq_done);
    }
}

static void jc_submit(int slot, u32 job_ea, int idx, u32 size_desc, u32 par)
{
    if (!s_jcq_started && !_InterlockedExchange(&s_jcq_started, 1)) {
        for (int i = 0; i < JC_POOL; i++) {
            HANDLE th = CreateThread(NULL, 1u << 20, jc_worker, (LPVOID)(intptr_t)i, 0, NULL);
            if (th) CloseHandle(th);
        }
        printf("[cellSpurs] SPURS_JC_PARALLEL: %d job threads\\n", JC_POOL);
    }
    AcquireSRWLockExclusive(&s_jcq_lock);
    while (s_jobchains[slot].inflight >= (long)par)
        SleepConditionVariableSRW(&s_jcq_done, &s_jcq_lock, INFINITE, 0);
    s_jobchains[slot].inflight++;
    const jc_work w = { s_jobchains[slot].jc_ea, job_ea, size_desc, idx, slot };
    s_jcq[s_jcq_tail++ & 255u] = w;
    ReleaseSRWLockExclusive(&s_jcq_lock);
    WakeConditionVariable(&s_jcq_work);
}

/* Wait until every job this chain handed out has finished. */
static void jc_drain(int slot)
{
    AcquireSRWLockExclusive(&s_jcq_lock);
    while (s_jobchains[slot].inflight)
        SleepConditionVariableSRW(&s_jcq_done, &s_jcq_lock, INFINITE, 0);
    ReleaseSRWLockExclusive(&s_jcq_lock);
}

/* The walk resumes where it stopped. CellSpursJobChain.pc is set at creation
""")

s = troca(s, """    int jobs = 0;
    /* Bound IDLE steps, not total steps. A SPURS job chain is frequently a
""", """    int jobs = 0;
    const u32 par = jc_parallel(slot);
    /* Bound IDLE steps, not total steps. A SPURS job chain is frequently a
""")

s = troca(s, """        if (cmd != 0 && op == 0) {                    /* JOB */
            { extern u32 g_spurs_job_ls_handle; g_spurs_job_ls_handle = jc_ea; }
            int idx = jobs++;
""", """        if (cmd != 0 && op == 0) {                    /* JOB */
            if (par > 1) {
                jc_submit(slot, (u32)(cmd & ~7ull), jobs++, size_desc, par);
                idle = 0;
                pc += 8; continue;
            }
            { extern u32 g_spurs_job_ls_handle; g_spurs_job_ls_handle = jc_ea; }
            int idx = jobs++;
""")

s = troca(s, """            if (ext == (7 | (15 << 3))) {                     /* END */
""", """            if (ext == (7 | (15 << 3))) {                     /* END */
                if (par > 1) jc_drain(slot);
""")

s = troca(s, """            u32 g_ea = (u32)(cmd & ~127ull);
            if (!jg_wait(g_ea)) goto stop;               /* still closed */
""", """            u32 g_ea = (u32)(cmd & ~127ull);
            if (par > 1) jc_drain(slot);
            if (!jg_wait(g_ea)) goto stop;               /* still closed */
""")

s = troca(s, """         * FLUSH(5) / JOBLIST(6, nested arrays TODO) / SET_LABEL */
        pc += 8;
    }
""", """         * FLUSH(5) / JOBLIST(6, nested arrays TODO) / SET_LABEL */
        if (par > 1 && (op == 2 || op == 5 || op == 6)) jc_drain(slot);
        pc += 8;
    }
""")

s = troca(s, """stop:
    s_jobchains[slot].pc = pc; s_jobchains[slot].ret_pc = ret_pc;
}
""", """stop:
    if (par > 1) jc_drain(slot);
    s_jobchains[slot].pc = pc; s_jobchains[slot].ret_pc = ret_pc;
}
""")

# Com jobs paralelos, varios drawablespu notificam o mesmo guard ao mesmo tempo, e
# a caminhada consome os creditos em outra thread: pending precisa ser atomico.
s = troca(s, """    s_jobguards[i].pending++;
    { u32 remaining = (s_jobguards[i].pending >= s_jobguards[i].reset)
                    ? 0u : s_jobguards[i].reset - s_jobguards[i].pending;
""", """    const u32 pend = (u32)_InterlockedIncrement((volatile long*)&s_jobguards[i].pending);
    { u32 remaining = (pend >= s_jobguards[i].reset)
                    ? 0u : s_jobguards[i].reset - pend;
""")
s = troca(s, """        if (s_jobguards[i].pending >= s_jobguards[i].reset) {
            /* Consume exactly one release worth of credits, so notifies that
             * arrived during the previous lap still count. */
            s_jobguards[i].pending -= s_jobguards[i].reset;
""", """        const long pend = (long)s_jobguards[i].pending, need = (long)s_jobguards[i].reset;
        if ((u32)pend >= (u32)need) {
            /* Consume exactly one release worth of credits, so notifies that
             * arrived during the previous lap still count. A notify can land
             * between the read and the write, so the subtraction is a CAS. */
            if (_InterlockedCompareExchange((volatile long*)&s_jobguards[i].pending,
                                           pend - need, pend) != pend) { spin--; continue; }
""")

# Estatistica por cadeia a cada 10 s (so com SPURS_JC_PARALLEL): jobs concluidos,
# jobs em voo e os ultimos descritores entregues.
s = troca(s, """    long inflight;    /* jobs handed to the pool and not finished (s_jcq_lock) */
""", """    long inflight;    /* jobs handed to the pool and not finished (s_jcq_lock) */
    volatile long done;      /* jobs finished, for the periodic statistics */
    u32 last_job[4];         /* last descriptors handed out */
""")
s = troca(s, """        AcquireSRWLockExclusive(&s_jcq_lock);
        s_jobchains[w.slot].inflight--;
""", """        _InterlockedIncrement(&s_jobchains[w.slot].done);
        AcquireSRWLockExclusive(&s_jcq_lock);
        s_jobchains[w.slot].inflight--;
""")
s = troca(s, """    s_jobchains[slot].inflight++;
    const jc_work w = { s_jobchains[slot].jc_ea, job_ea, size_desc, idx, slot };
""", """    s_jobchains[slot].inflight++;
    { static unsigned k; s_jobchains[slot].last_job[k++ & 3u] = job_ea; }
    { static ULONGLONG s_t; const ULONGLONG now = GetTickCount64();
      if (now - s_t >= 10000) {
          static long s_prev[MAX_JOBCHAINS];
          s_t = now;
          for (int c = 0; c < MAX_JOBCHAINS; c++) {
              if (!s_jobchains[c].jc_ea || s_jobchains[c].max_cont <= 1) continue;
              const long d = s_jobchains[c].done;
              fprintf(stderr, "[jc-stat] chain 0x%08X done=%ld (+%ld) inflight=%ld running=%ld kicks=%ld pc=0x%08X last=%08X %08X %08X %08X\\n",
                      s_jobchains[c].jc_ea, d, d - s_prev[c], s_jobchains[c].inflight,
                      s_jobchains[c].running, s_jobchains[c].kicks, s_jobchains[c].pc,
                      s_jobchains[c].last_job[0], s_jobchains[c].last_job[1],
                      s_jobchains[c].last_job[2], s_jobchains[c].last_job[3]);
              s_prev[c] = d;
          }
      } }
    const jc_work w = { s_jobchains[slot].jc_ea, job_ea, size_desc, idx, slot };
""")
open(S, "w", encoding="utf-8", newline="").write(s)
print("gerado", len(s))
