from collections import Counter
from pathlib import Path

import pytest
from protowhat.Feedback import Feedback, FeedbackComponent
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


# TODO: test_feedback
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
    r = Reporter()
    f = Feedback(
        FeedbackComponent("msg"),
        highlight=Highlight(highlight),
        highlight_offset=offset,
    )

    payload = r.build_failed_payload(f)

    expected_payload = {"correct": False, "message": "msg", **payload_highlight_info}

    assert payload == expected_payload


def test_highlighting_offset_proxy():
    r = Reporter()
    f = Feedback(
        FeedbackComponent("msg"),
        highlight=Highlight(highlight_range_1),
        highlight_offset=highlight_range_2,
    )

    payload = r.build_failed_payload(f)

    expected_payload = {"correct": False, "message": "msg", **highlight_combined}

    assert payload == expected_payload


def test_highlighting_path():
    r = Reporter()
    f = Feedback(
        FeedbackComponent("msg"),
        highlight=Highlight(highlight_range_1),
        path=Path("test.py"),
    )

    payload = r.build_failed_payload(f)

    expected_payload = {
        "correct": False,
        "message": "msg",
        "path": "test.py",
        **highlight_payload_1,
    }

    assert payload == expected_payload


def test_highlighting_path_no_position():
    r = Reporter()
    f = Feedback(FeedbackComponent("msg"), path=Path("test.py"))

    payload = r.build_failed_payload(f)

    expected_payload = {"correct": False, "message": "msg", "path": "test.py"}

    assert payload == expected_payload


def test_reporter_code_block():
    r = Reporter()
    msg = "Expected \n```\n{{sol_str}}\n```\n, but got \n```\n{{stu_str}}\n```\n"
    code = """
while True:
    car_wash_num += 1

    # Get the current simulation time and clock-in the process time
    yield env.timeout(5)"""
    fmt_kwargs = {"sol_str": code, "stu_str": code}
    f = Feedback(FeedbackComponent(msg, fmt_kwargs))

    payload = r.build_failed_payload(f)
    expected_message = """Expected 

<pre><code>
while True:
    car_wash_num += 1

    # Get the current simulation time and clock-in the process time
    yield env.timeout(5)
</code></pre>

, but got 

<pre><code>
while True:
    car_wash_num += 1

    # Get the current simulation time and clock-in the process time
    yield env.timeout(5)
</code></pre>"""

    assert payload["message"] == expected_message
