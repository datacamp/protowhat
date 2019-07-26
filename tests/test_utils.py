import pytest

from tests.helper import Success, state, dummy_checks
from protowhat.Test import TestFail as TF
from protowhat.sct_syntax import ExGen, LazyChain
from protowhat.utils import (
    legacy_signature,
    _debug,
    get_class_parameters,
    parameters_attr,
)

state = pytest.fixture(state)
dummy_checks = pytest.fixture(dummy_checks)


def test_debug(state, dummy_checks):
    state.do_test(Success("msg"))
    Ex = ExGen(state, dummy_checks)
    try:
        Ex().noop().child_state() >> LazyChain(attr_scts={"_debug": _debug})._debug(
            "breakpoint name"
        )
        assert False
    except TF as e:
        assert "breakpoint name" in str(e)
        assert "history" in str(e)
        assert "child_state" in str(e)
        assert "test" in str(e)


def test_delayed_debug(state, dummy_checks):
    Ex = ExGen(state, {"_debug": _debug, **dummy_checks})
    try:
        Ex()._debug("breakpoint name", on_error=True).noop().child_state().fail()
        assert False
    except TF as e:
        assert "history" in str(e)
        assert "child_state" in str(e)
        assert "test" in str(e)


def test_final_debug(state, dummy_checks):
    Ex = ExGen(state, {"_debug": _debug, **dummy_checks})
    Ex()._debug("breakpoint name", on_error=True).noop().child_state()
    assert state.reporter.fail


def test_get_class_parameters():
    # Given
    class A:
        def __init__(self, a, b="c"):
            pass

    class B(A):
        def __init__(self, one, *args, two=2, **kwargs):
            super().__init__(*args, **kwargs)
            self.one = one
            self.two = two

    # When
    args_a = list(get_class_parameters(A))
    args_b = list(get_class_parameters(B))

    # Then
    assert args_a == ["a", "b"]
    assert args_b == ["a", "b", "one", "two"]


def test_parameters_attr():
    # Given
    class A:
        def __init__(self, a, b="c"):
            pass

    assert not hasattr(A, "parameters")

    # When
    A = parameters_attr(A)

    # Then
    assert A.parameters == ["a", "b"]


def test_legacy_signature():
    @legacy_signature(old_arg1="arg1", old_arg2="arg2")
    def func(arg1, arg2=1):
        return arg1 + arg2

    assert func(1) == 2
    assert func(arg1=1) == 2
    assert func(old_arg1=1) == 2
    assert func(1, arg2=2) == 3
    assert func(1, old_arg2=2) == 3
    assert func(arg1=1, old_arg2=2) == 3
    assert func(old_arg1=1, arg2=2) == 3
    assert func(old_arg1=1, old_arg2=2) == 3
