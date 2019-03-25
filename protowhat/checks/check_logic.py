from protowhat.Feedback import Feedback
from protowhat.Test import TestFail
from functools import partial

from protowhat.utils import legacy_signature


def multi(state, *tests):
    """Run multiple subtests. Return original state (for chaining).

    This function could be thought as an AND statement, since all tests it runs must pass

    Args:
        state: State instance describing student and solution code,  can be omitted if used with Ex()
        tests: one or more sub-SCTs to run.

    :Example:
        The SCT below checks two has_code cases.. ::

            Ex().multi(has_code('SELECT'), has_code('WHERE'))

        The SCT below uses ``multi`` to 'branch out' to check that
        the SELECT statement has both a WHERE and LIMIT clause.. ::

            Ex().check_node('SelectStmt', 0).multi(
                check_edge('where_clause'),
                check_edge('limit_clause')
            )
    """
    for test in iter_tests(tests):
        # assume test is function needing a state argument
        # partial state so reporter can test
        state.do_test(partial(test, state))

    # return original state, so can be chained
    return state


@legacy_signature(incorrect_msg='msg')
def check_not(state, *tests, msg):
    """Run multiple subtests that should fail. If all subtests fail, returns original state (for chaining)

    - This function is currently only tested in working with ``has_code()`` in the subtests.
    - This function can be thought as a ``NOT(x OR y OR ...)`` statement, since all tests it runs must fail
    - This function can be considered a direct counterpart of multi.

    Args:
        state: State instance describing student and solution code, can be omitted if used with Ex()
        *tests: one or more sub-SCTs to run
        msg: feedback message that is shown in case not all tests specified in ``*tests`` fail.

    :Example:

        Thh SCT below runs two has_code cases.. ::

            Ex().check_not(
                has_code('INNER'),
                has_code('OUTER'),
                incorrect_msg="Don't use `INNER` or `OUTER`!"
            )

        If students use ``INNER (JOIN)`` or ``OUTER (JOIN)`` in their code, this test will fail.

    """
    for test in iter_tests(tests):
        try:
            test(state)
        except TestFail:
            # it fails, as expected, off to next one
            continue
        return state.report(Feedback(msg))

    # return original state, so can be chained
    return state


def check_or(state, *tests):
    """Test whether at least one SCT passes.

    If all of the tests fail, the feedback of the first test will be presented to the student.

    Args:
        state: State instance describing student and solution code, can be omitted if used with Ex()
        tests: one or more sub-SCTs to run

    :Example:
        The SCT below tests that the student typed either 'SELECT' or 'WHERE' (or both).. ::

            Ex().check_or(
                has_code('SELECT'),
                has_code('WHERE')
            )

        The SCT below checks that a SELECT statement has at least a WHERE c or LIMIT clause.. ::

            Ex().check_node('SelectStmt', 0).check_or(
                check_edge('where_clause'),
                check_edge('limit_clause')
            )
    """
    success = False
    first_feedback = None

    for test in iter_tests(tests):
        try:
            multi(state, test)
            success = True
        except TestFail as e:
            if not first_feedback:
                first_feedback = e.feedback
        if success:
            return state  # todo: add test

    state.report(first_feedback)


def check_correct(state, check, diagnose):
    """Allows feedback from a diagnostic SCT, only if a check SCT fails.

    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        check: An sct chain that must succeed.
        diagnose: An sct chain to run if the check fails.

    :Example:
        The SCT below tests whether students query result is correct, before running diagnostic SCTs.. ::

            Ex().check_correct(
                check_result(),
                check_node('SelectStmt')
            )

    """
    feedback = None
    try:
        multi(state, check)
    except TestFail as e:
        feedback = e.feedback

    # todo: let if from except wrap try-except
    #  only once teach uses force_diagnose
    try:
        multi(state, diagnose)
    except TestFail as e:
        if feedback is not None or state.force_diagnose:
            feedback = e.feedback

    if feedback is not None:
        state.report(feedback)

    return state  # todo: add test


def iter_tests(tests):
    for arg in tests:
        if arg is None:
            continue

        # when input is a single test, make iterable
        if callable(arg):
            arg = [arg]

        for test in arg:
            yield test


def disable_highlighting(state):
    """Disable highlighting in the remainder of the SCT chain.

    Include this function if you want to avoid that pythonwhat marks which part of the student submission is incorrect.
    """
    return state.to_child(highlighting_disabled=True)


def fail(state, msg="fail"):
    """Always fails the SCT, with an optional msg.

    This function takes a single argument, ``msg``, that is the feedback given to the student.
    Note that this would be a terrible idea for grading submissions, but may be useful while writing SCTs.
    For example, failing a test will highlight the code as if the previous test/check had failed.
    """
    _msg = state.build_message(msg)
    state.report(Feedback(_msg, state))

    return state
