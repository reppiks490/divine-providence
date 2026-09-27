import unittest
from challenger_forge.core import ComponentContext
class NestedMetadataTests(unittest.TestCase):
    def test_prefix_slices_nested_bar_aligned_metadata(self):
        ctx=ComponentContext(['X'],[1,2,3,4],{'close':[10,11,12,13]},
            {'factor_available_at':{'a':[1,2,3,4],'b':[1,2,3,4]},'static':{'note':'keep'}})
        p=ctx.prefix(2)
        self.assertEqual(p.metadata['factor_available_at']['a'],[1,2])
        self.assertEqual(p.metadata['factor_available_at']['b'],[1,2])
        self.assertEqual(p.metadata['static']['note'],'keep')
