class Feedback:
    def __init__(self, message, astobj=None):
        self.message = message
        self.highlight = astobj

    def get_line_info(self):
        try:
            if self.highlight is not None:
                return self.highlight.get_position()
            else:
                return {}
        except:
            return {}

    def get_formatted_line_info(self):
        formatted_info = self.get_line_info()
        for k in ["column_start", "column_end"]:
            if k in formatted_info:
                formatted_info[k] += 1
        return formatted_info


class InstructorError(Exception):
    pass
