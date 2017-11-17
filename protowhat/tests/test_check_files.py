import pytest
from tempfile import NamedTemporaryFile, TemporaryDirectory
from protowhat.selectors import Dispatcher
from protowhat.State import State
from protowhat.Reporter import Reporter
import ast

from protowhat.checks import check_files as cf
from protowhat.checks.check_funcs import check_node

# TODO: selectors require a _priority attribute and _get_field_names
#       this is a holdover from the sql ast modules
ast.Expr._priority = 0
ast.Module._get_field_names = lambda self: self._fields
ast.Expr._get_field_names = lambda self: self._fields
DUMMY_AST = ast.parse("1 + 1")
DUMMY_NODES = {'Expr': ast.Expr}

class ParseHey:
    ParseError = Exception

    def parse(self, *args, **kwargs): return DUMMY_AST

@pytest.fixture(scope="function")
def state():
    return State(
        student_code = "",
        solution_code = "",
        reporter = Reporter(),
        # args below should be ignored
        pre_exercise_code = "NA", 
        student_result = "", solution_result = "",
        student_conn = None, solution_conn = None,
        ast_dispatcher = Dispatcher(DUMMY_NODES, ParseHey())
        )

def test_check_file(state):
    with NamedTemporaryFile() as tf:
        tf.file.write(b'content')
        tf.file.flush()
        child = cf.check_file(state, tf.name)
        assert child.student_code == 'content'
        assert child.student_ast == DUMMY_AST
        assert check_node(child, 'Expr', 0)

def test_check_file_no_parse(state):
    with NamedTemporaryFile() as tf:
        tf.file.write(b'content')
        tf.file.flush()
        child = cf.check_file(state, tf.name, parse = False)
        assert child.student_code == 'content'
        assert child.student_ast is None
        with pytest.raises(TypeError):
            assert check_node(child, 'Expr', 0)

def test_check_dir(state):
    with TemporaryDirectory() as td:
        child = cf.test_dir(state, td)
