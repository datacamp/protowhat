from typing import Dict, Union, List
from collections import Counter
from jinja2 import Template


class FeedbackComponent:
    def __init__(self, feedback: str, kwargs=None, append=True):
        self.feedback = feedback  # TODO: message | feedback | ...
        self.kwargs = kwargs or {}
        self.append = append

    @property
    def message(self):
        return self.feedback

    @message.setter
    def message(self, message):
        self.feedback = message

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
        full_code_position=None,
    ):
        self.conclusion = conclusion
        self.context_components = context_components or []
        self.highlight = highlight
        self.path = path
        self.highlighting_disabled = highlighting_disabled
        self.highlight_offset = highlight_offset or {}
        self.full_code_position = full_code_position

    @classmethod
    def get_highlight_position(cls, highlight) -> Dict[str, int]:
        if hasattr(highlight, "get_position"):
            return highlight.get_position()

    def get_highlight(self) -> Dict[str, int]:
        highlight = Counter()

        if not self.highlighting_disabled:
            position = self.get_highlight_position(self.highlight)

            # TODO: handle highlighting everything
            # if position != self.full_code_position:

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
        msgs = [*filter(None.__ne__, self.context_components), self.conclusion]

        if not self.conclusion.append:
            msgs = msgs[-1:]
        elif getattr(self, "highlight", None) and not self.highlighting_disabled:
            # if highlighting info is available, don't use all context messages
            msgs = msgs[-3:]

        # format messages in list, by iterating over previous, current, and next message
        for prev_d, d, next_d in zip([None, *msgs[:-1]], msgs, [*msgs[1:], None]):
            tmp_kwargs = {
                "parent": getattr(prev_d, "kwargs", None),
                "child": getattr(next_d, "kwargs", None),
                "this": getattr(d, "kwargs"),
                **getattr(d, "kwargs"),
            }
            # don't bother appending if there is no message
            if not getattr(d, "feedback"):
                continue
            else:
                # TODO: rendering is slow in tests (40% of test time)
                out = Template(d.feedback.replace("__JINJA__:", "")).render(tmp_kwargs)
                out_list.append(out)

        return "".join(out_list)

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, repr(vars(self)))
