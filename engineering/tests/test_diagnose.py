import json
from pathlib import Path
import sys
import unittest
BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/'engineering/scripts'))
from diagnose import collect, report

class DiagnoseTests(unittest.TestCase):
    def test_trace_find_failure_scene(self):
        x=collect(BASE/'engineering/examples/demo_traces.jsonl','run_demo_20261105')
        self.assertEqual(len(x),5)
        y=report('run_demo_20261105',x)
        self.assertIn('scene_04',y)
        self.assertIn('VID_RENDER_RESOURCE_EXHAUSTED',y)
        self.assertIn('尚无充分证据',y)
        self.assertNotIn('CUDA out of memory',y)  # raw evidence must not be echoed
    def test_unknown_run(self):
        x=collect(BASE/'engineering/examples/demo_traces.jsonl','other_run')
        self.assertIn('未找到', report('other_run',x))
    def test_bad_run_id(self):
        with self.assertRaises(ValueError):
            collect(BASE/'engineering/examples/demo_traces.jsonl','../../foo')

if __name__=='__main__':unittest.main()
