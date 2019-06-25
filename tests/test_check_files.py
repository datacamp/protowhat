import os
import ast
from pathlib import Path

import pytest

from functools import partial
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest.mock import patch, mock_open

from protowhat.Test import TestFail as TF
from protowhat.selectors import Dispatcher
from protowhat.State import State
from protowhat.Reporter import Reporter

from protowhat.sct_syntax import F, Ex
from protowhat.checks import check_files as cf
from protowhat.checks.check_funcs import check_node, has_code

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


@pytest.fixture
def temp_file_sum():
    with NamedTemporaryFile() as tmp:
        tmp.file.write(b"1 + 1")
        tmp.file.flush()
        yield tmp


@pytest.fixture
def temp_file_unicode():
    with NamedTemporaryFile() as tmp:
        tmp.file.write("Hervé".encode("utf-8"))
        tmp.file.flush()
        yield tmp


@pytest.fixture(params=["temp_file_sum", "temp_file_unicode"])
def temp_file(request):
    return request.getfuncargvalue(request.param)


@pytest.fixture
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


def test_get_file_content_simple(temp_file_sum):
    content = cf.get_file_content(temp_file_sum.name)
    assert content == "1 + 1"


def test_get_file_content_unicode(temp_file_unicode):
    content = cf.get_file_content(temp_file_unicode.name)
    assert content == "Hervé"


def test_get_file_content_missing():
    content = cf.get_file_content("foo")
    assert content is None


def test_get_file_content_error(temp_file_sum):
    with patch("io.open") as mock_file:
        mock_file.side_effect = IOError()
        content = cf.get_file_content(temp_file_sum.name)
        assert content is None


def test_check_file(state, temp_file_sum):
    child = cf.check_file(state, temp_file_sum.name, solution_code="3 + 3")
    assert child.student_code == "1 + 1"
    assert_equal_ast(child.student_ast, ast.parse(child.student_code))

    assert child.solution_code == "3 + 3"
    assert_equal_ast(child.solution_ast, ast.parse(child.solution_code))

    assert child.path == Path(temp_file_sum.name)
    assert child.path.parent == Path(temp_file_sum.name).parent
    assert child.path.name == Path(temp_file_sum.name).name

    grandchild = check_node(child, "Expr", 0)
    assert grandchild.path == child.path


def test_check_file_no_parse(state, temp_file_sum):
    child = cf.check_file(state, temp_file_sum.name, parse=False)
    has_code(child, "1 + 1", fixed=True)
    assert child.student_code == "1 + 1"
    assert child.student_ast is False
    assert child.solution_ast is None  # no solution code is provided
    with pytest.raises(TypeError):
        assert check_node(child, "Expr", 0)


def test_check_no_sol(state, temp_file):
    child = cf.check_file(state, temp_file.name)
    assert child.solution_code is None


def test_check_file_missing(state):
    with pytest.raises(TF) as exception:
        cf.check_file(state, "foo")
    assert "Did you create the file" in str(exception)


def test_check_file_dir(state):
    with pytest.raises(TF) as exception:
        with TemporaryDirectory() as td:
            cf.check_file(state, td)
    assert "found a directory" in str(exception)


def test_check_dir(state):
    with TemporaryDirectory() as td:
        cf.has_dir(state, td)


def test_missing_check_dir(state):
    with pytest.raises(TF) as exception:
        cf.has_dir(state, "foo")
    assert "Did you create a directory" in str(exception)


def test_check_file_fchain(state, temp_file):
    f = F(attr_scts={"check_file": cf.check_file})
    Ex(state) >> f.check_file(temp_file.name)


def test_load_file(state, temp_file):
    expected_content = cf.get_file_content(temp_file.name)
    assert expected_content == cf.load_file(temp_file.name)

    filename = os.path.basename(os.path.normpath(temp_file.name))
    common_path = os.path.dirname(temp_file.name)

    load_file = partial(cf.load_file, prefix=common_path)
    assert expected_content == load_file(filename)

    assert expected_content == cf.load_file(filename, prefix=common_path)
    assert expected_content == cf.load_file(filename, prefix=common_path + "/")
