from protowhat.selectors import Selector

import pytest


def test_selector_standalone():
    # use python's builtin ast library
    from ast import Expr, Num
    Expr._priority = 0; Num._priority = 1
    node = Expr(value = Num(n = 1))

    sel = Selector(Num)
    sel.visit(node)
    assert isinstance(sel.out[0], Num)

    sel = Selector(Expr)
    sel.visit(node)
    assert isinstance(sel.out[0], Expr)

    sel = Selector(Expr)
    sel.visit(node, head=True)
    assert len(sel.out) == 0
