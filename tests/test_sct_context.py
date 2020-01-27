import pytest

from protowhat.State import State
from protowhat.sct_context import (
    get_checks_dict,
    create_sct_context,
    create_embed_state,
    create_embed_context,
    get_embed_chain_constructors,
)
from protowhat.sct_syntax import ChainStart, Chain, EagerChain, LazyChain, ExGen
from tests.helper import state, dummy_checks


state = pytest.fixture(state)
dummy_checks = pytest.fixture(dummy_checks)


def test_get_checks_dict_package():
    # Given
    from protowhat import checks

    # When
    sct_dict = get_checks_dict(checks)

    # Then
    assert isinstance(sct_dict, dict)
    assert sct_dict == {
        str(sct.__name__): sct
        for sct in [checks.get_bash_history, checks.update_bash_history_info, checks.prepare_validation]
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
    sct_ctx = create_sct_context(dummy_checks, state)

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
    Ex = ExGen(dummy_checks, state)
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
    Ex = ExGen(dummy_checks, state)
    assert Ex()._state == state

    # When
    EmbedEx, EmbedF = get_embed_chain_constructors("proto", Ex())

    # Then
    assert isinstance(EmbedEx(), EagerChain)
    assert isinstance(EmbedF(), LazyChain)
