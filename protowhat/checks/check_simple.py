

def has_chosen(state, correct, msgs):
    """Verify exercises of the type MultipleChoiceExercise

    Args:
        state:    State instance describing student and solution code. Can be omitted if used with Ex().
        correct:  index of correct option, where 1 is the first option.
        msgs  :    list of feedback messages corresponding to each option.

    :Example:
        The following SCT is for a multiple choice exercise with 2 options, the first
        of which is correct.::

            Ex().has_chosen(1, ['Correct!', 'Incorrect. Try again!'])
    """

    ctxt = {}
    exec(state.student_code, globals(), ctxt)
    sel_indx = ctxt["selected_option"]
    if sel_indx != correct:
        state.report(msgs[sel_indx - 1])
    else:
        state.reporter.success_msg = msgs[correct - 1]

    return state


def allow_errors(state):
    """
    Allow running the student code to generate errors.

    This has to be used only once for every time code is executed or a different xwhat library is used.
    In most exercises that means it should be used just once.

    :Example:
        The following SCT allows the student code to generate errors::

            Ex().allow_errors()
    """
    state.reporter.allow_errors()

    return state


def success_msg(state, msg):
    """
    Changes the success message to display if submission passes.

    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        msg  : feedback message if student and solution ASTs don't match

    :Example:
        The following SCT changes the success message::

            Ex().success_msg("You did it!")

    """
    state.reporter.success_msg = msg

    return state
