import rPickle
import pytest

class TestSetMaxSize:
    START = rPickle.dumps(0)[:8]

    def test_set_max_size(self):
        old = rPickle.core._MAX_SIZE
        try:
            rPickle.set_max_size(100)
            assert rPickle.core._MAX_SIZE == 100
        finally:
            rPickle.set_max_size(old)
            assert rPickle.core._MAX_SIZE == old

    def test_set_max_size_negative(self):
        with pytest.raises(ValueError, match="size must be non-negative"):
            rPickle.set_max_size(-1)

    def test_set_max_size_non_int(self):
        with pytest.raises(TypeError, match="size must be an integer"):
            rPickle.set_max_size("100")

    def test_payload_exceeds_max_size(self):
        old = rPickle.core._MAX_SIZE
        try:
            rPickle.set_max_size(100)
            payload = self.START + b'\x30\x65' + b'a' * 101
            
            with pytest.raises(ValueError, match="Exceeds the limit"):
                rPickle.loads(payload)
        finally: rPickle.set_max_size(old)

    def test_payload_within_max_size(self):
        old = rPickle.core._MAX_SIZE
        try:
            rPickle.set_max_size(100)
            data = 'a' * 50
            packed = rPickle.dumps(data)
            restored = rPickle.loads(packed)
            assert restored == data
        finally: rPickle.set_max_size(old)

    def test_large_bytearray_payload(self):
        old = rPickle.core._MAX_SIZE
        try:
            rPickle.set_max_size(100)
            payload = self.START + b'\x42\x65' + b'a' * 101
            
            with pytest.raises(ValueError, match="Exceeds the limit"):
                rPickle.loads(payload)
        finally: rPickle.set_max_size(old)

    def test_huge_length_payload(self):
        old = rPickle.core._MAX_SIZE
        try:
            rPickle.set_max_size(100 << 20)
            
            payload = self.START + b'\x43\x08' + (2 << 30).to_bytes(8, 'little')
            
            with pytest.raises(ValueError, match="Exceeds the limit"):
                rPickle.loads(payload)
        finally: rPickle.set_max_size(old)

    def test_zero_max_size(self):
        old = rPickle.core._MAX_SIZE
        try:
            rPickle.set_max_size(0)
            
            data = self.START + b'a'
            packed = rPickle.dumps(data)
            
            with pytest.raises(ValueError, match="Exceeds the limit"):
                rPickle.loads(packed)
        finally: rPickle.set_max_size(old)

class TestSetMaxSizeCtx:
    def test_set_max_size_ctx_basic(self):
        original = rPickle.core._MAX_SIZE
        with rPickle.set_max_size_ctx(1024): assert rPickle.core._MAX_SIZE == 1024
        assert rPickle.core._MAX_SIZE == original

    def test_set_max_size_ctx_default(self):
        original = rPickle.core._MAX_SIZE
        with rPickle.set_max_size_ctx() as limit:
            assert limit == original
            assert rPickle.core._MAX_SIZE == original

    def test_set_max_size_ctx_nested(self):
        original = rPickle.core._MAX_SIZE
        with rPickle.set_max_size_ctx(2048):
            assert rPickle.core._MAX_SIZE == 2048
            with rPickle.set_max_size_ctx(512): assert rPickle.core._MAX_SIZE == 512
            assert rPickle.core._MAX_SIZE == 2048
        assert rPickle.core._MAX_SIZE == original

    def test_set_max_size_ctx_exception(self):
        original = rPickle.core._MAX_SIZE
        try:
            with rPickle.set_max_size_ctx(1024): raise ValueError('test')
        except ValueError: pass
        assert rPickle.core._MAX_SIZE == original

    def test_set_max_size_ctx_works_with_loads(self):
        data = rPickle.dumps('str' * 4)
        with rPickle.set_max_size_ctx(10):
            with pytest.raises(ValueError): rPickle.loads(data)

    def test_set_max_size_ctx_raises_on_negative(self):
        with pytest.raises(ValueError, match="size must be non-negative"):
            rPickle.set_max_size_ctx(-1)

    def test_set_max_size_ctx_raises_on_non_int(self):
        with pytest.raises(TypeError, match="size must be an integer"):
            rPickle.set_max_size_ctx("1024")