class Feedback(object):
    def __init__(self, message, astobj=None):
        self.message = message
        self.astobj = astobj

    def get_line_info(self):
        try:
            if self.astobj is not None:
                return self.astobj.get_position()
            else:
                return {}
        except:
            return {}


class TestFail(Exception):
    def __init__(self, feedback, payload):
        super().__init__(feedback.message)
        self.feedback = feedback
        self.payload = payload
