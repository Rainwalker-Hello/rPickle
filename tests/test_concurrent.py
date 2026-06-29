import threading
import rPickle

def test_concurrent_dumps():
    data = list(range(1000))
    errors = []
    
    def worker():
        try:
            for _ in range(100):
                rPickle.loads(rPickle.dumps(data))
        except Exception as e:
            errors.append(e)
    
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert not errors