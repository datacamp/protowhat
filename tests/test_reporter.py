from collections import Counter
from pathlib import Path

import pytest
from protowhat.Feedback import Feedback
from protowhat.Reporter import Reporter
from protowhat.Test import Fail
from tests.helper import Success


def test_test_runner_proxy():
    r = Reporter()

    assert len(r.tests) == 0
    assert not r.has_failed
    assert not r.failures

    result, feedback = r.do_test(Success("msg"))

    assert len(r.tests) == 1
    assert not r.has_failed
    assert not r.failures
    assert isinstance(result, bool)
    assert feedback is None

    failing_test = Fail("msg")
    results = r.do_tests([failing_test, Success("msg")])

    assert len(r.tests) == 3
    assert r.has_failed
    assert len(r.failures) == 1
    assert failing_test in r.failures
    assert isinstance(results, list)

    assert r.tests == r.runner.tests
    assert r.runner.has_failed
    assert r.failures == r.runner.failures


highlight_range_1 = {"line_start": 1, "column_start": 3, "line_end": 5, "column_end": 7}
highlight_payload_1 = {
    "line_start": 1,
    "column_start": 4,
    "line_end": 5,
    "column_end": 8,
}
highlight_range_2 = {
    "line_start": 3,
    "column_start": 5,
    "line_end": 7,
    "column_end": 11,
}
highlight_payload_2 = {
    "line_start": 3,
    "column_start": 6,
    "line_end": 7,
    "column_end": 12,
}
highlight_combined = Counter()
highlight_combined.update(highlight_payload_1)
highlight_combined.update(highlight_range_2)


class Highlight:
    def __init__(self, position):
        self.position = position

    def get_position(self):
        return self.position


@pytest.mark.parametrize(
    "offset, highlight, payload_highlight_info",
    [
        (None, {}, {}),
        (None, highlight_range_1, highlight_payload_1),
        ({}, {}, {}),
        ({}, highlight_range_1, highlight_payload_1),
        (highlight_range_1, {}, {}),
        (
            {"line_start": 1},
            highlight_range_1,
            {**highlight_payload_1, "line_start": 2, "line_end": 6},
        ),
        (highlight_range_2, highlight_range_1, highlight_combined),
    ],
)
def test_highlighting_offset(offset, highlight, payload_highlight_info):
    r = Reporter(highlight_offset=offset)

    f = Feedback("msg")
    f.highlight = Highlight(highlight)

    payload = r.build_failed_payload(f)

    expected_payload = {"correct": False, "message": "msg", **payload_highlight_info}

    assert payload == expected_payload


def test_highlighting_offset_proxy():
    r = Reporter(Reporter(), highlight_offset=highlight_range_2)

    f = Feedback("msg")
    f.highlight = Highlight(highlight_range_1)

    payload = r.build_failed_payload(f)

    expected_payload = {"correct": False, "message": "msg", **highlight_combined}

    assert payload == expected_payload


def test_highlighting_path():
    r = Reporter()

    class FeedbackState:
        highlighting_disabled = False
        highlight = Highlight(highlight_range_1)
        path = Path("test.py")

    f = Feedback("msg", FeedbackState())

    payload = r.build_failed_payload(f)

    expected_payload = {
        "correct": False,
        "message": "msg",
        "path": "test.py",
        **highlight_payload_1,
    }

    assert payload == expected_payload
