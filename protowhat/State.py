from copy import copy
import inspect
from jinja2 import Template

class DummyParser:
    def __init__(self):
        self.ParseError = Exception

    def parse(self, *args, **kwargs): return self.ParseError()

class State:
    def __init__(self,
                 student_code,
                 solution_code,
                 pre_exercise_code,
                 student_conn,
                 solution_conn,
                 student_result,
                 solution_result,
                 reporter,
                 force_diagnose = False,
                 solution_ast = None,
                 student_ast = None,
                 fname = None,
                 ast_dispatcher = None,
                 history = tuple()):

        for k,v in locals().items():
            if k != 'self': setattr(self, k, v)

        if ast_dispatcher is None:
            self.ast_dispatcher = self.get_dispatcher()
        
        self.messages = []
        
        # Parse solution and student code
        # solution code raises an exception if can't be parsed
        if self.ast_dispatcher:
            if isinstance(self.solution_code, str) and self.solution_ast is None:
                self.solution_ast = self.ast_dispatcher.parse(self.solution_code)
            if isinstance(self.student_code, str) and self.student_ast is None:
                self.student_ast  = self.ast_dispatcher.parse(self.student_code)

        self._child_params = inspect.signature(State.__init__).parameters

    def get_dispatcher(self):
        return DummyParser()
        
    def get_ast_path(self):
        rev_checks = filter(lambda x: x['type'] in ['check_edge', 'check_node'], reversed(self.history))
        try:
            last = next(rev_checks)
            if last['type'] == 'check_node':
                # final check was for a node
                return self.ast_dispatcher.describe(last['node'],
                                                    index = last['kwargs']['index'],
                                                    msg = "{index}{node_name}")
            else:
                node = next(rev_checks)
                if node['type'] == 'check_node':
                    # checked for node, then for target, so can give rich description
                    return self.ast_dispatcher.describe(node['node'],
                                                        field = last['kwargs']['name'],
                                                        index = last['kwargs']['index'],
                                                        msg = "{index}{field_name} of the {node_name}")

        except StopIteration:
            return self.ast_dispatcher.describe(self.student_ast, "{node_name}")


    def do_test(self, *args, highlight=None, **kwargs):
        highlight = self.student_ast if highlight is None else highlight

        return self.reporter.do_test(*args, highlight=highlight, **kwargs)

    def to_child(self, append_message="", **kwargs):
        """Basic implementation of returning a child state"""

        bad_pars = set(kwargs) - set(self._child_params)
        if bad_pars:
            raise KeyError("Invalid init params for State: %s"% ", ".join(bad_pars))

        child = copy(self)
        for k, v in kwargs.items(): setattr(child, k, v)
        child.parent = self

        # append messages
        child.messages = [*self.messages, append_message]

        return child

    def build_message(self, tail_msg="", fmt_kwargs=None):

        if not fmt_kwargs: fmt_kwargs = {}
        out_list = []
        # add trailing message to msg list
        msgs = self.messages[:] + [{'msg': tail_msg, 'kwargs':fmt_kwargs}]

        for d in msgs:
            # don't bother appending if there is no message
            if not d or not d['msg']: continue
            out = Template(d['msg']).render(**d['kwargs'])
            out_list.append(out)

        return "".join(out_list)
