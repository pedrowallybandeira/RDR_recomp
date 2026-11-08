"""Testes do launcher sem interface e sem rodar o jogo: python launcher/test_launcher.py"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rdr_launcher as L  # noqa: E402


class Testes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = dict(L.PADRAO, local=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def toca(self, *partes):
        p = os.path.join(self.tmp.name, *partes)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").close()

    def test_vazio_tudo_falta(self):
        r = L.confere(self.s)
        self.assertFalse(r[0][0])
        self.assertFalse(r[1][0])

    def test_instalacao_completa(self):
        self.toca("build", "MyGameRecomp.exe")
        self.toca("game", "RDR2.elf")
        self.toca("vfs", "PS3_GAME", "PARAM.SFO")
        self.toca("vfs", "game", "BLUS30418", "USRDIR", "x.rpf")
        os.makedirs(os.path.join(self.tmp.name, "vfs", "game", "BLUS30418", "USRDIR", "dlcPack"))
        self.toca("overlay", "cellSpurs.c")
        faltas = [m for ok, m in L.confere(self.s) if not ok]
        self.assertEqual(faltas, [])

    def test_ambiente(self):
        self.s.update(pad_script=True, extra_env="SPU_INTERP_STATS=30\n# comentario\nX = y")
        e = L.ambiente(self.s, base={"PAD_SCRIPT": "velho"})
        self.assertEqual(e["PAD_SCRIPT"], L.PAD_ATE_A_CENA)
        self.assertEqual(e["PS3_VERBOSE"], "0")
        self.assertEqual(e["SPU_INTERP_STATS"], "30")
        self.assertEqual(e["X"], "y")
        self.assertEqual(e["RDR_ROOT"], self.tmp.name)
        self.s["pad_script"] = False
        self.assertNotIn("PAD_SCRIPT", L.ambiente(self.s, base={"PAD_SCRIPT": "velho"}))

    def test_comando_usa_boot_seguro(self):
        c = L.comando(self.s, "t1")
        self.assertIn(L.BOOT, c)
        self.assertEqual(c[c.index("-Segundos") + 1], "1800")
        self.assertIn("-Visivel", c)
        self.s["visivel"] = False
        self.assertNotIn("-Visivel", L.comando(self.s, "t1"))


if __name__ == "__main__":
    unittest.main()
