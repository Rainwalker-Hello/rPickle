import rPickle
import pytest
import sys

@pytest.mark.skipif(sys.version_info < (3, 15), reason="requires Python 3.15+")
class TestSentinel:
    def test_no_memory_leak(self):
        s = sentinel('MIS') # type: ignore
        d = id(s)
        rPickle.loads(rPickle.dumps(s))
        del s
        with pytest.raises(KeyError): rPickle.core._SENTINEL_REG[d]

    def test_long_reg(self):
        s = sentinel('SSS') # type: ignore
        packed = rPickle.dumps(s)
        del s
        restored = rPickle.loads(packed)
        assert isinstance(restored, sentinel) # type: ignore
        assert restored.__name__ == 'SSS'
        assert restored is rPickle.loads(rPickle.dumps(restored))

    def test_no_sentinel(self):
        data_p314 = bytearray(b'RPkl') + rPickle.core._version.to_bytes(2, 'little') + b'\x03\x0f\x14' + b'\x03MIS'
        ID = id(data_p314).to_bytes(8, 'little').rstrip(b'\x00')
        data_p314 += len(ID).to_bytes()
        data_p314 += ID
        MIS = rPickle.loads(data_p314)
        assert isinstance(MIS, sentinel) # type: ignore
        assert MIS.__name__ == 'MIS'
