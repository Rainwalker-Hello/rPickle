import rPickle
from hypothesis import given, strategies as st
import math

@given(st.binary())
def test_any_bytes_dont_crash(data):
    try:
        rPickle.loads(data)
    except Exception:
        pass

@given(st.lists(st.integers(), max_size=1000))
def test_any_list_roundtrip(data):
    assert rPickle.loads(rPickle.dumps(data)) == data

@given(st.recursive(st.integers(), st.lists, max_leaves=100))
def test_any_nested(data):
    assert rPickle.loads(rPickle.dumps(data)) == data

@given(st.dictionaries(st.text(), st.integers(), max_size=50))
def test_any_dict(data):
    assert rPickle.loads(rPickle.dumps(data)) == data

def assert_equal(a, b):
    if isinstance(a, float) and math.isnan(a):
        assert math.isnan(b)
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            assert_equal(x, y)
    else:
        assert a == b

@given(st.lists(st.one_of(st.integers(), st.text(), st.floats(), st.booleans(), st.none())))
def test_mixed_list(data):
    restored = rPickle.loads(rPickle.dumps(data))
    assert_equal(data, restored)