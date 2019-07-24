import re
from collections import Counter

import markdown2

from protowhat.Feedback import Feedback
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


class TestRunnerProxy(TestRunner):
    # Checks using this might be split into more atomic checks
    def __init__(self, runner: TestRunner):
        super().__init__()
        self.runner = runner

    def do_test(self, test):
        if isinstance(test, Test):
            self.tests.append(test)
        return self.runner.do_test(test)


class Reporter(TestRunnerProxy):
    """Do reporting.

    This class holds the feedback- or success message and tracks whether there are failed tests
    or not. All tests are executed trough do_test() in the Reporter.
    """

    # This is the offset for ANTLR
    ast_highlight_offset = {"column_start": 1, "column_end": 1}

    def __init__(self, runner=None, errors=None, highlight_offset=None):
        super().__init__(runner or TestRunner())
        self.fail = False
        self.errors = errors
        self.errors_allowed = False
        self.highlight_offset = highlight_offset or {}
        self.success_msg = "Great work!"

    def get_errors(self):
        return self.errors

    def allow_errors(self):
        self.errors_allowed = True

    def build_failed_payload(self, feedback: Feedback):
        highlight = Counter()
        code_highlight = feedback.get_highlight_data()

        path = code_highlight.get("path", None)
        if path is not None:
            del code_highlight["path"]

        if code_highlight:
            highlight.update(self.highlight_offset)
            if "line_start" in highlight and "line_end" not in highlight:
                highlight["line_end"] = highlight["line_start"]

            highlight.update(code_highlight)
            highlight.update(self.ast_highlight_offset)

        if path is not None:
            highlight["path"] = str(path)

        return {
            "correct": False,
            "message": Reporter.to_html(feedback.message),
            **highlight,
        }

    def build_final_payload(self):
        if self.fail or self.errors and not self.errors_allowed:
            feedback_msg = "Your code generated an error. Fix it and try again!"
            return {"correct": False, "message": Reporter.to_html(feedback_msg)}
        else:
            return {"correct": True, "message": Reporter.to_html(self.success_msg)}

    @staticmethod
    def to_html(msg):
        return re.sub("<p>(.*)</p>", "\\1", markdown2.markdown(msg)).strip()
