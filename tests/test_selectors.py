import pytest

from protowhat.selectors import Selector, get_ord, DispatcherInterface, Dispatcher

# use python's builtin ast library
from ast import AST, Expr, Num

Num._priority = 1


@pytest.fixture
def node():
    return Expr(value=Num(n=1))


def test_selector_standalone(node):
    sel = Selector(Num)
    sel.visit(node)
    assert isinstance(sel.out[0], Num)

    sel = Selector(Expr)
    sel.visit(node)
    assert isinstance(sel.out[0], Expr)

    sel = Selector(Expr)
    sel.visit(node, head=True)
    assert len(sel.out) == 0


@pytest.mark.parametrize(
    "path_str, path_list",
    [
        ("", []),
        ("a", ["a"]),
        ("a.", ["a"]),
        ("1", [1]),
        ("a.0", ["a", 0]),
        ("a.b.c", ["a", "b", "c"]),
        ("a.2.c", ["a", 2, "c"]),
    ],
)
def test_dispatcher_path_str_to_list(path_str, path_list):
    assert DispatcherInterface._path_str_to_list(path_str) == path_list


def test_dispatcher_find(node):
    assert isinstance(Dispatcher(AST).find("Num", node)[0], Num)


def test_dispatcher_select(node):
    assert isinstance(Dispatcher(AST).select("value", node), Num)


@pytest.mark.parametrize("num, ord", [(1, "first"), (12, "12th"), (23, "23rd")])
def test_ord(num, ord):
    assert get_ord(num) == ord
