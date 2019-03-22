from ast import AST


class AstNode(AST):
    _fields = ()
    _priority = 1

    def get_text(self, text):
        raise NotImplementedError()

    def get_position(self):
        raise NotImplementedError()

    def __str__(self):
        els = [k for k in self._fields if getattr(self, k, None) is not None]
        return "{}: {}".format(self.__class__.__name__, ", ".join(els))

    def __repr__(self):
        field_reps = [
            (k, repr(getattr(self, k)))
            for k in self._fields
            if getattr(self, k, None) is not None
        ]
        args = ", ".join("{} = {}".format(k, v) for k, v in field_reps)
        return "{}({})".format(self.__class__.__name__, args)


class ParseError(Exception):
    pass


class AstModule:
    """Subclasses can be used to instantiate a Dispatcher"""

    AstNode = AstNode
    ParseError = ParseError
    nodes = dict()
    speaker = None

    @classmethod
    def parse(cls, code, **kwargs):
        raise NotImplementedError("This method needs to be defined in a subclass.")

    # methods below are for updating an AstModule subclass based on data in the dump dictionary format --

    @classmethod
    def load(cls, node):
        if not isinstance(node, dict):
            return node  # return primitives

        type_str = node["type"]
        data = node["data"]
        obj = cls._instantiate_node(type_str, tuple(data.keys()))
        for field_name, value in data.items():
            if isinstance(value, (list, tuple)):
                child = [cls.load(entry) for entry in value]
            else:
                child = cls.load(value)
            setattr(obj, field_name, child)

        return obj

    @classmethod
    def _instantiate_node(cls, type_str, fields):
        # TODO: implement on AstNode (+ interface to get classes)
        node_cls = cls.nodes.get(type_str, None)
        if not node_cls:
            node_cls = type(type_str, (cls.AstNode,), {"_fields": fields})
            cls.nodes[type_str] = node_cls

        return node_cls()
