from rPickle.ext import Extension
import pytest

class TestExtension:
    DATA = Extension(list, lambda x: x, lambda x: x)

    def test_or(self):
        self.DATA | self.DATA
        with pytest.raises(TypeError): self.DATA | {}

    def test_ror(self):
        with pytest.raises(TypeError): {} | self.DATA

    def test_ior(self):
        self.DATA |= Extension(tuple, lambda x: x, lambda x: x)
        with pytest.raises(TypeError): self.DATA |= {}
