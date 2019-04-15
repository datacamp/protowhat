from typing import TypeVar, Generic, Union, List, Dict
from ast import NodeVisitor
import inspect
import importlib


class Selector(NodeVisitor):
    def __init__(self, target_cls, target_cls_name=None, strict=True, priority=None):
        self.target_cls = target_cls
        self.target_cls_name = target_cls_name
        self.strict = strict
        self.priority = target_cls._priority if priority is None else priority
        self.out = []

    def visit(self, node, head=False):
        if head:
            return super().visit(node)

        if self.is_match(node):
            self.out.append(node)
        if self.has_priority_over(node):
            return super().visit(node)

    def visit_list(self, lst):
        # this allows the root to be a list
        for item in lst:
            self.visit(item)

    def is_match(self, node):
        if self.strict:
            if type(node) is self.target_cls:
                return True
            else:
                return False
        else:
            if isinstance(node, self.target_cls) and (
                    self.target_cls_name is None or self.target_cls_name == node.__class__.__name__
            ):
                return True
            else:
                return False

    def has_priority_over(self, node):
        return self.priority > node._priority


T = TypeVar("T")


class DispatcherInterface(Generic[T]):
    def find(self, name: str, node: T, *args, **kwargs) -> Union[List[T], Dict[str, T]]:
        # todo: document signature, strategy kwarg (depth/breadth first)
        raise NotImplementedError

    def select(self, path: Union[str, List[Union[str, int]]], node: T) -> Union[T, List[T]]:
        raise NotImplementedError

    @staticmethod
    def _path_str_to_list(path):
        steps = path.split(".")

        def parse_int(x):
            try:
                return int(x)
            except ValueError:
                return x

        steps = map(parse_int, steps)
        return list(steps)

    def parse(self, code: str):
        raise NotImplementedError


class Dispatcher(DispatcherInterface):
    def __init__(self, node_cls, nodes=None, ast_mod=None, safe_parsing=True):
        """Wrapper to instantiate and use a Selector using node names."""
        self.node_cls = node_cls
        self.nodes = nodes or {}
        self.ast_mod = ast_mod
        self.safe_parsing = safe_parsing

        self.ParseError = getattr(
            self.ast_mod, "ParseError", type("ParseError", (Exception,), {})
        )

    def find(self, name, node, *args, **kwargs):
        if name in self.nodes:
            ast_cls = self.nodes[name]
            strict_selector = True
        else:
            ast_cls = self.node_cls
            strict_selector = False

        selector = Selector(
            ast_cls, target_cls_name=name, strict=strict_selector, *args, **kwargs
        )
        selector.visit(node, head=True)

        return selector.out

    def select(self, path, node):
        result = node
        if isinstance(path, str):
            path = self._path_str_to_list(path)
        for step in path:
            if isinstance(step, str):
                result = getattr(result, step, None)
            elif isinstance(step, int):
                result = result[step] if len(result) > step else None
            if result is None:
                break
        return result

    def parse(self, code):
        try:
            return self.ast_mod.parse(code, strict=True)
        except self.ParseError as e:
            if self.safe_parsing:
                return e
            else:
                raise e

    def describe(self, node, msg, field="", **kwargs):
        speaker = getattr(self.ast_mod, "speaker", None)

        if kwargs.get("index") is not None:
            phrase = "{} entry in the " if field else "{} "
            kwargs["index"] = phrase.format(get_ord(kwargs["index"] + 1))
        else:
            kwargs["index"] = ""

        if speaker:
            return self.ast_mod.speaker.describe(node, field=field, fmt=msg, **kwargs)

    @classmethod
    def from_module(cls, mod):
        if isinstance(mod, str):
            mod = importlib.import_module(mod)

        ast_nodes = getattr(mod, "nodes", None)
        if ast_nodes is None:
            ast_nodes = {
                k: v
                for k, v in vars(mod).items()
                if (inspect.isclass(v) and issubclass(v, mod.AstNode))
            }
        dispatcher = cls(mod.AstNode, nodes=ast_nodes, ast_mod=mod)
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
