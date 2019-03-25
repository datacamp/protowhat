from copy import copy
import inspect
from jinja2 import Template

from protowhat.selectors import DispatcherInterface
from protowhat.Feedback import Feedback, InstructorError
from protowhat.Test import Fail, Test


class DummyDispatcher(DispatcherInterface):
    def __init__(self):
        class ParseError(Exception):
            pass

        self.ParseError = ParseError

    def __call__(self, name, node, *args, **kwargs):
        return []

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
        solution_ast=None,
        student_ast=None,
        fname=None,
        ast_dispatcher=None,
        history=tuple(),
    ):

        for k, v in locals().items():
            if k != "self":
                setattr(self, k, v)

        if ast_dispatcher is None:
            self.ast_dispatcher = self.get_dispatcher()

        self.messages = []

        # Parse solution and student code
        if isinstance(self.solution_code, str) and self.solution_ast is None:
            self.solution_ast = self.parse(self.solution_code, test=False)
        if isinstance(self.student_code, str) and self.student_ast is None:
            self.student_ast = self.parse(self.student_code)

        self._child_params = inspect.signature(State.__init__).parameters

    def parse(self, text, test=True):
        result = None
        if self.ast_dispatcher:
            try:
                result = self.ast_dispatcher.parse(text)
            except self.ast_dispatcher.ParseError as e:
                if test:
                    self.report(Feedback(e.message))
                else:
                    raise InstructorError(
                        "Something went wrong when parsing PEC or solution code: %s"
                        % str(e)
                    )

        return result

    def get_dispatcher(self):
        return DummyDispatcher()

    def get_ast_path(self):
        rev_checks = filter(
            lambda x: x["type"] in ["check_edge", "check_node"], reversed(self.history)
        )
        try:
            last = next(rev_checks)
            if last["type"] == "check_node":
                # final check was for a node
                return self.ast_dispatcher.describe(
                    last["node"],
                    index=last["kwargs"]["index"],
                    msg="{index}{node_name}",
                )
            else:
                node = next(rev_checks)
                if node["type"] == "check_node":
                    # checked for node, then for target, so can give rich description
                    return self.ast_dispatcher.describe(
                        node["node"],
                        field=last["kwargs"]["name"],
                        index=last["kwargs"]["index"],
                        msg="{index}{field_name} of the {node_name}",
                    )

        except StopIteration:
            return self.ast_dispatcher.describe(self.student_ast, "{node_name}")

    def report(self, feedback: Feedback):
        if feedback.highlight is None and self is not getattr(self, "root_state", None):
            feedback.highlight = self.student_ast
        test = Fail(feedback)

        return self.do_test(test)

    def do_test(self, test: Test):
        return self.reporter.do_test(test)

    def to_child(self, append_message="", **kwargs):
        """Basic implementation of returning a child state"""

        bad_pars = set(kwargs) - set(self._child_params)
        if bad_pars:
            raise KeyError("Invalid init params for State: %s" % ", ".join(bad_pars))

        child = copy(self)
        for k, v in kwargs.items():
            setattr(child, k, v)
        child.parent = self

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
