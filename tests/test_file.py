import rPickle
import tempfile
import os
import pytest

class TestFileStream:
    def test_dump_load_roundtrip(self):
        data = {'a': 1, 'b': [2, 3, 4], 'c': 'hello' * 100}
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.rp') as f:
            rPickle.dump(data, f)
            path = f.name
        
        try:
            with open(path, 'rb') as f: restored = rPickle.load(f)
            assert restored == data
        finally: os.unlink(path)

    def test_dump_load_large_data(self):
        data = {'list': list(range(10000)), 'dict': {i: i**2 for i in range(1000)}}
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.rp') as f:
            rPickle.dump(data, f)
            path = f.name
        
        try:
            with open(path, 'rb') as f: restored = rPickle.load(f)
            assert restored == data
        finally: os.unlink(path)

    def test_dump_load_multiple_objects(self):
        data1 = [1, 2, 3]
        data2 = {'a': 1, 'b': 2}
        data3 = 'hello'
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.rp') as f:
            rPickle.dump(data1, f)
            rPickle.dump(data2, f)
            rPickle.dump(data3, f)
            path = f.name
        
        try:
            with open(path, 'rb') as f:
                restored1 = rPickle.load(f)
                restored2 = rPickle.load(f)
                restored3 = rPickle.load(f)
            assert restored1 == data1
            assert restored2 == data2
            assert restored3 == data3
        finally: os.unlink(path)

    def test_dump_load_with_extensions(self):
        from datetime import datetime
        from decimal import Decimal
        
        data = {
            'dt': datetime.now(),
            'dec': Decimal('3.14159')
        }
        ext = rPickle.ext.datetime_ext | rPickle.ext.Decimal_ext
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.rp') as f:
            rPickle.dump(data, f, extensions=ext)
            path = f.name
        
        try:
            with open(path, 'rb') as f: restored = rPickle.load(f, extensions=ext)
            assert restored['dt'].date() == data['dt'].date()
            assert restored['dec'] == data['dec']
        finally: os.unlink(path)

    def test_load_corrupted_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.rp') as f:
            f.write(b'not rpickle data')
            path = f.name
        
        try:
            with pytest.raises(ValueError, match="invalid data"):
                with open(path, 'rb') as f: rPickle.load(f)
        finally: os.unlink(path)

    def test_old_protocol_file(self):
        data = {'a': 1, 'b': [2, 3, 4], 'c': 'hello' * 100}

        for protocol in range(1, rPickle.core._version):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.rp') as f:
                rPickle.dump(data, f, protocol=protocol)
                path = f.name
            
            try:
                with open(path, 'rb') as f:
                    assert rPickle.load(f) == data
            finally: os.unlink(path)