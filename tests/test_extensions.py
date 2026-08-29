import rPickle
from datetime import datetime, date, time
from decimal import Decimal
from uuid import uuid4
from fractions import Fraction
from pathlib import Path
from collections import defaultdict, OrderedDict, Counter
from ipaddress import IPv4Address, IPv6Address
from array import array
import sys
import pytest

class TestBuiltinExtensions:
    def test_datetime(self):
        dt = datetime.now()
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

    def test_path(self):
        p = Path('/tmp/test.txt')
        packed = rPickle.dumps(p, extensions=rPickle.ext.Path_ext)
        restored = rPickle.loads(packed, extensions=rPickle.ext.Path_ext)
        assert restored == p

    def test_date(self):
        d = date.today()
        packed = rPickle.dumps(d, extensions=rPickle.ext.date_ext)
        restored = rPickle.loads(packed, extensions=rPickle.ext.date_ext)
        assert restored == d

    def test_time(self):
        t = time(14, 30, 0, 0)
        packed = rPickle.dumps(t, extensions=rPickle.ext.time_ext)
        restored = rPickle.loads(packed, extensions=rPickle.ext.time_ext)
        assert restored == t

    def test_counter(self):
        c = Counter({'a': 3, 'b': 2, 'c': 1})
        packed = rPickle.dumps(c, extensions=rPickle.ext.Counter_ext)
        restored = rPickle.loads(packed, extensions=rPickle.ext.Counter_ext)
        assert restored == c

    def test_ordereddict(self):
        od = OrderedDict([('a', 1), ('b', 2), ('c', 3)])
        packed = rPickle.dumps(od, extensions=rPickle.ext.OrderedDict_ext)
        restored = rPickle.loads(packed, extensions=rPickle.ext.OrderedDict_ext)
        assert restored == od
        assert isinstance(restored, OrderedDict)

    def test_ipv4(self):
        ip = IPv4Address('192.168.1.1')
        packed = rPickle.dumps(ip, extensions=rPickle.ext.IPv4Address_ext)
        restored = rPickle.loads(packed, extensions=rPickle.ext.IPv4Address_ext)
        assert restored == ip

    def test_ipv6(self):
        ip = IPv6Address('2001:db8::1')
        packed = rPickle.dumps(ip, extensions=rPickle.ext.IPv6Address_ext)
        restored = rPickle.loads(packed, extensions=rPickle.ext.IPv6Address_ext)
        assert restored == ip

    def test_array(self):
        arr = array('i', [1, 2, 3, 4, 5])
        packed = rPickle.dumps(arr, extensions=rPickle.ext.array_ext)
        restored = rPickle.loads(packed, extensions=rPickle.ext.array_ext)
        assert restored == arr
        assert restored.typecode == arr.typecode

    def test_multiple_extensions(self):
        data = {
            'dt': datetime.now(),
            'dec': Decimal('3.14'),
            'uuid': uuid4(),
            'frac': Fraction(2, 3),
            'path': Path('/tmp/test.txt'),
            'date': date.today(),
            'time': time(14, 30, 0, 0),
            'counter': Counter({'a': 3, 'b': 1}),
            'od': OrderedDict([('x', 1), ('y', 2)]),
            'ipv4': IPv4Address('192.168.1.1'),
            'ipv6': IPv6Address('2001:db8::1'),
            'array': array('i', [1, 2, 3]),
        }
        ext = (rPickle.ext.datetime_ext | 
               rPickle.ext.Decimal_ext |
               rPickle.ext.UUID_ext |
               rPickle.ext.Fraction_ext |
               rPickle.ext.Path_ext |
               rPickle.ext.date_ext |
               rPickle.ext.time_ext |
               rPickle.ext.Counter_ext |
               rPickle.ext.OrderedDict_ext |
               rPickle.ext.IPv4Address_ext |
               rPickle.ext.IPv6Address_ext |
               rPickle.ext.array_ext
               )
        
        packed = rPickle.dumps(data, extensions=ext)
        restored = rPickle.loads(packed, extensions=ext)

        assert restored['dt'] == data['dt']
        assert restored['dec'] == data['dec']
        assert restored['uuid'] == data['uuid']
        assert restored['frac'] == data['frac']
        assert restored['path'] == data['path']
        assert restored['date'] == data['date']
        assert restored['time'] == data['time']
        assert restored['counter'] == data['counter']
        assert restored['od'] == data['od']
        assert isinstance(restored['od'], OrderedDict)
        assert restored['ipv4'] == data['ipv4']
        assert restored['ipv6'] == data['ipv6']
        assert restored['array'] == data['array']
        assert restored['array'].typecode == data['array'].typecode