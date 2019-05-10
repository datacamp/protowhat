from copy import copy
from jinja2 import Template

from protowhat.selectors import DispatcherInterface
from protowhat.Feedback import Feedback, InstructorError
from protowhat.Test import Fail, Test, TestFail
from protowhat.utils import _debug


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
        highlighting_disabled=False,
        messages=None,
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

        self.messages = messages if messages else []

        if ast_dispatcher is None:
            self.ast_dispatcher = self.get_dispatcher()

        # Parse solution and student code
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
                    raise InstructorError(
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
    def state_history(self):
        history = [self]
        while history[-1].parent_state is not None:
            history.append(history[-1].parent_state)

        return list(reversed(history))

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

    def report(self, feedback: str):
        test_feedback = Feedback(feedback, self)
        if test_feedback.highlight is None and self is not getattr(
            self, "root_state", None
        ):
            test_feedback.highlight = self.student_ast
        test = Fail(test_feedback)

        return self.do_test(test)

    def do_test(self, test: Test):
        result, feedback = self.reporter.do_test(test)
        if result is False:
            if getattr(self, "debug", False):
                setattr(self, "debug", False)  # prevent loop
                _debug(self)
            raise TestFail(feedback, self.reporter.build_failed_payload(feedback))
        return result, feedback

    def do_tests(self, tests):
        return [self.do_test(test) for test in tests]

    def to_child(self, append_message="", **kwargs):
        """Basic implementation of returning a child state"""

        bad_pars = set(kwargs) - set(self.params)
        if bad_pars:
            raise KeyError("Invalid init params for State: %s" % ", ".join(bad_pars))

        child = copy(self)
        for k, v in kwargs.items():
            setattr(child, k, v)

        # append messages
        if not isinstance(append_message, dict):
            append_message = {"msg": append_message, "kwargs": {}}
        child.messages = [*self.messages, append_message]

        return child

    def build_message(self, tail_msg="", fmt_kwargs=None, append=True):
        if not fmt_kwargs:
            fmt_kwargs = {}
        out_list = []
        # add trailing message to msg list
        msgs = self.messages[:] + [{"msg": tail_msg, "kwargs": fmt_kwargs}]

        # format messages in list, by iterating over previous, current, and next message
        for prev_d, d, next_d in zip([{}, *msgs[:-1]], msgs, [*msgs[1:], {}]):
            tmp_kwargs = {
                "parent": prev_d.get("kwargs"),
                "child": next_d.get("kwargs"),
                "this": d["kwargs"],
                **d["kwargs"],
            }
            # don't bother appending if there is no message
            if not d or not d["msg"]:
                continue
            # TODO: rendering is slow in tests (40% of test time)
            out = Template(d["msg"].replace("__JINJA__:", "")).render(tmp_kwargs)
            out_list.append(out)

        # if highlighting info is available, don't put all expand messages
        if getattr(self, "highlight", None) and not self.highlighting_disabled:
            out_list = out_list[-3:]

        if append:
            return "".join(out_list)
        else:
            return out_list[-1]
