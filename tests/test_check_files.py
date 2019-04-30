import os
import pytest
from functools import partial
from tempfile import NamedTemporaryFile, TemporaryDirectory

from protowhat.selectors import Dispatcher
from protowhat.State import State
from protowhat.Reporter import Reporter
import ast

from protowhat.sct_syntax import F, Ex
from protowhat.checks import check_files as cf
from protowhat.checks.check_funcs import check_node

# TODO: selectors require a _priority attribute
#  this is a holdover from the sql ast modules
ast.Expr._priority = 0
DUMMY_NODES = {"Expr": ast.Expr}


class ParseHey:
    ParseError = SyntaxError

    def parse(self, code, *args, **kwargs):
        return ast.parse(code)


def assert_equal_ast(a, b):
    assert ast.dump(a) == ast.dump(b)


@pytest.fixture(scope="function")
def tf():
    with NamedTemporaryFile() as tmp:
        tmp.file.write(b"1 + 1")
        tmp.file.flush()
        yield tmp


@pytest.fixture(scope="function")
def state():
    return State(
        # only Reporter and Dispatcher are used
        student_code="",
        solution_code="",
        reporter=Reporter(),
        pre_exercise_code="",
        student_result="",
        solution_result="",
        student_conn=None,
        solution_conn=None,
        ast_dispatcher=Dispatcher(ast.AST, DUMMY_NODES, ParseHey()),
    )


def test_check_file(state, tf):
    child = cf.check_file(state, tf.name, solution_code="3 + 3")
    assert child.student_code == "1 + 1"
    assert_equal_ast(child.student_ast, ast.parse(child.student_code))
    assert child.solution_code == "3 + 3"
    assert_equal_ast(child.solution_ast, ast.parse(child.solution_code))
    assert check_node(child, "Expr", 0)


def test_check_file_no_parse(state, tf):
    child = cf.check_file(state, tf.name, parse=False)
    assert child.student_code == "1 + 1"
    assert child.student_ast is None
    assert child.solution_ast is None
    with pytest.raises(TypeError):
        assert check_node(child, "Expr", 0)


def test_check_no_sol(state, tf):
    child = cf.check_file(state, tf.name)
    assert child.solution_code is None


def test_check_dir(state):
    with TemporaryDirectory() as td:
        cf.has_dir(state, td)


def test_check_file_fchain(state, tf):
    f = F(attr_scts={"check_file": cf.check_file})
    Ex(state) >> f.check_file(tf.name)


def test_load_file(state, tf):
    assert "1 + 1" == cf.load_file(tf.name)

    filename = os.path.basename(os.path.normpath(tf.name))
    common_path = os.path.dirname(tf.name) + "/"

    load_file = partial(cf.load_file, prefix=common_path)
    assert "1 + 1" == load_file(filename)

    assert "1 + 1" == cf.load_file(filename, prefix=common_path)

    assert "1 + 1" == cf.load_file(filename, prefix=os.path.dirname(tf.name))
