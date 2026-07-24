import rPickle
from hypothesis import given, strategies as st
import math

class TestFuzzing:
    @given(st.binary())
    def test_any_bytes_dont_crash(self, data):
        try:
            rPickle.loads(data)
        except Exception:
            pass

    @given(st.lists(st.integers(), max_size=1000))
    def test_any_list_roundtrip(self, data):
        assert rPickle.loads(rPickle.dumps(data)) == data

    @given(st.recursive(st.integers(), st.lists, max_leaves=100))
    def test_any_nested(self, data):
        assert rPickle.loads(rPickle.dumps(data)) == data

    @given(st.dictionaries(st.text(), st.integers(), max_size=50))
    def test_any_dict(self, data):
        assert rPickle.loads(rPickle.dumps(data)) == data

    def assert_equal(self, a, b):
        if isinstance(a, float) and math.isnan(a):
            assert math.isnan(b)
        elif isinstance(a, list):
            assert len(a) == len(b)
            for x, y in zip(a, b):
                self.assert_equal(x, y)
        else:
            assert a == b

    @given(st.lists(st.one_of(st.integers(), st.text(), st.floats(), st.booleans(), st.none())))
    def test_mixed_list(self, data):
        restored = rPickle.loads(rPickle.dumps(data))
        self.assert_equal(data, restored)