from protowhat.checks.check_simple import has_chosen, success_msg, allow_errors
from protowhat.sct_syntax import EagerChain
from protowhat.State import State
from protowhat.Reporter import Reporter
from protowhat.failure import TestFail as TF
import pytest

sct_ctx = {
    "has_chosen": has_chosen,
    "success_msg": success_msg,
    "allow_errors": allow_errors,
}


def prepare_state(student_code):
    return State(
        student_code=student_code,
        reporter=Reporter(),
        # args below should be ignored
        solution_code="NA",
        pre_exercise_code="NA",
        solution_ast="NA",
        student_ast="NA",
        student_result=[],
        solution_result=[],
        student_conn=None,
        solution_conn=None,
    )


def test_has_chosen_alone_pass():
    state = prepare_state("selected_option = 1")
    has_chosen(state, 1, ["good", "bad"])


def test_has_chosen_alone_fail():
    state = prepare_state("selected_option = 2")
    with pytest.raises(TF):
        has_chosen(state, 1, ["good", "bad"])


def test_has_chosen_chain_pass():
    state = prepare_state("selected_option = 1")
    EagerChain(chainable_functions=sct_ctx, state=state).has_chosen(1, ["good", "bad"])
    assert state.reporter.build_final_payload()["message"] == "good"


def test_has_chosen_chain_fail():
    state = prepare_state("selected_option = 2")
    with pytest.raises(TF, match="bad"):
        EagerChain(chainable_functions=sct_ctx, state=state).has_chosen(
            1, ["good", "bad"]
        )


def test_success_msg_pass():
    state = prepare_state("")
    success_msg(state, "NEW SUCCESS MSG")

    sct_payload = state.reporter.build_final_payload()
    assert sct_payload["correct"] is True
    assert sct_payload["message"] == "NEW SUCCESS MSG"


def test_success_msg_pass_ex():
    state = prepare_state("")
    EagerChain(chainable_functions=sct_ctx, state=state).success_msg("NEW SUCCESS MSG")

    sct_payload = state.reporter.build_final_payload()
    assert sct_payload["correct"] is True
    assert sct_payload["message"] == "NEW SUCCESS MSG"


def test_no_allow_errors():
    state = prepare_state("")
    state.reporter.errors = ["Error"]
    EagerChain(chainable_functions=sct_ctx, state=state).success_msg("Good")
    sct_payload = state.reporter.build_final_payload()
    assert sct_payload["correct"] is False
    assert (
        sct_payload["message"] == "Your code generated an error. Fix it and try again!"
    )


def test_allow_errors():
    state = prepare_state("")
    state.reporter.errors = ["Error"]
    EagerChain(chainable_functions=sct_ctx, state=state).allow_errors().success_msg(
        "Good"
    )
    sct_payload = state.reporter.build_final_payload()
    assert sct_payload["correct"] is True
    assert sct_payload["message"] == "Good"
