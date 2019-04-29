import re
import markdown2
from protowhat.Test import Test

"""
This file holds the reporter class.
"""


class TestRunner:
    def __init__(self):
        self.tests = []

    def do_test(self, test):
        """Raise failing test.

        Raise a ``TestFail`` object, containing the feedback message and highlight information.
        """
        result = None
        feedback = None
        test()
        if isinstance(test, Test):
            self.tests.append(test)
            result = test.result
            if not result:
                feedback = test.get_feedback()

        return result, feedback

    def do_tests(self, tests):
        return [self.do_test(test) for test in tests]

    @property
    def failures(self):
        return list(filter(lambda test: test.result is False, self.tests))

    @property
    def has_failed(self):
        return len(self.failures) > 0


class Reporter(TestRunner):
    """Do reporting.

    This class holds the feedback- or success message and tracks whether there are failed tests
    or not. All tests are executed trough do_test() in the Reporter.
    """

    def __init__(self, errors=None, highlight_offset=None):
        super().__init__()
        self.errors = errors
        self.errors_allowed = False
        self.highlight_offset = highlight_offset or {}
        self.success_msg = "Great work!"

    def get_errors(self):
        return self.errors

    def allow_errors(self):
        self.errors_allowed = True

    def build_failed_payload(self, feedback):
        highlight = feedback.get_highlight_info()
        for k in self.highlight_offset:
            if k in highlight:
                highlight[k] = highlight[k] + self.highlight_offset[k]

        return {
            "correct": False,
            "message": Reporter.to_html(feedback.message),
            **highlight,
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


class TestRunnerProxy(TestRunner):
    # Checks using this might be split into more atomic checks
    def __init__(self, runner: TestRunner):
        super().__init__()
        self.runner = runner

    def do_test(self, test):
        self.tests.append(test)
        return self.runner.do_test(test)
