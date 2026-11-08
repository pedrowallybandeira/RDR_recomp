"""Poe uma chamada a exp_dma_audit (audit.c) no inicio de mfc_do_transfer do
spu_dma.h copiado aqui (v0.19). spu_channels.c, copiado ao lado, pega este
spu_dma.h pelo #include com aspas; os TUs SPU, por --inc-first."""
p = "spu_dma.h"
s = open(p, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
velho = ("static inline int mfc_do_transfer(spu_context* spu, uint32_t lsa, uint64_t ea,\n"
         "                                   uint32_t size, uint32_t cmd)\n{\n").replace("\n", nl)
assert s.count(velho) == 1
novo = velho + ("    { extern void exp_dma_audit(spu_context*, uint32_t, uint64_t, uint32_t, uint32_t);" + nl +
                "      exp_dma_audit(spu, lsa, ea, size, cmd); }" + nl)
open(p, "w", encoding="utf-8", newline="").write(s.replace(velho, novo))
print("gerado")
