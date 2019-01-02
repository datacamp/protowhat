import re
import markdown2
from protowhat.Test import TestFail, Feedback

"""
This file holds the reporter class.
"""


class Reporter:
    """Do reporting.

    This class holds the feedback- or success message and tracks whether there are failed tests
    or not. All tests are executed trough do_test() in the Reporter.
    """

    active_reporter = None

    def __init__(self, errors=None):
        self.success_msg = "Great work!"
        self.errors = errors
        self.errors_allowed = False

    def get_errors(self):
        return self.errors

    def allow_errors(self):
        self.errors_allowed = True

    def do_test(self, feedback_msg, highlight=None):
        """Raise failing test.

        Raise a ``TestFail`` object, containing the feedback message and highlight information.
        """

        feedback = Feedback(feedback_msg, highlight)
        raise TestFail(feedback, self.build_failed_payload(feedback))

    @staticmethod
    def formatted_line_info(line_info):
        cpy = {**line_info}
        for k in ["column_start", "column_end"]:
            if k in cpy:
                cpy[k] += 1
        return cpy

    def build_failed_payload(self, feedback):
        return {
            "correct": False,
            "message": Reporter.to_html(feedback.message),
            **self.formatted_line_info(feedback.get_line_info()),
        }

    def build_final_payload(self):
        if self.errors and not self.errors_allowed:
            feedback_msg = "Your code generated an error. Fix it and try again!"
            return {"correct": False, "message": Reporter.to_html(feedback_msg)}
        else:
            return {"correct": True, "message": Reporter.to_html(self.success_msg)}

    @staticmethod
    def to_html(msg):
        return re.sub("<p>(.*)</p>", "\\1", markdown2.markdown(msg)).strip()
