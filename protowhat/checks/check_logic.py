from protowhat.Test import TestFail
from types import GeneratorType
from functools import partial

def fail(state, incorrect_msg="fail"):
    """Always fails the SCT, with an optional msg."""
    state.do_test(incorrect_msg)

    return state

def multi(state, *tests):
    """Run multiple subtests. Return original state (for chaining).

    This function could be thought as an AND statement, since all tests it runs must pass

    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        args: one or more sub-SCTs to run.

    :Example:
        The SCT below runs run two has_code cases.. ::

            Ex().multi(has_code('SELECT'), has_code('WHERE'))

        The SCT below checks that a SELECT statement has both a WHERE and LIMIT clause.. ::

            Ex().check_node('SelectStmt', 0).multi(
                check_edge('where_clause'),
                check_edge('limit_clause')
            )
    """

    for arg in tests:
        # when input is a single test, make iterable
        if callable(arg): arg = [arg]

        for test in arg:
            # assume test is function needing a state argument
            # partial state so reporter can test
            test(state)

    # return original state, so can be chained
    return state

def check_not(state, *tests, incorrect_msg):
    """Run multiple subtests that should fail. If all subtests fail, returns original state (for chaining)

    - This function is currently only tested in working with ``has_code()`` in the subtests.
    - This function can be thought as a ``NOT(x OR y OR ...)`` statement, since all tests it runs must fail
    - This function can be considered a direct counterpart of multi.

    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        *tests: one or more sub-SCTs to run.
        incorrect_msg: feedback message that is shown in case not all tests specified in ``*tests`` fail.

    :Example:

        Thh SCT below runs two has_code cases.. ::

            Ex().check_not(
                has_code('INNER'),
                has_code('OUTER'),
                incorrect_msg="Don't use `INNER` or `OUTER`!"
            )

        If students use ``INNER (JOIN)`` or ``OUTER (JOIN)`` in their code, this test will fail.

    """

    for arg in tests:
        # when input is a single test, make iterable
        if callable(arg): arg = [arg]
            
        for test in arg:
            try:
                test(state)
            except TestFail:
                # it fails, as expected, off to next one
                continue
            return state.do_test(incorrect_msg)

    # return original state, so can be chained
    return state

def check_or(state, *tests):
    """Test whether at least one SCT passes.
    
    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        tests: one or more sub-SCTs to run.

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

    for arg in tests:
        # when input is a single test, make iterable
        if callable(arg): arg = [arg]

        for test in arg:
            try:
                test(state)
                success = True
            except TestFail as e:
                if not first_feedback: first_feedback = e.feedback
            if success:
                return
    
    state.do_test(first_feedback.message, highlight=first_feedback.astobj)

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

    def diagnose_and_check(state):
        # use multi twice, since diagnose and check may be lists of tests
        multi(state, diagnose, check)

    check_or(state, diagnose_and_check, check)
