from collections import Counter

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
highlight_range_2 = {
    "line_start": 3,
    "column_start": 5,
    "line_end": 7,
    "column_end": 11,
}
highlight_combined = Counter()
highlight_combined.update(highlight_range_1)
highlight_combined.update(highlight_range_2)


class FeedbackTest(Feedback):
    def _highlight_data(self):
        return self.highlight

    def get_highlight_info(self):
        return self.get_highlight_data()


@pytest.mark.parametrize(
    "offset, highlight, payload_highlight_info",
    [
        (None, {}, {}),
        (None, highlight_range_1, highlight_range_1),
        ({}, {}, {}),
        ({}, highlight_range_1, highlight_range_1),
        (highlight_range_1, {}, {}),
        (
            {"line_start": 1},
            highlight_range_1,
            {**highlight_range_1, "line_start": 2, "line_end": 6},
        ),
        (highlight_range_2, highlight_range_1, highlight_combined),
    ],
)
def test_highlighting_offset(offset, highlight, payload_highlight_info):
    r = Reporter(highlight_offset=offset)

    f = FeedbackTest("msg")
    f.highlight = highlight

    payload = r.build_failed_payload(f)

    expected_payload = {"correct": False, "message": "msg", **payload_highlight_info}

    assert payload == expected_payload


def test_highlighting_offset_proxy():
    r = Reporter(Reporter(), highlight_offset=highlight_range_2)

    f = FeedbackTest("msg")
    f.highlight = highlight_range_1

    payload = r.build_failed_payload(f)

    expected_payload = {"correct": False, "message": "msg", **highlight_combined}

    assert payload == expected_payload
