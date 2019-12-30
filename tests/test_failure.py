import pytest

from protowhat.failure import _debug, InstructorError
from protowhat.sct_syntax import LazyChain, ExGen
from tests.helper import state, dummy_checks, Success

state = pytest.fixture(state)
dummy_checks = pytest.fixture(dummy_checks)


def test_debug(state, dummy_checks):
    state.do_test(Success("msg"))
    sct_dict = {"_debug": _debug, **dummy_checks}
    Ex = ExGen(sct_dict, state)
    try:
        Ex().noop().child_state() >> LazyChain(chainable_functions=sct_dict)._debug(
            "breakpoint name"
        )
        assert False
    except InstructorError as e:
        assert "breakpoint name" in str(e)
        assert "history" in str(e)
        assert "child_state" in str(e)
        assert "test" in str(e)


def test_delayed_debug(state, dummy_checks):
    Ex = ExGen({"_debug": _debug, **dummy_checks}, state)
    try:
        Ex()._debug("breakpoint name", on_error=True).noop().child_state().fail()
        assert False
    except InstructorError as e:
        assert "history" in str(e)
        assert "child_state" in str(e)
        assert "test" in str(e)


def test_final_debug(state, dummy_checks):
    Ex = ExGen({"_debug": _debug, **dummy_checks}, state)
    Ex()._debug("breakpoint name", on_error=True).noop().child_state()
    assert state.reporter.fail
