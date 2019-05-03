class Feedback:
    def __init__(self, message, state=None):
        self.message = message
        self.highlight = None
        self.highlighting_disabled = False
        if state is not None:
            self.highlight = getattr(state, "highlight", None)
            self.highlighting_disabled = state.highlighting_disabled

    def _highlight_data(self):
        return self.highlight.get_position()

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
