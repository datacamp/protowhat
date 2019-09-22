from contextlib import contextmanager
from typing import TYPE_CHECKING, List, Generator, Callable

from protowhat.Feedback import Feedback, FeedbackComponent

if TYPE_CHECKING:
    from protowhat.State import State


def check_history(state_history: List["State"]) -> Generator[str, None, None]:
    return (state.creator["type"] for state in state_history if state.creator)


def invert_failure(state: "State") -> bool:
    return "check_not" in check_history(state.state_history)


class Failure(Exception):
    throwing = False

    def __init__(self, feedback: Feedback, state_history: List["State"]):
        super().__init__(feedback)
        self.feedback = feedback
        self.state_history = state_history

    def __str__(self):
        # get_message can be expensive
        # TODO: check speed
        return self.feedback.get_message()

    @classmethod
    def from_message(cls, message: str) -> "Failure":
        return cls(Feedback(FeedbackComponent(message)), [])


class TestFail(Failure):
    pass


class InstructorError(Failure):
    pass


class SkipDebug(Exception):
    pass


@contextmanager
def debugger(state: "State", allow_failure: Callable[["State"], bool] = invert_failure):
    # TODO: skip debugging in production
    debugging = state.debug
    state.debug = True
    try:
        # if not state.force_diagnose:
        #     raise SkipDebug()
        yield
    except SkipDebug:
        pass
    except InstructorError as e:
        if not allow_failure(state):
            raise e

    state.debug = debugging


def _debug(state: "State", msg="", on_error=False, force=True):
    """
    This SCT function makes the SCT fail with a message containing debugging information
    and highlights the focus of the SCT at that point.

    To make the interruption behave like a student failure, use ``force=False``.
    """
    checks = check_history(state.state_history)

    feedback = ""
    if msg:
        feedback += msg + "\n"

    if checks:
        feedback += "SCT function state history: `{}`".format(" > ".join(checks))

    if state.reporter.tests:
        feedback += "\nLast test: `{}`".format(repr(state.reporter.tests[-1]))

    if on_error:
        # debug on next failure
        state.debug = True
        # or at the end (to prevent debug mode in production)
        state.reporter.fail = True
    else:
        # latest highlight added automatically
        failure_type = InstructorError if force else TestFail
        raise failure_type(state.get_feedback(FeedbackComponent(feedback)), state.state_history)

    return state
