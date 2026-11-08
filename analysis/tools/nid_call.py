"""Mostra as chamadas a um import por NID no RDR2.elf, sem executar nada."""
import json
import os
import struct
import sys

ROOT = os.environ.get("RDR_ROOT", os.getcwd())
sys.path.insert(0, os.path.join(ROOT, "referencias", "ps3recomp-v0.18.0", "tools"))
import nid_database  # noqa: E402
import ppu_disasm  # noqa: E402

d = open(os.path.join(ROOT, "build_rdr2", "baseline_v1", "entradas", "RDR2.elf"), "rb").read()
shoff = struct.unpack_from(">Q", d, 40)[0]
_, _, _, addr, off, size = struct.unpack_from(">IIQQQQ", d, shoff + 2 * 64)
n = size // 4
W = struct.unpack(">%dI" % n, d[off:off + n * 4])
imp = json.load(open(os.path.join(ROOT, "build_rdr2", "baseline_v1", "entradas", "RDR2.imports.json")))
for alvo in sys.argv[1:]:
    nid = int(alvo, 16)
    st = [int(i["stub"], 16) for i in imp if int(i["nid"], 16) == nid]
    print(f"== NID {nid:#x} stub {[hex(s) for s in st]}")
    for s in st:
        cs = []
        for i, w in enumerate(W):
            if (w >> 26) == 18 and (w & 3) == 1:
                li = w & 0x03FFFFFC
                li = li - 0x04000000 if li & 0x02000000 else li
                if addr + i * 4 + li == s:
                    cs.append(i)
        print("  chamadas:", [hex(addr + i * 4) for i in cs])
        for i in cs[:3]:
            print("  --- em", hex(addr + i * 4))
            for k in range(i - 12, i + 6):
                ins = ppu_disasm.decode(W[k], addr + k * 4)
                print(f"    {addr + k * 4:#x} {ins.mnemonic} {ins.operands}")

cands = """cellSpursTaskAttribute2Initialize _cellSpursTaskAttribute2Initialize cellSpursTaskGenerateLsPattern cellSpursCreateTask2 cellSpursCreateTask2WithBinInfo cellSpursCreateTaskWithAttribute cellSpursTaskGetLoadableSegmentPattern cellSpursTaskGetReadOnlyAreaPattern cellSpursTaskGetContextSaveAreaSize cellSpursTasksetAttributeSetTasksetSize cellSpursTaskExitCodeGet cellSpursJoinTask2 cellSpursTryJoinTask2 _cellSpursSendSignal cellSpursLFQueueAttachLv2EventQueue cellSpursLFQueueDetachLv2EventQueue _cellSpursLFQueuePushBody _cellSpursLFQueuePopBody cellSpursLFQueueClear cellSpursLFQueueSize cellSpursLFQueueDepth cellSpursLFQueueGetTasksetAddress _cellSpursLFQueueInitialize cellSpursQueueGetDirection cellSpursQueueGetEntrySize cellSpursQueueSize cellSpursQueueDepth cellSpursQueueClear cellSpursQueueGetTasksetAddress _cellSpursQueueInitialize cellSpursQueuePushBody _cellSpursQueuePushBody cellSpursQueuePopBody _cellSpursQueuePopBody cellSpursQueueAttachLv2EventQueue cellSpursQueueDetachLv2EventQueue cellSpursSetGlobalExceptionEventHandler cellSpursUnsetGlobalExceptionEventHandler cellSpursEnableExceptionEventHandler cellSpursGetSpuGuid cellSpursGetTasksetAddress cellSpursAddWorkloadWithAttribute _cellSpursWorkloadAttributeInitialize cellSpursWorkloadAttributeSetName cellSpursWorkloadAttributeSetShutdownCompletionEventHook _cellSpursWorkloadFlagReceiver cellSpursGetWorkloadFlag cellSpursGetWorkloadInfo cellSpursGetWorkloadData cellSpursSetContention cellSpursTraceInitialize cellSpursTraceStart cellSpursTraceStop cellSpursTraceFinalize cellSpursJobChainSetExceptionEventHandler cellSpursJobChainUnsetExceptionEventHandler cellSpursJobChainAttributeSetJobTypeMemoryCheck cellSpursJobChainGetError cellSpursJobChainGetSpursAddress cellSpursGetJobChainId cellSpursGetJobPipelineInfo cellSpursJobSetMaxGrab cellSpursJobHeaderSetJobbin2Param cellSpursCheckJobChain cellSpursRunJobChain cellSpursKickJobChain cellSpursAddUrgentCommand cellSpursAddUrgentCall cellSpursBarrierInitialize cellSpursBarrierGetTasksetAddress cellSpursSemaphoreGetTasksetAddress _cellSpursSemaphoreInitialize cellSpursJobGuardInitialize cellSpursJobGuardNotify cellSpursJobGuardReset cellSpursJobChainGetSpursAddress cellSpursAttributeSetSpuThreadGroupType cellSpursAttributeEnableSystemWorkload cellSpursAttributeSetMemoryContainerForSpuThread cellSpursAttributeEnableSpuPrintfIfAvailable cellSpursInitializeWithAttribute2 cellSpursInitialize _cellSpursAttributeInitialize cellSpursFinalize cellSpursGetSpuThreadId cellSpursGetSpuThreadGroupId cellSpursGetNumSpuThread cellSpursGetInfo cellSpursSetMaxContention cellSpursSetPriorities cellSpursSetPriority cellSpursSetPreemptionVictimHints cellSpursAttachLv2EventQueue cellSpursDetachLv2EventQueue cellSpursEventFlagGetTasksetAddress cellSpursEventFlagClear cellSpursEventFlagTryWait cellSpursEventFlagGetClearMode cellSpursEventFlagGetDirection cellSpursReadyCountAdd cellSpursReadyCountCompareAndSwap cellSpursReadyCountStore cellSpursReadyCountSwap cellSpursRequestIdleSpu cellSpursSendWorkloadSignal cellSpursShutdownTaskset cellSpursJoinTaskset cellSpursTryJoinTask2 cellSpursTasksetAttributeEnableClearLS cellSpursTasksetAttributeSetExceptionEventHandler cellSpursTasksetAttribute2Initialize _cellSpursTasksetAttribute2Initialize cellSpursGetTasksetInfo cellSpursLookUpTasksetAddress cellSpursTasksetGetSpursAddress cellSpursTasksetSetExceptionEventHandler cellSpursTasksetUnsetExceptionEventHandler""".split()
m = {nid_database.compute_nid(c): c for c in cands}
for u in ("9197915f", "1d344406", "77cdac0c"):
    print(f"0x{u}: {m.get(int(u, 16), '?')}")
