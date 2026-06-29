import rPickle
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from fractions import Fraction

class TestBuiltinExtensions:
    def test_datetime(self):
        dt = datetime(2026, 6, 12, 12, 0, 0)
        packed = rPickle.dumps(dt, extensions=rPickle.ext.datetime_ext)
        restored = rPickle.loads(packed, extensions=rPickle.ext.datetime_ext)
        assert restored == dt
    
    def test_decimal(self):
        d = Decimal('3.14159')
        packed = rPickle.dumps(d, extensions=rPickle.ext.Decimal_ext)
        restored = rPickle.loads(packed, extensions=rPickle.ext.Decimal_ext)
        assert restored == d
    
    def test_uuid(self):
        u = uuid4()
        packed = rPickle.dumps(u, extensions=rPickle.ext.UUID_ext)
        restored = rPickle.loads(packed, extensions=rPickle.ext.UUID_ext)
        assert restored == u
    
    def test_fraction(self):
        f = Fraction(3, 4)
        packed = rPickle.dumps(f, extensions=rPickle.ext.Fraction_ext)
        restored = rPickle.loads(packed, extensions=rPickle.ext.Fraction_ext)
        assert restored == f
    
    def test_multiple_extensions(self):
        data = {
            'dt': datetime(2026, 6, 12, 12, 0, 0),
            'dec': Decimal('3.14'),
            'frac': Fraction(2, 3),
        }
        ext = (rPickle.ext.datetime_ext | 
               rPickle.ext.Decimal_ext | 
               rPickle.ext.Fraction_ext)
        packed = rPickle.dumps(data, extensions=ext)
        restored = rPickle.loads(packed, extensions=ext)
        assert restored['dt'] == data['dt']
        assert restored['dec'] == data['dec']
        assert restored['frac'] == data['frac']
