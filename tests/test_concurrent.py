import threading
import rPickle
import pytest
import sys
import time
from concurrent.futures import ThreadPoolExecutor

class TestConcurrent:
    def test_concurrent_dumps_loads(self):
        data = {'a': 1, 'b': [2, 3, 4], 'c': 'hello' * 100}
        errors = []
        
        def worker():
            try:
                for _ in range(100):
                    packed = rPickle.dumps(data)
                    restored = rPickle.loads(packed)
                    assert restored == data
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        assert not errors, f"Errors occurred: {errors}"

    def test_concurrent_with_extensions(self):
        from datetime import datetime
        data = {'now': datetime.now()}
        ext = rPickle.ext.datetime_ext
        errors = []
        
        def worker():
            try:
                for _ in range(100):
                    packed = rPickle.dumps(data, extensions=ext)
                    restored = rPickle.loads(packed, extensions=ext)
                    assert restored['now'].date() == data['now'].date()
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        assert not errors, f"Errors occurred: {errors}"

    @pytest.mark.skipif(sys.version_info < (3, 15), reason="requires Python 3.15+")
    def test_concurrent_with_sentinel(self):
        MISSING = sentinel('MISSING') # type: ignore
        data = {'status': MISSING}
        errors = []
        
        def worker():
            try:
                for _ in range(100):
                    packed = rPickle.dumps(data)
                    restored = rPickle.loads(packed)
                    assert restored['status'] is MISSING
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        assert not errors, f"Errors occurred: {errors}"

    def test_concurrent_with_cycles(self):
        a = []
        b = [a]
        a.append(b)
        data = a
        errors = []
        
        def worker():
            try:
                for _ in range(100):
                    packed = rPickle.dumps(data)
                    restored = rPickle.loads(packed)
                    assert restored[0][0] is restored
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        assert not errors, f"Errors occurred: {errors}"

    @pytest.mark.skipif(sys.version_info < (3, 15), reason="requires Python 3.15+")
    def test_concurrent_sentinel_registry(self):
        errors = []
        
        def worker():
            try:
                for _ in range(100):
                    s = sentinel(f'TEST_{threading.current_thread().name}') # type: ignore
                    packed = rPickle.dumps(s)
                    restored = rPickle.loads(packed)
                    assert restored is s
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker, name=f'Thread-{i}') for i in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        assert not errors, f"Errors occurred: {errors}"

    def test_concurrent_mixed_types(self):
        data = {
            'none': None,
            'bool': True,
            'int': 42,
            'float': 3.14,
            'str': 'hello',
            'list': [1, 2, 3],
            'tuple': (4, 5, 6),
            'set': {7, 8, 9},
            'dict': {'a': 1, 'b': 2},
        }
        errors = []
        
        def worker():
            try:
                for _ in range(100):
                    packed = rPickle.dumps(data)
                    restored = rPickle.loads(packed)
                    assert restored == data
            except Exception as e:
                errors.append(e)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(10)]
            for f in futures: f.result()
        
        assert not errors, f"Errors occurred: {errors}"

    def test_concurrent_large_data(self):
        data = {'list': list(range(10000)), 'dict': {i: i**2 for i in range(1000)}}
        errors = []
        
        def worker():
            try:
                for _ in range(10):
                    packed = rPickle.dumps(data)
                    restored = rPickle.loads(packed)
                    assert restored == data
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        assert not errors, f"Errors occurred: {errors}"

class TestSMSCtx:
    def test_ctx_basic_parallel(self):
        def worker():
            for _ in range(100):
                with rPickle.set_max_size_ctx(1024):
                    data = rPickle.dumps([1, 2, 3])
                    rPickle.loads(data)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

    def test_ctx_nested_parallel(self):
        def worker():
            for _ in range(50):
                original_1 = rPickle.core._MAX_SIZE
                with rPickle.set_max_size_ctx(2048):
                    original_2 = rPickle.core._MAX_SIZE
                    with rPickle.set_max_size_ctx(512):
                        data = rPickle.dumps({'a': [1, 2, 3]})
                        rPickle.loads(data)
                        assert rPickle.core._MAX_SIZE == 512
                    assert rPickle.core._MAX_SIZE == original_2
                assert rPickle.core._MAX_SIZE == original_1

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads: t.start()
        for t in threads: t.join()

    def test_ctx_raises_on_negative_parallel(self):
        def worker():
            for _ in range(50):
                with pytest.raises(ValueError, match="size must be non-negative"):
                    rPickle.set_max_size_ctx(-1)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

    def test_ctx_with_different_sizes_parallel(self):
        def worker(size):
            for _ in range(100):
                with rPickle.set_max_size_ctx(size):
                    data = rPickle.dumps([size] * 10)
                    rPickle.loads(data)

        sizes = [1024, 2048, 4096, 8192]
        threads = [threading.Thread(target=worker, args=(size,)) for size in sizes for _ in range(3)]
        for t in threads: t.start()
        for t in threads: t.join()

    def test_ctx_race_detection(self):
        original = rPickle.core._MAX_SIZE
        seen = []
        def worker(size, name):
            for _ in range(50):
                with rPickle.set_max_size_ctx(size):
                    s = 's' * size
                    rPickle.loads(rPickle.dumps(s))
                    s += 's'
                    with pytest.raises(ValueError): rPickle.loads(rPickle.dumps(s))
                    current = size
                    seen.append((name, current))
                    time.sleep(0.0001)

        threads = [threading.Thread(target=worker, args=(1 << i, 1 << i)) for i in range(8)]

        for t in threads: t.start()
        for t in threads: t.join()

        rPickle.set_max_size(original)
        for name, val in seen: assert name == val
