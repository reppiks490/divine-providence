
import unittest
from challenger_forge.core import ComponentContext

class CoreMetadataTests(unittest.TestCase):
    def test_prefix_slices_bar_aligned_metadata(self):
        ctx=ComponentContext(
            ["X"], [1,2,3,4],
            {"close":[10,11,12,13]},
            {"session_id":["a","a","b","b"],"static_note":"keep"}
        )
        p=ctx.prefix(2)
        self.assertEqual(p.timestamps,[1,2])
        self.assertEqual(p.series["close"],[10,11])
        self.assertEqual(p.metadata["session_id"],["a","a"])
        self.assertEqual(p.metadata["static_note"],"keep")
