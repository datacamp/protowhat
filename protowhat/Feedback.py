from typing import Dict, Union, List
from collections import Counter
from jinja2 import Template


class FeedbackComponent:
    def __init__(self, feedback: str, kwargs=None, append=True):
        self.feedback = feedback
        self.kwargs = kwargs or {}
        self.append = append

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, repr(vars(self)))


class Feedback:
    # This is the offset for ANTLR
    ast_highlight_offset = {"column_start": 1, "column_end": 1}

    def __init__(
        self,
        conclusion: FeedbackComponent,
        context_components: List[FeedbackComponent] = None,
        highlight=None,
        path=None,
        highlighting_disabled=False,
        highlight_offset=None,
    ):
        self.conclusion = conclusion
        self.context_components = context_components or []
        self.highlight = highlight
        self.path = path
        self.highlighting_disabled = highlighting_disabled
        self.highlight_offset = highlight_offset or {}

    @property
    def _highlight_position(self) -> Dict[str, int]:
        if hasattr(self.highlight, "get_position"):
            position = self.highlight.get_position()
        elif getattr(self.highlight, "first_token", None) and getattr(
            self.highlight, "last_token", None
        ):
            # used by pythonwhat
            # a plugin+register system would be better
            # if many different AST interfaces exist
            position = {
                "line_start": self.highlight.first_token.start[0],
                "column_start": self.highlight.first_token.start[1],
                "line_end": self.highlight.last_token.end[0],
                "column_end": self.highlight.last_token.end[1],
            }
        else:
            position = None

        return position

    def get_highlight(self) -> Dict[str, int]:
        highlight = Counter()
        if not self.highlighting_disabled:
            position = self._highlight_position

            if position:
                highlight.update(self.highlight_offset)
                if "line_start" in highlight and "line_end" not in highlight:
                    highlight["line_end"] = highlight["line_start"]

                highlight.update(position)
                highlight.update(self.ast_highlight_offset)

            if self.path:
                highlight["path"] = str(self.path)

        return highlight or {}

    def get_message(self):
        out_list = []
        msgs = [*self.context_components, self.conclusion]

        if not self.conclusion.append:
            msgs = msgs[-1:]
        elif getattr(self, "highlight", None) and not self.highlighting_disabled:
            # if highlighting info is available, don't use all context messages
            msgs = msgs[-3:]

        # format messages in list, by iterating over previous, current, and next message
        for prev_d, d, next_d in zip([{}, *msgs[:-1]], msgs, [*msgs[1:], {}]):
            tmp_kwargs = {
                "parent": getattr(prev_d, "kwargs", None),
                "child": getattr(next_d, "kwargs", None),
                "this": getattr(d, "kwargs"),
                **getattr(d, "kwargs"),
            }
            # don't bother appending if there is no message
            if not d or not getattr(d, "feedback"):
                continue
            else:
                # TODO: rendering is slow in tests (40% of test time)
                out = Template(d.feedback.replace("__JINJA__:", "")).render(tmp_kwargs)
                out_list.append(out)

        return "".join(out_list)

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, repr(vars(self)))
