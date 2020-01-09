import re

import pytest

from protowhat.failure import InstructorError
from tests.helper import state, dummy_checks
from protowhat.State import State
from protowhat.sct_syntax import (
    ExGen,
    state_dec_gen,
    get_checks_dict,
    create_sct_context,
    EagerChain,
    LazyChain,
    ChainExtender,
    ChainedCall,
    LazyChainStart,
)

sct_dict = {}
Ex = ExGen(sct_dict, None)
state_dec = state_dec_gen(sct_dict)

state = pytest.fixture(state)
dummy_checks = pytest.fixture(dummy_checks)


@pytest.fixture
def addx():
    return lambda state, x: state + x


@pytest.fixture
def f():
    return LazyChain(ChainedCall(lambda state, b: state + b, kwargs={"b": "b"}))


@pytest.fixture
def f2():
    return LazyChain(ChainedCall(lambda state, c: state + c, kwargs={"c": "c"}))


def test_f_from_func(f):
    assert f("a") == "ab"


def test_f_sct_copy_kw(addx):
    assert LazyChain(ChainedCall(addx, kwargs={"x": "x"}))("state") == "statex"


def test_f_sct_copy_pos(addx):
    assert LazyChain(ChainedCall(addx, ("x",)))("state") == "statex"


def test_ex_sct_copy_kw(addx):
    assert (
        EagerChain(ChainedCall(addx, kwargs={"x": "x"}), state="state")._state
        == "statex"
    )


def test_ex_sct_copy_pos(addx):
    assert EagerChain(ChainedCall(addx, ("x",)), state="state")._state == "statex"


def test_f_2_funcs(f, addx):
    g = ChainExtender(f, addx)

    assert g(x="x")("a") == "abx"


def test_f_add_unary_func(f):
    g = f >> (lambda state: state + "c")
    assert g("a") == "abc"


def test_f_add_f(f, f2):
    g = f >> f2
    assert g("a") == "abc"


def test_f_from_state_dec(addx):
    dec_addx = state_dec(addx)
    f = dec_addx(x="x")
    isinstance(f, LazyChain)
    assert f("state") == "statex"


@pytest.fixture
def ex():
    return ChainExtender(Ex("state"), lambda state, x: state + x)("x")


def test_ex_add_f(ex, f):
    assert (ex >> f)._state == "statexb"


def test_ex_add_f_add_f(ex, f, f2):
    assert (ex >> (f >> f2))._state == "statexbc"


def test_ex_add_unary(ex):
    chain = ex >> (lambda state: state + "b")
    assert isinstance(chain, EagerChain)
    assert chain._state == "statexb"
    assert chain("rerun") == "rerunxb"


def test_ex_add_ex_err(ex):
    with pytest.raises(BaseException):
        ex >> ex


def test_f_add_ex_err(f, ex):
    with pytest.raises(BaseException):
        f >> ex


def test_state_dec_instant_eval(state):
    @state_dec
    def stu_code(state, x="x"):
        return state.student_code + x

    assert stu_code(state) == "student_codex"


def test_sct_dict_creation():
    from protowhat import checks

    sct_dict = get_checks_dict(checks)
    assert isinstance(sct_dict, dict)
    assert sct_dict == {
        str(sct.__name__): sct
        for sct in [checks.get_bash_history, checks.update_bash_history_info]
    }  # other checks not exported in init

    from protowhat.checks import check_simple

    sct_dict = get_checks_dict(check_simple)

    assert len(sct_dict) == 3
    assert sct_dict["has_chosen"] == check_simple.has_chosen
    assert sct_dict["success_msg"] == check_simple.success_msg


def test_sct_context_creation(state, dummy_checks):
    sct_ctx = create_sct_context(dummy_checks)

    for check in ["noop", "child_state"]:
        assert check in sct_ctx
        assert callable(sct_ctx[check])

    for chain in ["Ex", "F"]:
        assert chain in sct_ctx

    assert isinstance(sct_ctx["Ex"](state), EagerChain)
    assert isinstance(sct_ctx["F"]()(state), State)


def test_state_linking_root_creator(state):
    def diagnose(end_state):
        assert end_state.creator is None

    TestF = LazyChainStart({"diagnose": diagnose})

    Ex(state) >> TestF().diagnose()


def test_state_linking_root_creator_noop(state, dummy_checks):
    def diagnose(end_state):
        assert end_state.creator is None

    sct_dict = {"diagnose": diagnose, **dummy_checks}
    TestEx = ExGen(sct_dict, state)
    TestF = LazyChainStart(sct_dict)
    TestEx().noop() >> TestF().diagnose()


