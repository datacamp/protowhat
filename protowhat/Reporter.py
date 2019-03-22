import re
import markdown2
from protowhat.Test import TestFail, Test

"""
This file holds the reporter class.
"""


class Reporter:
    """Do reporting.

    This class holds the feedback- or success message and tracks whether there are failed tests
    or not. All tests are executed trough do_test() in the Reporter.
    """
    def __init__(self, errors=None):
        self.errors = errors
        self.errors_allowed = False
        self.success_msg = "Great work!"

    def get_errors(self):
        return self.errors

    def allow_errors(self):
        self.errors_allowed = True

    def do_test(self, test):
        """Raise failing test.

        Raise a ``TestFail`` object, containing the feedback message and highlight information.
        """
        if isinstance(test, Test):
            test.test()
            result = test.result
            if not result:
                feedback = test.get_feedback()
                raise TestFail(feedback, self.build_failed_payload(feedback))

        else:
            result = None
            test()  # run function for side effects

        return result

    def build_failed_payload(self, feedback):
        return {
            "correct": False,
            "message": Reporter.to_html(feedback.message),
            **feedback.get_formatted_line_info(),
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
