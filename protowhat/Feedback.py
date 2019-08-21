from typing import Dict


class Feedback:
    def __init__(self, message, state=None):
        self.message = message
        self.highlight = None
        self.highlighting_disabled = False
        self.path = None
        if state is not None:
            self.highlight = getattr(state, "highlight", None)
            self.highlighting_disabled = state.highlighting_disabled
            if hasattr(state, "path"):
                self.path = state.path

    def _highlight_data(self) -> Dict[str, int]:
        highlight = {}
        if self.path:
            highlight["path"] = self.path

        if hasattr(self.highlight, "get_position"):
            position = self.highlight.get_position()
            if position:
                highlight.update(position)
        elif getattr(self.highlight, "first_token", None) and getattr(
            self.highlight, "last_token", None
        ):
            # used by pythonwhat
            # a plugin+register system would be better
            # if many different AST interfaces exist
            highlight.update(
                {
                    "line_start": self.highlight.first_token.start[0],
                    "column_start": self.highlight.first_token.start[1],
                    "line_end": self.highlight.last_token.end[0],
                    "column_end": self.highlight.last_token.end[1],
                }
            )

        return highlight

    def get_highlight_data(self) -> Dict[str, int]:
        result = None
        if self.highlight is not None and not self.highlighting_disabled:
            result = self._highlight_data()

        return result or {}

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, repr(vars(self)))


class InstructorError(Exception):
    pass