def test_state_linking_root_creator_child_state(state, dummy_checks):
    def diagnose(end_state):
        assert end_state != state
        assert end_state.parent_state is state
        assert len(end_state.state_history) == 2
        assert state == end_state.state_history[0]
        assert end_state == end_state.state_history[1]

    sct_dict = {"diagnose": diagnose, **dummy_checks}
    TestEx = ExGen(sct_dict, state)
    TestF = LazyChainStart(sct_dict)
    TestEx().child_state() >> TestF().diagnose()


def test_dynamic_registration(state, dummy_checks):
    diagnose_calls = 0

    @state_dec_gen(dummy_checks)
    def diagnose(end_state):
        assert end_state.state_history[0] is state
        nonlocal diagnose_calls
        diagnose_calls += 1

    TestEx = ExGen(dummy_checks, state)
    TestF = LazyChainStart(dummy_checks)

    TestEx.register_chainable_function(diagnose)

    TestEx().diagnose()
    TestEx() >> TestF().diagnose()
    TestEx() >> diagnose()
    assert diagnose_calls == 3

    TestEx().diagnose().noop()
    TestEx() >> TestF().diagnose().noop()
    TestEx() >> diagnose().noop()
    assert diagnose_calls == 6

    TestEx().child_state().diagnose()


def test_dynamic_registration_named(state, dummy_checks):
    diagnose_calls = 0

    @state_dec_gen(dummy_checks)
    def diagnose(end_state):
        assert end_state.state_history[0] is state
        nonlocal diagnose_calls
        diagnose_calls += 1

    TestEx = ExGen(dummy_checks, state)
    TestF = LazyChainStart(dummy_checks)

    TestEx.register_chainable_function(diagnose, "test123")

    TestEx().test123()
    TestEx() >> TestF().test123()
    TestEx() >> diagnose()
    assert diagnose_calls == 3

    with pytest.raises(AttributeError):
        TestEx().diagnose()

    with pytest.raises(NameError):
        TestEx() >> test123()


def test_dynamic_registration_raising(state, dummy_checks):
    @state_dec_gen(dummy_checks)
    def diagnose(_):
        raise InstructorError.from_message("problem")

    TestEx = ExGen(dummy_checks, state)
    TestEx.register_chainable_function(diagnose)

    with pytest.raises(InstructorError) as e:
        TestEx().diagnose()

    # If calls with a state argument in state_dec would be decorated with link_to_state,
    # there would be a double link_to_state call when an sct decorated with state_dec
    # is registered for chaining
    assert len(re.findall("Debug", str(e.value))) == 1
    assert len(e.value.state_history) == 2


def test_sct_reflection(dummy_checks):
    def diagnose(_):
        raise RuntimeError("This is not run")

    sct_dict = {"diagnose": diagnose, **dummy_checks}
    Ex = ExGen(sct_dict, None, strict=False)
    F = LazyChainStart(sct_dict)

    chain_part_1 = Ex().noop().child_state()
    assert str(chain_part_1) == "child_state()"

    chain_part_2 = F().diagnose().fail()
    assert str(chain_part_2) == "diagnose().fail()"

    chain_part_3 = F().noop()
    assert str(chain_part_3) == "noop()"

    chain_part_2_and_3 = chain_part_2 >> chain_part_3
    assert str(chain_part_2_and_3) == "diagnose().fail().noop()"

    chain = chain_part_1 >> chain_part_2_and_3
    assert str(chain) == str(chain_part_2_and_3)
    assert str(chain_part_1) == "child_state().diagnose().fail().noop()"

    assert str(Ex) == "Ex().noop().child_state().diagnose().fail().noop()"


def test_sct_reflection_lazy(dummy_checks):
    def diagnose(state):
        raise RuntimeError("This is not run")

    sct_dict = {"diagnose": diagnose, **dummy_checks}
    Ex = LazyChainStart(sct_dict)
    F = LazyChainStart(sct_dict)

    chain_part_1 = Ex().noop().child_state()
    assert str(chain_part_1) == "noop().child_state()"

    chain_part_2 = F().diagnose().fail()
    assert str(chain_part_2) == "diagnose().fail()"

    chain = chain_part_1 >> chain_part_2
    assert str(chain) == "noop().child_state().diagnose().fail()"
    assert str(chain_part_1) == "noop().child_state()"

    assert str(Ex) == "noop().child_state().diagnose().fail()"
    assert str(chain) == str(Ex)
