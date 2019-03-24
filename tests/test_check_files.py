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
DUMMY_NODES = {'Expr': ast.Expr}

class ParseHey:
    ParseError = SyntaxError

    def parse(self, code, *args, **kwargs): return ast.parse(code)

def assert_equal_ast(a, b):
    assert ast.dump(a) == ast.dump(b)

@pytest.fixture(scope="function")
def tf():
    with NamedTemporaryFile() as tmp:
        tmp.file.write(b'1 + 1')
        tmp.file.flush()
        yield tmp

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
        ast_dispatcher = Dispatcher(ast.AST, DUMMY_NODES, ParseHey())
        )

def test_initial_state():
    State(student_code = {'script.py': '1'}, solution_code = {'script.py': '1'},
          reporter = Reporter(), pre_exercise_code = "",
          student_result = "", solution_result = "",
          student_conn = None, solution_conn = None,
          ast_dispatcher = Dispatcher(ast.AST, DUMMY_NODES, ParseHey()))

def test_check_file_use_fs(state, tf):
    state.solution_code = { tf.name: '3 + 3' }
    child = cf.check_file(state, tf.name, use_solution = True)
    assert child.student_code == '1 + 1'
    assert_equal_ast(child.student_ast, ast.parse(child.student_code))
    assert child.solution_code == '3 + 3'
    assert_equal_ast(child.solution_ast, ast.parse(child.solution_code))
    assert check_node(child, 'Expr', 0)

def test_check_file_use_fs_no_parse(state, tf):
    state.solution_code = { tf.name: '3 + 3' }
    child = cf.check_file(state, tf.name, parse = False)
    assert child.student_code == '1 + 1'
    assert child.student_ast is None
    assert child.solution_ast is None
    with pytest.raises(TypeError):
        assert check_node(child, 'Expr', 0)

def test_check_no_sol(state, tf):
    child = cf.check_file(state, tf.name, use_fs = True)
    assert child.solution_code is None

def test_check_dir(state):
    with TemporaryDirectory() as td:
        cf.has_dir(state, td)

@pytest.fixture(scope="function")
def code_state():
    return State(
        student_code = {'script1.py': '1 + 1', 'script2.py': '2 + 2'},
        solution_code = {'script1.py': '3 + 3', 'script2.py': '4 + 4'},
        reporter = Reporter(),
        # args below should be ignored
        pre_exercise_code = "NA",
        student_result = "", solution_result = "",
        student_conn = None, solution_conn = None,
        ast_dispatcher = Dispatcher(ast.AST, DUMMY_NODES, ParseHey())
        )

def test_check_file(code_state):
    child = cf.check_file(code_state, 'script1.py', use_fs=False, use_solution=True)
    assert child.student_code == "1 + 1"
    assert_equal_ast(child.student_ast, ast.parse(child.student_code))
    assert_equal_ast(child.solution_ast, ast.parse(child.solution_code))

def test_check_file_no_parse(code_state):
    child = cf.check_file(code_state, 'script1.py', use_fs=False, parse = False, use_solution=True)
    assert child.student_code == "1 + 1"
    assert child.student_ast is None
    assert child.solution_ast is None

