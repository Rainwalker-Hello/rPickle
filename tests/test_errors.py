import pytest
import rPickle
import os

class TestErrors:
    START = rPickle.dumps(0)[:8]
    
    def test_invalid_data(self):
        with pytest.raises(ValueError, match="invalid data"):
            rPickle.loads(b'not rpickle data')
    
    def test_unsupported_type(self):
        class Custom:
            pass
        
        with pytest.raises(rPickle.UnsupportedTypeError, match="Unsupported type: 'Custom'"):
            rPickle.dumps(Custom())
    
    def test_extension_without_load(self):
        class MyType:
            pass
        
        bad_ext = rPickle.ext.Extension(MyType, None, None)
        
        obj = MyType()
        
        with pytest.raises(TypeError):
            rPickle.dumps(obj, extensions=bad_ext)

    def test_corrupted_data(self):
        good = rPickle.dumps([1, 2, 3])
        
        bad = b'XXXX' + good[4:]
        with pytest.raises(ValueError):
            rPickle.loads(bad)
        
        with pytest.raises(EOFError):
            rPickle.loads(good[:-5])
        
        with pytest.raises(ValueError):
            rPickle.loads(os.urandom(100))

    def test_wrong_protocol(self):
        with pytest.raises(ValueError): rPickle.dumps(0, protocol=65535)
        data = self.START[:4] + b'\xFF\xFF' + self.START[6:]
        with pytest.raises(ValueError): rPickle.loads(data)

    def test_wrong_opcode(self):
        with pytest.raises(ValueError): rPickle.loads(self.START + b'\x0f')