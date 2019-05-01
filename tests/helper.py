from protowhat.Reporter import Reporter
from protowhat.State import State
from protowhat.Test import Test


class Success(Test):
    def test(self):
        self.result = True


def state():
    return State("student_code", "", "", None, None, {}, {}, Reporter())


def noop(state):
    return state


def child_state(state):
    return state.to_child()


def dummy_checks():
    return {"noop": noop, "child_state": child_state}
