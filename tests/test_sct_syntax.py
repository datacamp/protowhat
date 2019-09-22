import pytest

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
    create_embed_state,
    create_embed_context,
    get_embed_chain_constructors,
    ChainStart,
    Chain,
)

Ex = ExGen(None)
state_dec = state_dec_gen(State)

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


def test_get_checks_dict_package():
    # Given
    from protowhat import checks

    # When
    sct_dict = get_checks_dict(checks)

    # Then
    assert isinstance(sct_dict, dict)
    assert sct_dict == {
        str(sct.__name__): sct
        for sct in [checks.get_bash_history, checks.update_bash_history_info]
    }  # other checks not exported in init


def test_get_checks_dict_module():
    # Given
    from protowhat.checks import check_simple

    # When
    sct_dict = get_checks_dict(check_simple)

    # Then
    assert len(sct_dict) == 3
    assert sct_dict["has_chosen"] == check_simple.has_chosen
    assert sct_dict["success_msg"] == check_simple.success_msg


def test_create_sct_context(state, dummy_checks):
    # When
    sct_ctx = create_sct_context(State, dummy_checks, state)

    # Then
    assert "state_dec" in sct_ctx

    for check in dummy_checks:
        assert check in sct_ctx
        assert callable(sct_ctx[check])

    for chain in ["Ex", "F"]:
        assert chain in sct_ctx
        assert isinstance(sct_ctx[chain], ChainStart)
        assert isinstance(sct_ctx[chain](), Chain)
        assert isinstance(sct_ctx[chain]()(state), State)
        for check in dummy_checks:
            assert getattr(sct_ctx[chain](), check)

    assert isinstance(sct_ctx["Ex"](), EagerChain)
    assert isinstance(sct_ctx["F"](), LazyChain)


def test_create_embed_state(state):
    # Given
    state.debug = True
    assert state.solution_result == {}

    class XState(State):
        def __init__(self, *args, custom=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.custom = custom

    def derive_custom_state_args(parent_state):
        assert parent_state == state
        return {
            "student_code": "override",
            "custom": "Xstate property",
            "highlight_offset": {"test": "nonsense highlight"},
        }

    # When
    embed_state = create_embed_state(XState, state, derive_custom_state_args)

    # Then
    assert isinstance(embed_state, XState)
    assert not getattr(embed_state, "debug")  # TODO
    assert embed_state.student_code == "override"
    assert embed_state.custom == "Xstate property"
    assert embed_state.reporter.runner == state.reporter
    assert embed_state.highlight_offset == {"test": "nonsense highlight"}
    assert embed_state.creator == {"type": "embed", "args": {"state": state}}


def test_create_embed_context(state, dummy_checks):
    # Given
    Ex = ExGen(state, dummy_checks)
    assert Ex()._state == state

    def derive_custom_state_args(parent_state):
        assert parent_state == state
        return {"student_code": "override"}

    # When
    embed_context = create_embed_context(
        "proto", Ex(), derive_custom_state_args=derive_custom_state_args,
    )

    # Then
    assert isinstance(embed_context["get_bash_history"](), LazyChain)
    assert isinstance(embed_context["F"]().get_bash_history(), LazyChain)

    embed_state = embed_context["Ex"].root_state
    assert isinstance(embed_state, State)
    assert embed_state.student_code == "override"
    assert embed_state.reporter.runner == state.reporter
    assert embed_state.creator == {"type": "embed", "args": {"state": state}}


def test_get_embed_chain_constructors(state, dummy_checks):
    # Given
    Ex = ExGen(state, dummy_checks)
    assert Ex()._state == state

    # When
    EmbedEx, EmbedF = get_embed_chain_constructors("proto", Ex())

    # Then
    assert isinstance(EmbedEx(), EagerChain)
    assert isinstance(EmbedF(), LazyChain)


def test_state_linking_root_creator(state):
    def diagnose(end_state):
        assert end_state.creator is None

    LazyChain.register_functions({"diagnose": diagnose})
    Ex(state) >> LazyChain().diagnose()


def test_state_linking_root_creator_noop(state, dummy_checks):
    def diagnose(end_state):
        assert end_state.creator is None

    LazyChain.register_functions({"diagnose": diagnose, **dummy_checks})
    TestEx = ExGen(state)
    TestEx().noop() >> LazyChain().diagnose()


def test_state_linking_root_creator_child_state(state, dummy_checks):
    def diagnose(end_state):
        assert end_state != state
        assert end_state.parent_state is state
        assert len(end_state.state_history) == 2
        assert state == end_state.state_history[0]
        assert end_state == end_state.state_history[1]

    LazyChain.register_functions({"diagnose": diagnose, **dummy_checks})
    TestEx = ExGen(state)
    TestEx().child_state() >> LazyChain().diagnose()


def test_sct_reflection(dummy_checks):
    def diagnose(state):
        raise RuntimeError("This is not run")

    LazyChain.register_functions({"diagnose": diagnose, **dummy_checks})
    Ex = ExGen(None, strict=False)

    chain_part_1 = Ex().noop().child_state()
    assert str(chain_part_1) == "child_state()"

    chain_part_2 = LazyChain().diagnose().fail()
    assert str(chain_part_2) == "diagnose().fail()"

    chain_part_3 = LazyChain().noop()
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

    LazyChain.register_functions({"diagnose": diagnose, **dummy_checks})
    Ex = LazyChainStart()

    chain_part_1 = Ex().noop().child_state()
    assert str(chain_part_1) == "noop().child_state()"

    chain_part_2 = LazyChain().diagnose().fail()
    assert str(chain_part_2) == "diagnose().fail()"

    chain = chain_part_1 >> chain_part_2
    assert str(chain) == "noop().child_state().diagnose().fail()"
    assert str(chain_part_1) == "noop().child_state()"

    assert str(Ex) == "noop().child_state().diagnose().fail()"
    assert str(chain) == str(Ex)
