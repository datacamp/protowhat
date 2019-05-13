from protowhat.check import Check, store_call_data


class HasChosen(Check):
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
    @store_call_data
    def __init__(self, correct, msgs):
        super().__init__(locals())

    def call(self, state):
        ctxt = {}
        exec(state.student_code, globals(), ctxt)
        sel_indx = ctxt["selected_option"]
        if sel_indx != self.correct:
            state.report(self.msgs[sel_indx - 1])
        else:
            state.reporter.success_msg = self.msgs[self.correct - 1]

        return state


class AllowErrors(Check):
    """
    Allow running the student code to generate errors.

    This has to be used only once for every time code is executed or a different xwhat library is used.
    In most exercises that means it should be used just once.

    :Example:
        The following SCT allows the student code to generate errors::

            Ex().allow_errors()
    """
    def call(self, state):
        state.reporter.allow_errors()

        return state


class SuccessMsg(Check):
    """
    Changes the success message to display if submission passes.

    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        msg  : feedback message if student and solution ASTs don't match

    :Example:
        The following SCT changes the success message::

            Ex().success_msg("You did it!")

    """
    @store_call_data
    def __init__(self, msg):
        super().__init__(locals())

    def call(self, state):
        state.reporter.success_msg = self.msg

        return state
