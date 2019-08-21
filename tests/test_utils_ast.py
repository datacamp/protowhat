import bashlex
import bashlex.errors
from asttokens import ASTTokens

from protowhat import utils_ast
from collections import OrderedDict

from protowhat.utils_ast import get_blanks, find_range_ast_path, select_path


def dump_bash(obj, parent_cls=bashlex.ast.node, v=False):
    """Takes a bashlex AST and returns it structured as a dictionary.

    Each dictionary entry has two fields:
        type: the name of the AST node
        data: a dictionary mapping field_name: attribute node (or list of nodes)

    """
    # pull element out of single entry lists
    if isinstance(obj, (list, tuple)) and len(obj) == 1:
        obj = obj[0]
    # dump to dict
    if isinstance(obj, parent_cls):
        if obj.kind in ["word", "reservedword"] and not v:
            return obj.word
        fields = OrderedDict()
        for name in [el for el in obj.__dict__.keys() if el not in ("kind", "pos")]:
            attr = getattr(obj, name)
            if isinstance(attr, parent_cls):
                fields[name] = dump_bash(attr, parent_cls, v)
            elif isinstance(attr, list) and len(attr) == 0:
                continue
            elif isinstance(attr, list):
                fields[name] = [dump_bash(x, parent_cls, v) for x in attr]
            else:
                fields[name] = attr
        return {"type": obj.kind, "data": fields}
    elif isinstance(obj, list):
        return [dump_bash(x, parent_cls, v) for x in obj]
    else:
        raise Exception("received non-node object?")


def test_AstModule_load():
    cmd = """for ii in {1..10}; do echo $ii; done"""

    class Bashlex(utils_ast.AstModule):
        ParseError = bashlex.errors.ParsingError

        def parse(self, code, **kwargs):
            # dump parse tree and
            # use it to dynamically update this AstModule
            return self.load(dump_bash(bashlex.parse(code)))

    parser = Bashlex()
    tree = parser.parse(cmd)

    assert type(tree.list[0]) == parser.nodes["for"]


def test_select_blank():
    solution = \
"""
def a():
    return b + c
"""
    sample = \
"""
def a():
    return ____ + c
"""
    blanks = get_blanks(solution, sample)
    tree = ASTTokens(solution, parse=True).tree
    ast_path = find_range_ast_path(blanks[0], tree)
    node = select_path(tree, ast_path)
    assert node
