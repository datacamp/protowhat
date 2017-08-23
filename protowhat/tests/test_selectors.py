from protowhat.selectors import Selector, Dispatcher
from protowhat.State import State
import importlib
from protowhat.Reporter import Reporter
from protowhat.Test import TestFail as TF
import pytest

@pytest.mark.xfail
def test_selector_standalone():
    from ast import Expr, Num        # use python's builtin ast library
    Expr._priority = 0; Num._priority = 1
    node = Expr(value = Num(n = 1))
    sel = Selector(Num)
    sel.visit(node)
    assert isinstance(sel.out[0], Num)
