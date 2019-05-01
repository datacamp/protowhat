from functools import wraps

from protowhat.Feedback import Feedback


def _debug(state, msg=""):
    """
    This SCT function makes the SCT fail with a message containing debugging information
    and highlights the focus of the SCT at that point.
    """
    check_history = [
        s.creator["type"]
        for s in state.state_history
        if getattr(s, "creator", None)
    ]

    feedback = ""
    if msg:
        feedback += msg + "\n"

    if check_history:
        feedback += "SCT function history: `{}`".format(" > ".join(check_history))

    if state.reporter.tests:
        feedback += "\nLast test: `{}`".format(repr(state.reporter.tests[-1]))

    # latest highlight added automatically
    state.report(Feedback(feedback))

    return state


def legacy_signature(**kwargs_mapping):
    """
    This decorator makes it possible to call a function using old argument names
    when they are passed as keyword arguments.

    @legacy_signature(old_arg1='arg1', old_arg2='arg2')
    def func(arg1, arg2=1):
        return arg1 + arg2

    func(old_arg1=1) == 2
    func(old_arg1=1, old_arg2=2) == 3
    """

    def signature_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            redirected_kwargs = {
                kwargs_mapping[k] if k in kwargs_mapping else k: v
                for k, v in kwargs.items()
            }
            return f(*args, **redirected_kwargs)

        return wrapper

    return signature_decorator
