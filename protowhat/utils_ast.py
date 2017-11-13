from ast import AST

class AstNode(AST):
    _fields = []
    _priority = 1

    def _get_field_names(self):
        return self._fields
    
    def _get_text(self, text):
        raise NotImplemented()

    def _get_pos(self):
        raise NotImplemented()

    def __str__(self):
        els = [k for k in self._get_field_names() if getattr(self, k, None) is not None]
        return "{}: {}".format(self.__class__.__name__, ", ".join(els))

    def __repr__(self):
        field_reps = [(k, repr(getattr(self, k))) for k in self._get_field_names() if getattr(self, k, None) is not None]
        args = ", ".join("{} = {}".format(k, v) for k, v in field_reps)
        return "{}({})".format(self.__class__.__name__, args)


class AstModule:
    def __init__(self, parse, ParseError = Exception, classes = None, AstNode = AstNode):
        self.parse = parse
        self.classes = classes or {}
        self.ParseError = ParseError
        self.AstNode = AstNode

    # methods below are for creating an AstModule instance from a dictionary --

    def load(self, node):
        if not isinstance(node, dict): return node        # return primitives

        obj = self._instantiate_node(node['type'])

        data = node['data']
        obj._fields = tuple(data.keys())
        for field_name, attr in data.items():
            if isinstance(attr, (list, tuple)): child = [self.load(entry) for entry in attr]
            else: child = self.load(attr)
            setattr(obj, field_name, child)

        return obj


    def _instantiate_node(self, type_str):
        cls = self.classes.get(type_str, None)
        if not cls:
            cls = type(type_str, (AstNode,), {})
            self.classes[type_str] = cls

        return cls()

    @classmethod
    def from_parse_dict(cls, parse):
        obj = cls(None)
        obj.parse = lambda cmd, strict: obj.load(parse(cmd, strict))
        return obj
