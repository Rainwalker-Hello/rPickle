import rPickle
from hypothesis import given, strategies as st
import math
import sys
import pytest

class TestProtocol:
    data = [1, 1 << 128, b's', 'sss', {'s': 'b', 3: 2}]
    if sys.version_info >= (3, 15): data.append(frozendict({'s': 'b', 3: 2}))

    def assert_equal(self, a, b):
        if isinstance(a, float) and math.isnan(a):
            assert math.isnan(b)
        elif isinstance(a, list | tuple | dict):
            assert len(a) == len(b)
            for x, y in zip(a, b):
                self.assert_equal(x, y)
        else:
            assert a == b

    @given(st.lists(st.one_of(st.integers(), st.text(), st.floats(), st.booleans(), st.none(), st.binary())))
    def test_mixed_list(self, data):
        for p in range(1, rPickle.core._version):
            restored = rPickle.loads(rPickle.dumps(data, protocol=p))
            self.assert_equal(data, restored)

    @given(st.tuples(st.one_of(st.integers(), st.text(), st.floats(), st.booleans(), st.none(), st.binary())))
    def test_mixed_tuple(self, data):
        for p in range(1, rPickle.core._version):
            restored = rPickle.loads(rPickle.dumps(data, protocol=p))
            self.assert_equal(data, restored)

    @given(st.dictionaries(st.one_of(st.integers(), st.text(), st.floats(), st.booleans(), st.none(), st.binary()), st.one_of(st.integers(), st.text(), st.floats(), st.booleans(), st.none(), st.binary())))
    def test_mixed_dict(self, data):
        for p in range(1, rPickle.core._version):
            restored = rPickle.loads(rPickle.dumps(data, protocol=p))
            self.assert_equal(data, restored)

    @pytest.mark.skipif(rPickle.core._version_info < (0, 11, 2), reason="requires rPickle 0.11.2+")
    @pytest.mark.skipif(sys.version_info < (3, 15), reason="requires Python 0.11.2+")
    def test_deep_immutable_chain(self):
        for p in range(3, rPickle.core._version):
            a = frozenset({1})
            b = frozendict({a: a})  # type: ignore
            c = frozendict({b: b})  # type: ignore
            d = (c, c)
            e = [d, d]
            stored = rPickle.loads(rPickle.dumps(e, protocol=p))
            assert stored[0] is stored[1]
            assert stored[0][0] is stored[0][1]
            assert stored[0][0][b] is stored[0][0][list(stored[0][0])[0]]
