from ast import AST, iter_fields
from bisect import bisect_left
from collections import OrderedDict
from difflib import SequenceMatcher
from itertools import chain, accumulate
from typing import List, Tuple, Dict

from protowhat.Feedback import InstructorError


class DumpConfig:
    def __init__(
        self,
        is_node=lambda node: isinstance(node, AST),
        node_type=lambda node: node.__class__.__name__,
        fields_iter=lambda node: node._fields,
        field_val=lambda node, field: getattr(node, field, None),
        is_list=lambda node: isinstance(node, list),
        list_iter=id,
        leaf_val=id,
    ):
        """
        Configuration to convert a node tree to the dump format

        The default configuration can be used to dump a tree of AstNodes
        """
        self.is_node = is_node
        self.node_type = node_type
        self.fields_iter = fields_iter
        self.field_val = field_val
        self.is_list = is_list
        self.list_iter = list_iter
        self.leaf_val = leaf_val


def dump(node, config):
    """
    Convert a node tree to a simple nested dict

    All steps in this conversion are configurable using DumpConfig

    dump dictionary node: {"type": str, "data": dict}
    """
    if config.is_node(node):
        fields = OrderedDict()
        for name in config.fields_iter(node):
            attr = config.field_val(node, name)
            if attr is not None:
                fields[name] = dump(attr, config)
        return {"type": config.node_type(node), "data": fields}
    elif config.is_list(node):
        return [dump(x, config) for x in config.list_iter(node)]
    else:
        return config.leaf_val(node)


class AstNode(AST):
    _fields = ()
    _priority = 1

    def get_text(self, full_text=None):
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

    @classmethod
    def dump(cls, tree):
        return dump(tree, DumpConfig())

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


# Zoom in on blank

# - focus SCT work on exercise focus
# - can zoom on any part of the AST, from any wrapping part
# - implementation can be made more dynamic without SCT rewrite

# - common definition of positions important
# - unique (& stable) identifier for blanks

# - sample code / blanks info needed
#   - send sample to backend -> sample to blanks
#   - transform solution & solution to blanks -> send blanks
#   -> blanks in SCT context
#   - helper from solution text match + index to range
# - what if different blanks for different proficiency?
#   - select until 'outer' blank and write SCT from there
#   - selects are chainable
#   - reuse lazychain for inner part


# common


class StringPosition:
    def __init__(self, line, column):
        self.line = line
        self.column = column


class StringRange:
    def __init__(self, start: StringPosition, end: StringPosition):
        self.start = start
        self.end = end

    def __eq__(self, other):
        return

    def __contains__(self, item: "StringRange"):
        return self.start <= item.start and item.end <= self.end


# extract sample info

# working with offset ranges?
# working with utf-8
# blanks.append((solution_start, solution_end))
def get_blanks(
    solution_code: str, sample_code: str, pattern: str = "____", strict=True
):
    blanks = []
    line_offsets = get_line_offsets(solution_code)
    diff = SequenceMatcher(lambda x: x in " \t\r\n", solution_code, sample_code)
    for (
        tag,
        solution_start,
        solution_end,
        sample_start,
        sample_end,
    ) in diff.get_opcodes():
        if tag == "replace":
            if strict and sample_code[sample_start:sample_end] != pattern:
                raise ValueError(
                    "The solution and sample have an unexpected difference: {} > {} ".format(
                        solution_code[solution_start:solution_end],
                        sample_code[sample_start:sample_end],
                    )
                )
            start_position = StringPosition(
                *offset_to_position(solution_start, line_offsets)
            )
            end_position = StringPosition(
                *offset_to_position(solution_end, line_offsets)
            )
            blanks.append(StringRange(start_position, end_position))

    return blanks


def get_line_offsets(code: str) -> List[int]:
    return list(accumulate(chain([0], map(len, code.splitlines(keepends=True)))))


def offset_to_position(offset: int, line_offsets: List[int]) -> Tuple[int, int]:
    line = bisect_left(line_offsets, offset)
    # index of line is the element before the insertion point
    column = offset - line_offsets[line - 1]
    return line, column


# data conversion


def range_to_mapping(string_range: StringRange) -> Dict[str, int]:
    return {
        "line_start": string_range.start.line,
        "column_start": string_range.start.column,
        "line_end": string_range.end.line,
        "column_end": string_range.end.column,
    }


def mapping_to_range(mapping: dict) -> StringRange:
    return StringRange(
        StringPosition(mapping["line_start"], mapping["column_start"]),
        StringPosition(mapping["line_end"], mapping["column_end"]),
    )


# Python specific

# extract solution info


def find_range_ast_path(code_range: StringRange, node, strict=True):
    node_name = node.__class__.__name__
    node_field = None
    node_field_index = None
    nested_path = None
    for field, value in iter_fields(node):
        if isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, AST) and code_range in node_range(item):
                    node_field = field
                    node_field_index = index
                    nested_path = find_range_ast_path(code_range, item)
                    break
        elif isinstance(value, AST) and code_range in node_range(value):
            node_field = field
            nested_path = find_range_ast_path(code_range, value)
        if node_field:
            break

    if strict and not nested_path:
        # non-strict can be used to get best node for cursor position or selection
        if code_range != node_range(node_name):
            raise ValueError("Invalid range")

    return [(node_name, node_field, node_field_index)] + (nested_path or [])


def node_range(node) -> StringRange:
    if hasattr(node, "first_token") and hasattr(node, "last_token"):
        return StringRange(node.first_token.start, node.last_token.end)
    else:
        return StringRange(StringPosition(-1, -1), StringPosition(-1, -1))


# select subtree


def select_path(tree, path, strict=False):
    result = tree
    missing_path = []
    for index, item in enumerate(path):
        node_name, field_name, index = item
        if result.__class__.__name__ is node_name:
            if field_name:
                result = getattr(result, field_name)
                if index is not None:
                    result = result[index]
        else:
            if strict:
                raise ValueError("Path not found in tree")
            else:
                missing_path = path[index:]

    return result, missing_path


def check_blank(state, id, max_context=3):
    blank = state.context.blanks[id]

    try:
        path_to_blank = find_range_ast_path(blank, state.solution_ast)
        sol_part, missing_sol_path = select_path(state.solution_ast, path_to_blank)
        assert not missing_sol_path
    except (ValueError, AssertionError):
        raise InstructorError("Blank {} could not be found in solution.".format(id))

    def get_location(path):
        return " in ".join(
            list(map(lambda path_el: "the " + path_el[0], reversed(path)))[:max_context]
        )

    stu_part, missing_stu_path = select_path(state.student_ast, path_to_blank)
    if missing_stu_path:
        # for highlight:
        child = state.to_child(student_ast=stu_part, solution_ast=sol_part)
        child.report(
            "Did you modify the sample code? We didn't find the expected {} in {}".format(
                missing_stu_path[0][0],
                get_location(path_to_blank[: -len(missing_stu_path)]),
            )
        )

    append_msg = "We checked your answer for {}.".format(get_location(path_to_blank))

    return state.to_child(
        student_ast=stu_part,
        solution_ast=sol_part,
        append_message=append_msg,
        node_name=sol_part.__class__.__name__,
    )
