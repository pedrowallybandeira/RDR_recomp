/* hsamp: amostra de fora as threads mais ocupadas de um processo e imprime as
 * pilhas mais frequentes. So le o outro processo; cada thread fica suspensa
 * apenas durante a leitura do contexto e da pilha.
 *
 * uso: hsamp <pid> <amostras> <intervalo_ms>
 */
#include <windows.h>
#include <tlhelp32.h>
#include <dbghelp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_TH 256
#define TOP 3
#define MAX_FR 16
#define MAX_KEY 4096

typedef struct { DWORD tid; ULONGLONG t0; ULONGLONG d; } Th;
typedef struct { DWORD64 pc[MAX_FR]; int n; int hits; } Chave;

static HANDLE g_proc;
static Chave g_ch[TOP][MAX_KEY];
static int g_nch[TOP];
static int g_folha_n[TOP];

static ULONGLONG cpu100ns(HANDLE h)
{
    FILETIME c, e, k, u;
    if (!GetThreadTimes(h, &c, &e, &k, &u)) return 0;
    return ((ULONGLONG)k.dwHighDateTime << 32 | k.dwLowDateTime) +
           ((ULONGLONG)u.dwHighDateTime << 32 | u.dwLowDateTime);
}

static const char* nome(DWORD64 a, char* out, size_t cap)
{
    char buf[sizeof(SYMBOL_INFO) + 256];
    SYMBOL_INFO* s = (SYMBOL_INFO*)buf;
    IMAGEHLP_MODULE64 m;
    DWORD64 d = 0;
    memset(buf, 0, sizeof buf);
    s->SizeOfStruct = sizeof(SYMBOL_INFO);
    s->MaxNameLen = 255;
    memset(&m, 0, sizeof m);
    m.SizeOfStruct = sizeof m;
    int tem_mod = SymGetModuleInfo64(g_proc, a, &m);
    if (SymFromAddr(g_proc, a, &d, s))
        snprintf(out, cap, "%s!%s+0x%llX", tem_mod ? m.ModuleName : "?", s->Name, (unsigned long long)d);
    else if (tem_mod)
        snprintf(out, cap, "%s+0x%llX", m.ModuleName, (unsigned long long)(a - m.BaseOfImage));
    else
        snprintf(out, cap, "0x%llX", (unsigned long long)a);
    return out;
}

static void guarda(int i, const DWORD64* pc, int n)
{
    for (int k = 0; k < g_nch[i]; k++) {
        Chave* c = &g_ch[i][k];
        if (c->n == n && !memcmp(c->pc, pc, n * sizeof(DWORD64))) { c->hits++; return; }
    }
    if (g_nch[i] < MAX_KEY) {
        Chave* c = &g_ch[i][g_nch[i]++];
        memcpy(c->pc, pc, n * sizeof(DWORD64));
        c->n = n; c->hits = 1;
    }
}

static int por_hits(const void* a, const void* b)
{ return ((const Chave*)b)->hits - ((const Chave*)a)->hits; }

static int por_d(const void* a, const void* b)
{
    ULONGLONG x = ((const Th*)a)->d, y = ((const Th*)b)->d;
    return x < y ? 1 : x > y ? -1 : 0;
}

int main(int argc, char** argv)
{
    if (argc < 4) { puts("uso: hsamp <pid> <amostras> <intervalo_ms>"); return 2; }
    DWORD pid = (DWORD)atoi(argv[1]);
    int amostras = atoi(argv[2]);
    DWORD ms = (DWORD)atoi(argv[3]);
    g_proc = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (!g_proc) { printf("OpenProcess falhou: %lu\n", GetLastError()); return 1; }
    SymSetOptions(SYMOPT_DEFERRED_LOADS | SYMOPT_UNDNAME);
    SymInitialize(g_proc, NULL, TRUE);

    static Th th[MAX_TH];
    int nth = 0;
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    THREADENTRY32 te; te.dwSize = sizeof te;
    if (Thread32First(snap, &te)) do {
        if (te.th32OwnerProcessID == pid && nth < MAX_TH) {
            HANDLE h = OpenThread(THREAD_QUERY_INFORMATION, FALSE, te.th32ThreadID);
            if (h) { th[nth].tid = te.th32ThreadID; th[nth].t0 = cpu100ns(h); nth++; CloseHandle(h); }
        }
    } while (Thread32Next(snap, &te));
    CloseHandle(snap);
    Sleep(3000);
    for (int i = 0; i < nth; i++) {
        HANDLE h = OpenThread(THREAD_QUERY_INFORMATION, FALSE, th[i].tid);
        th[i].d = h ? cpu100ns(h) - th[i].t0 : 0;
        if (h) CloseHandle(h);
    }
    qsort(th, nth, sizeof(Th), por_d);
    int top = nth < TOP ? nth : TOP;
    HANDLE hs[TOP];
    for (int i = 0; i < top; i++) {
        hs[i] = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, FALSE, th[i].tid);
        printf("thread %lu: %.0f%% da CPU em 3 s\n", th[i].tid, th[i].d / 3e5);
    }
    for (int s = 0; s < amostras; s++) {
        for (int i = 0; i < top; i++) {
            if (!hs[i] || SuspendThread(hs[i]) == (DWORD)-1) continue;
            CONTEXT c; memset(&c, 0, sizeof c); c.ContextFlags = CONTEXT_FULL;
            if (GetThreadContext(hs[i], &c)) {
                STACKFRAME64 f; memset(&f, 0, sizeof f);
                f.AddrPC.Offset = c.Rip; f.AddrPC.Mode = AddrModeFlat;
                f.AddrFrame.Offset = c.Rbp; f.AddrFrame.Mode = AddrModeFlat;
                f.AddrStack.Offset = c.Rsp; f.AddrStack.Mode = AddrModeFlat;
                DWORD64 pc[MAX_FR]; int n = 0;
                while (n < MAX_FR && StackWalk64(IMAGE_FILE_MACHINE_AMD64, g_proc, hs[i], &f, &c, NULL,
                                                 SymFunctionTableAccess64, SymGetModuleBase64, NULL)) {
                    if (!f.AddrPC.Offset) break;
                    pc[n++] = f.AddrPC.Offset;
                }
                if (n) { guarda(i, pc, n); g_folha_n[i]++; }
            }
            ResumeThread(hs[i]);
        }
        Sleep(ms);
    }
    for (int i = 0; i < top; i++) {
        printf("\n=== thread %lu: %d amostras, %d pilhas distintas\n", th[i].tid, g_folha_n[i], g_nch[i]);
        qsort(g_ch[i], g_nch[i], sizeof(Chave), por_hits);
        for (int k = 0; k < g_nch[i]; k++) {
            Chave* c = &g_ch[i][k];
            printf("--- %d\n", c->hits);
            for (int f = 0; f < c->n && f < 16; f++) { char b[320]; printf("  %s\n", nome(c->pc[f], b, sizeof b)); }
        }
    }
    return 0;
}

