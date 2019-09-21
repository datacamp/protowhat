from copy import copy

from protowhat.selectors import DispatcherInterface
from protowhat.Feedback import Feedback, FeedbackComponent
from protowhat.Test import Fail, Test
from protowhat.failure import TestFail, InstructorError, _debug


class DummyDispatcher(DispatcherInterface):
    def __init__(self):
        class ParseError(Exception):
            pass

        self.ParseError = ParseError

    def find(self, name, node, *args, **kwargs):
        return []

    def select(self, path: str, node):
        return None

    def parse(self, code):
        return self.ParseError()

    def describe(self, *args, **kwargs):
        return "code"


class State:
    def __init__(
        self,
        student_code,
        solution_code,
        pre_exercise_code,
        student_conn,
        solution_conn,
        student_result,
        solution_result,
        reporter,
        force_diagnose=False,
        highlight_offset=None,
        highlighting_disabled=False,
        feedback_context=None,
        creator=None,
        solution_ast=None,
        student_ast=None,
        ast_dispatcher=None,
    ):
        args = locals().copy()
        self.params = list()

        for k, v in args.items():
            if k != "self":
                self.params.append(k)
                setattr(self, k, v)

        if ast_dispatcher is None:
            self.ast_dispatcher = self.get_dispatcher()

        # Parse solution and student code
        # if possible, not done yet and wanted (ast arguments not False)
        if isinstance(self.solution_code, str) and self.solution_ast is None:
            self.solution_ast = self.parse(self.solution_code, test=False)
        if isinstance(self.student_code, str) and self.student_ast is None:
            self.student_ast = self.parse(self.student_code)

    def parse(self, text, test=True):
        result = None
        if self.ast_dispatcher:
            try:
                result = self.ast_dispatcher.parse(text)
            except self.ast_dispatcher.ParseError as e:
                if test:
                    self.report(e.message)
                else:
                    raise InstructorError.from_message(
                        "Something went wrong when parsing PEC or solution code: %s"
                        % str(e)
                    )

        return result

    def get_dispatcher(self):
        return DummyDispatcher()

    @property
    def parent_state(self):
        if self.creator is not None:
            return self.creator["args"]["state"]

    @property
    def is_root(self):
        return self.parent_state is None

    @property
    def state_history(self):
        return getattr(self.parent_state, "state_history", []) + [self]

    def get_ast_path(self):
        rev_checks = filter(
            lambda x: x.creator is not None
            and x.creator["type"] in ["check_edge", "check_node"],
            reversed(self.state_history),
        )
        try:
            last = next(rev_checks)
            if last.creator["type"] == "check_node":
                # final check was for a node
                return self.ast_dispatcher.describe(
                    last.student_ast,
                    index=last.creator["args"]["index"],
                    msg="{index}{node_name}",
                )
            else:
                node = next(rev_checks)
                if node.creator["type"] == "check_node":
                    # checked for node, then for target, so can give rich description
                    return self.ast_dispatcher.describe(
                        node.student_ast,
                        field=last.creator["args"]["name"],
                        index=last.creator["args"]["index"],
                        msg="{index}{field_name} of the {node_name}",
                    )

        except StopIteration:
            return self.ast_dispatcher.describe(self.student_ast, "{node_name}")

    def report(self, feedback: str, kwargs=None, append=True):
        test_feedback = FeedbackComponent(feedback, kwargs, append)
        test = Fail(test_feedback)

        return self.do_test(test)

    def do_test(self, test: Test):
        result, test_feedback = self.reporter.do_test(test)
        if result is False:
            if getattr(self, "debug", False):
                _debug(self.to_child(test_feedback), "Debug on error:")

            raise TestFail(self.get_feedback(test_feedback), self.state_history)
        return result, test_feedback

    def do_tests(self, tests):
        return [self.do_test(test) for test in tests]

    def get_feedback(self, conclusion):
        if self.student_ast == self.state_history[0].student_ast:
            highlighting_disabled = True
        else:
            highlighting_disabled = self.highlighting_disabled

        return Feedback(
            conclusion,
            [state.feedback_context for state in self.state_history if state.feedback_context],
            getattr(self, "highlight", self.student_ast),
            getattr(self, "path", None),
            highlighting_disabled,
            self.highlight_offset,
        )

    def to_child(self, append_message="", **kwargs):
        """Basic implementation of returning a child state"""

        bad_pars = set(kwargs) - set(self.params)
        if bad_pars:
            raise ValueError("Invalid init params for State: %s" % ", ".join(bad_pars))

        if not isinstance(append_message, dict):
            append_message = {"msg": append_message, "kwargs": {}}
        kwargs["message"] = append_message

        child = copy(self)
        for k, v in kwargs.items():
            setattr(child, k, v)

        return child
