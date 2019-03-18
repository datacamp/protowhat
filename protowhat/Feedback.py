class Feedback:
    def __init__(self, message, state=None):
        self.message = message
        self.highlight = None
        self.highlighting_disabled = False
        if state is not None:
            self.highlight = getattr(state, "highlight", None)
            self.highlighting_disabled = state.highlighting_disabled

    def _line_info(self):
        return self.highlight.get_position()

    def get_line_info(self):
        result = None
        try:
            if self.highlight is not None and not self.highlighting_disabled:
                result = self._line_info()
        except:
            pass

        return result or {}

    def get_formatted_line_info(self):
        formatted_info = self.get_line_info()
        for k in ["column_start", "column_end"]:
            if k in formatted_info:
                formatted_info[k] += 1
        return formatted_info


class InstructorError(Exception):
    pass
