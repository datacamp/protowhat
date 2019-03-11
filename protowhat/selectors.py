from ast import NodeVisitor, AST
import inspect
import importlib


class Selector(NodeVisitor):
    def __init__(self, src, src_name=None, strict=True, priority=None):
        self.src = src
        self.src_name = src_name
        self.strict = strict
        self.priority = src._priority if priority is None else priority
        self.out = []

    def visit(self, node, head=False):
        if head:
            return super().visit(node)

        if self.is_match(node):
            self.out.append(node)
        if self.has_priority_over(node):
            return super().visit(node)

    def visit_list(self, lst):
        for item in lst:
            self.visit(item)

    def is_match(self, node):
        if self.strict:
            if type(node) is self.src:
                return True
            else:
                return False
        else:
            if isinstance(node, self.src) and (
                self.src_name is None or self.src_name == node.__class__.__name__
            ):
                return True
            else:
                return False

    def has_priority_over(self, node):
        return self.priority > node._priority


class Dispatcher:
    def __init__(self, node_cls, nodes=None, ast=None, safe_parsing=True):
        """Wrapper to instantiate and use a Selector using node names."""
        self.node_cls = node_cls
        self.nodes = nodes or []
        self.ast = ast
        self.safe_parsing = safe_parsing

        self.ParseError = getattr(self.ast, "ParseError", None)

    def __call__(self, name, index, node, *args, **kwargs):
        if name in self.nodes:
            ast_cls = self.nodes[name]
            strict_selector = True
        else:
            ast_cls = self.node_cls
            strict_selector = False

        selector = Selector(
            ast_cls, src_name=name, strict=strict_selector, *args, **kwargs
        )
        selector.visit(node, head=True)

        return selector.out[index]

    def parse(self, code):
        try:
            return self.ast.parse(code, strict=True)
        except self.ParseError as e:
            if self.safe_parsing:
                return e
            else:
                raise e

    def describe(self, node, msg, field="", **kwargs):
        speaker = getattr(self.ast, "speaker", None)

        if kwargs.get("index") is not None:
            phrase = "{} entry in the " if field else "{} "
            kwargs["index"] = phrase.format(get_ord(kwargs["index"] + 1))
        else:
            kwargs["index"] = ""

        if speaker:
            return self.ast.speaker.describe(node, field=field, fmt=msg, **kwargs)

    @classmethod
    def from_module(cls, mod):
        if isinstance(mod, str):
            mod = importlib.import_module(mod)

        ast_nodes = {
            k: v
            for k, v in vars(mod).items()
            if (inspect.isclass(v) and issubclass(v, mod.AstNode))
        }
        dispatcher = cls(mod.AstNode, nodes=ast_nodes, ast=mod)
        return dispatcher


def get_ord(num):
    assert num != 0, "use strictly positive numbers in get_ord()"
    nums = {
        1: "first",
        2: "second",
        3: "third",
        4: "fourth",
        5: "fifth",
        6: "sixth",
        7: "seventh",
        8: "eight",
        9: "ninth",
        10: "tenth",
    }
    if num in nums:
        return nums[num]
    else:
        return "%dth" % num
