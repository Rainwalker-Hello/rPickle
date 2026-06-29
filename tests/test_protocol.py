import rPickle

class TestProtocol:
    def test_v1_1(self):
        data = [1, 2, 3, 'hello']
        assert rPickle.loads(rPickle.dumps(data, protocol=1)) == data
    
    def test_v1_2(self):
        data = {'x': 10, 'y': 20}
        v1_packed = rPickle.dumps(data, protocol=1)
        assert rPickle.loads(v1_packed) == data