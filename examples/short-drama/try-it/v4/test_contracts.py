"""Regression contracts for wrong audio wiring, frame rate and actor identity."""
import copy
import json
from pathlib import Path
import unittest
from contracts import validate_audio_graph,validate_actor_sources

PACK=Path(__file__).parent
class SpeechContractTests(unittest.TestCase):
    def setUp(self):self.fixture=json.loads((PACK/'contract-fixture.json').read_text(encoding='utf-8'))
    def test_actual_audio_conditioned_graph(self):validate_audio_graph(self.fixture['graph'],77/16)
    def test_reject_missing_audio_condition(self):
        g=copy.deepcopy(self.fixture['graph']);del g['condition']['inputs']['audio_encoder_output']
        with self.assertRaises(ValueError):validate_audio_graph(g,77/16)
    def test_reject_sampler_bypassing_audio(self):
        g=copy.deepcopy(self.fixture['graph']);g['sample']['inputs']['positive']=['positive',0]
        with self.assertRaises(ValueError):validate_audio_graph(g,77/16)
    def test_reject_fps_speedup(self):
        g=copy.deepcopy(self.fixture['graph']);g['save']['inputs']['fps']=24
        with self.assertRaises(ValueError):validate_audio_graph(g,77/16)
    def test_reject_audio_truncation(self):
        with self.assertRaises(ValueError):validate_audio_graph(self.fixture['graph'],8.2)
    def test_reject_measured_8gb_overlength(self):
        g=copy.deepcopy(self.fixture['graph']);g['condition']['inputs']['length']=145
        with self.assertRaises(ValueError):validate_audio_graph(g,145/16)
    def test_single_master_per_actor(self):validate_actor_sources(self.fixture['actor_cuts'])
    def test_reject_actor_voice_swap(self):
        cuts=copy.deepcopy(self.fixture['actor_cuts']);cuts[0]['speaker']='serena'
        with self.assertRaises(ValueError):validate_actor_sources(cuts)
    def test_reject_mixed_actor_master(self):
        cuts=copy.deepcopy(self.fixture['actor_cuts']);cuts[0]['source_sha256']='0'*64
        with self.assertRaises(ValueError):validate_actor_sources(cuts)
if __name__=='__main__':unittest.main()
