"""Lista os 41 NIDs de cellSpurs importados e tenta nomea-los pela API publica."""
import os as _os
# Raiz da arvore de trabalho privada (layout original: build_rdr2/, referencias/).
ROOT = _os.environ.get("RDR_ROOT", _os.getcwd())
import glob, hashlib, re, struct
d = ROOT + "/build_rdr2"
e = open(d + "/baseline_v1/entradas/RDR2.elf", "rb").read()
SUF = bytes.fromhex("6759659904250490566427499489741A")
def calc(n):
    return struct.unpack("<I", hashlib.sha1(n.encode() + SUF).digest()[:4])[0]
base = """Initialize InitializeWithAttribute InitializeWithAttribute2 Finalize GetSpuThreadGroupId GetNumSpuThread GetSpuThreadId
GetInfo SetMaxContention SetPriorities SetPriority SetPreemptionVictimHints AttachLv2EventQueue DetachLv2EventQueue
EnableExceptionEventHandler SetGlobalExceptionEventHandler UnsetGlobalExceptionEventHandler SetExceptionEventHandler
UnsetExceptionEventHandler AddWorkloadWithAttribute AddWorkload ShutdownWorkload WaitForWorkloadShutdown RemoveWorkload
ReadyCountStore GetWorkloadFlag SendWorkloadSignal GetWorkloadData ReadyCountAdd ReadyCountCompareAndSwap ReadyCountSwap
RequestIdleSpu GetWorkloadInfo GetSpuGuid GetJobChainInfo JobChainGetSpursAddress JobChainGetError
EventFlagAttachLv2EventQueue EventFlagDetachLv2EventQueue EventFlagClear EventFlagSet EventFlagTryWait EventFlagWait
EventFlagGetDirection EventFlagGetClearMode EventFlagGetTasksetAddress CreateTasksetWithAttribute CreateTaskset
DestroyTaskset2 DestroyTaskset CreateTask CreateTaskWithAttribute TaskGetLoadableSegmentPattern TaskGetReadOnlyAreaPattern
TaskGenerateLsPattern TaskExitCodeGet TaskExitCodeInitialize TaskExitCodeTryGet TaskGetContextSaveAreaSize JoinTask2
TryJoinTask2 JoinTaskset SendSignal GetTasksetId ShutdownTaskset TasksetAttributeSetName TasksetAttributeSetTasksetSize
TasksetAttributeEnableClearLS TasksetSetExceptionEventHandler TasksetUnsetExceptionEventHandler GetTasksetInfo
CreateTask2 CreateTask2WithBinInfo CreateTaskset2 TasksetAttribute2Initialize BarrierInitialize BarrierGetTasksetAddress
SemaphoreGetTasksetAddress JobGuardInitialize JobGuardNotify JobGuardReset CreateJobChainWithAttribute CreateJobChain
JoinJobChain KickJobChain ShutdownJobChain RunJobChain AddUrgentCommand AddUrgentCall QueuePopBody QueuePushBody
QueueAttachLv2EventQueue QueueDetachLv2EventQueue QueueGetTasksetAddress QueueClear QueueDepth QueueGetEntrySize QueueSize
QueueGetDirection LFQueueAttachLv2EventQueue LFQueueDetachLv2EventQueue LFQueueGetTasksetAddress
AttributeSetMemoryContainerForSpuThread AttributeSetNamePrefix AttributeEnableSpuPrintfIfAvailable
AttributeSetSpuThreadGroupType AttributeEnableSystemWorkload WorkloadAttributeSetName
WorkloadAttributeSetShutdownCompletionEventHook JobChainAttributeSetName JobChainAttributeSetHaltOnError
JobChainAttributeSetJobTypeMemoryCheck GetSpursAddress TraceInitialize TraceFinalize TraceStart TraceStop""".split()
und = """AttributeInitialize WorkloadAttributeInitialize WorkloadFlagReceiver EventFlagInitialize QueueInitialize
LFQueueInitialize LFQueuePushBody LFQueuePopBody TasksetAttributeInitialize TaskAttributeInitialize TaskAttribute2Initialize
TasksetAttribute2Initialize SemaphoreInitialize JobChainAttributeInitialize""".split()
nomes = {calc("cellSpurs" + n): "cellSpurs" + n for n in base}
nomes.update({calc("_cellSpurs" + n): "_cellSpurs" + n for n in und})
ov = open(d + "/work_v3/overlay/cellSpurs.c", encoding="utf-8", errors="ignore").read()
o = 0x1107804 - 0x10000 - 16 * 4
for i in range(41):
    n = struct.unpack_from(">I", e, o + i * 4)[0]
    nm = nomes.get(n, "?")
    print(f"{i:2d} {n:#010x} {nm:44s} {'overlay' if nm != '?' and re.search(r'\b' + nm + r'\s*\(', ov) else ''}")
