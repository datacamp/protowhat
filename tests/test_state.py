from tests.helper import state


def test_is_root():
    first_state = state()
    assert first_state.is_root

    second_state = state()
    second_state.creator = {"type": "check_something", "args": {"state": first_state}}
    assert not second_state.is_root
