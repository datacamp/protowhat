class Feedback:
    def __init__(self, message, state=None):
        self.message = message
        self.highlight = None
        self.highlighting_disabled = False
        if state is not None:
            self.highlight = getattr(state, "highlight", None)
            self.highlighting_disabled = state.highlighting_disabled

    def _highlight_data(self):
        if hasattr(self.highlight, "get_position"):
            return self.highlight.get_position()
        elif hasattr(self.highlight, "first_token") and hasattr(
            self.highlight, "last_token"
        ):
            # used by pythonwhat
            # a plugin+register system would be better
            # if many different AST interfaces exist
            return {
                "line_start": self.highlight.first_token.start[0],
                "column_start": self.highlight.first_token.start[1],
                "line_end": self.highlight.last_token.end[0],
                "column_end": self.highlight.last_token.end[1],
            }

    def get_highlight_data(self):
        result = None
        try:
            if self.highlight is not None and not self.highlighting_disabled:
                result = self._highlight_data()
        except:
            pass

        return result or {}


class InstructorError(Exception):
    pass
