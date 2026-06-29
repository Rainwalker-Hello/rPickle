import rPickle
import sys
import pytest

class TestContainers:
    def test_list(self):
        data = [1, 2, 3, 'a', None]
        assert rPickle.loads(rPickle.dumps(data)) == data
    
    def test_tuple(self):
        data = (1, 2, 3, 'a', None)
        assert rPickle.loads(rPickle.dumps(data)) == data
    
    def test_dict(self):
        data = {'a': 1, 'b': [2, 3], 'c': None}
        assert rPickle.loads(rPickle.dumps(data)) == data
    
    def test_set(self):
        data = {1, 2, 3}
        assert rPickle.loads(rPickle.dumps(data)) == data
    
    def test_frozenset(self):
        data = frozenset([1, 2, 3])
        assert rPickle.loads(rPickle.dumps(data)) == data
    
    def test_nested(self):
        data = [{'a': (1, 2)}, {b'key': {3, 4}}]
        assert rPickle.loads(rPickle.dumps(data)) == data

    def test_empty_containers(self):
        assert rPickle.loads(rPickle.dumps([])) == []
        assert rPickle.loads(rPickle.dumps({})) == {}
        assert rPickle.loads(rPickle.dumps(set())) == set()
        assert rPickle.loads(rPickle.dumps(())) == ()
        assert rPickle.loads(rPickle.dumps(frozenset())) == frozenset()
        if sys.version_info >= (3, 15):
            assert rPickle.loads(rPickle.dumps(frozendict())) == frozendict()

    @pytest.mark.skipif(rPickle.core._version_info < (0, 2), reason="requires rPickle 0.2+")
    def test_deep_nesting(self):
        obj = []
        curr = obj
        for _ in range(10000):
            curr.append([])
            curr = curr[-1]
        
        restored = rPickle.loads(rPickle.dumps(obj))
        curr2 = restored
        depth = 0
        while isinstance(curr2, list) and curr2:
            curr2 = curr2[0]
            depth += 1
        assert depth == 10000

class TestCircularReferences:
    def test_self_list(self):
        a = []
        a.append(a)
        b = rPickle.loads(rPickle.dumps(a))
        assert b[0] is b
    
    def test_self_dict(self):
        d = {}
        d['self'] = d
        e = rPickle.loads(rPickle.dumps(d))
        assert e['self'] is e
    
    def test_shared_reference(self):
        inner = [1, 2]
        outer = [inner, inner]
        result = rPickle.loads(rPickle.dumps(outer))
        assert result[0] is result[1]

    def test_complex_cycle(self):
        a, b, c = [], [], []
        a.append(b)
        b.append(c)
        c.append(a)
        
        restored = rPickle.loads(rPickle.dumps([a, b, c]))
        ra, rb, rc = restored
        assert ra[0] is rb
        assert rb[0] is rc
        assert rc[0] is ra