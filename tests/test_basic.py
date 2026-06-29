import rPickle
import math
import pytest
import sys

if sys.version_info < (3, 15):
    class sentinel: pass

class TestBasicTypes:
    def test_none(self):
        assert rPickle.loads(rPickle.dumps(None)) is None
    
    def test_bool(self):
        assert rPickle.loads(rPickle.dumps(True)) is True
        assert rPickle.loads(rPickle.dumps(False)) is False
    
    def test_int(self):
        for n in [-1, 0, 1, 127, 128, 32767, 32768, 2**31-1, 2**31, 2**64]:
            assert rPickle.loads(rPickle.dumps(n)) == n
    
    def test_float(self):
        for f in [0.0, 1.5, -3.14, float('inf'), float('-inf')]:
            assert rPickle.loads(rPickle.dumps(f)) == f
        assert math.isnan(rPickle.loads(rPickle.dumps(math.nan)))
    
    def test_complex(self):
        for c in [1+2j, 3.5-4j, 1j]:
            assert rPickle.loads(rPickle.dumps(c)) == c
    
    def test_str(self):
        s = 'Hello 世界 \n\t\r "\' \\ 😎'
        assert rPickle.loads(rPickle.dumps(s)) == s
    
    def test_bytes(self):
        b = b'\x00\x01\x02\xFF'
        assert rPickle.loads(rPickle.dumps(b)) == b
    
    def test_bytearray(self):
        ba = bytearray(b'\x00\x01\x02\xFF')
        result = rPickle.loads(rPickle.dumps(ba))
        assert result == ba
        assert isinstance(result, bytearray)
    
    def test_ellipsis(self):
        assert rPickle.loads(rPickle.dumps(...)) is ...
    
    def test_notimplemented(self):
        assert rPickle.loads(rPickle.dumps(NotImplemented)) is NotImplemented

    @pytest.mark.skipif(sys.version_info < (3, 15), reason='requires Python 3.15+')
    def test_sentinel(self):
        SEN = sentinel('SEN')
        assert rPickle.loads(rPickle.dumps(SEN)).__name__ == SEN.__name__
    