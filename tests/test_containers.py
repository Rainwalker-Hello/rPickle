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

    def test_self_tuple(self):
        t = [],
        t[0].append(t)
        stored = rPickle.loads(rPickle.dumps(t))
        assert stored is stored[0][0]

    @pytest.mark.skipif(sys.version_info < (3, 15), reason="requires Python 3.15+")
    def test_self_frozendict(self):
        a = frozendict({'a': {}}) # type: ignore
        a['a']['a'] = a
        stored = rPickle.loads(rPickle.dumps(a))
        assert stored is stored['a']['a']

class TestBullying:
    @pytest.mark.skipif(sys.version_info < (3, 15), reason="requires Python 3.15+")
    def test_cycle_complex(self):
        f = frozenset({5})
        k = frozendict({f: f}) # type: ignore
        a = frozendict({k: k, 'a': {}}) # type: ignore
        a['a']['a'] = a
        t = [],
        t[0].extend([t, a])
        a['a']['b'] = t
        stored = rPickle.loads(rPickle.dumps(a))
        assert stored is stored['a']['a']
        assert stored is stored['a']['b'][0][1]
        assert stored['a']['b'] is stored['a']['b'][0][0]
        assert list(stored)[0] is stored[k]
        assert list(list(stored)[0])[0] is stored[k][f]

    def test_cycle_tuple_list(self):
        t = [], []
        t[0].append(t)
        t[1].append(t)
        t[0].extend(t)
        t[1].extend(t)
        stored = rPickle.loads(rPickle.dumps(t))
        assert stored is stored[0][0]
        assert stored is stored[1][0]
        assert stored[0] is stored[0][1]
        assert stored[0] is stored[1][1]
        assert stored[1] is stored[0][2]
        assert stored[1] is stored[1][2]

    @pytest.mark.skipif(rPickle.core._version_info < (0, 11, 2), reason="requires rPickle 0.11.2+")
    @pytest.mark.skipif(sys.version_info < (3, 15), reason="requires Python 3.15+")
    def test_deep_immutable_chain(self):
        a = frozenset({1})
        b = frozendict({a: a})  # type: ignore
        c = frozendict({b: b})  # type: ignore
        d = (c, c)
        e = [d, d]
        stored = rPickle.loads(rPickle.dumps(e))
        assert stored[0] is stored[1]
        assert stored[0][0] is stored[0][1]
        assert stored[0][0][b] is stored[0][0][list(stored[0][0])[0]]
