from pathlib import Path
from collections.abc import Mapping

from protowhat.Feedback import Feedback


def check_file(
    state,
    fname,
    missing_msg="Did you create a file named `{}`?",
    is_dir_msg="Want to check a file named `{}`, but found a directory.",
    parse=True,
    use_fs=True,
    use_solution=False,
):
    """Test whether file exists, and make its contents the student code.

    Note: this SCT fails if the file is a directory.
    """

    if use_fs:
        p = Path(fname)
        if not p.exists():
            state.report(Feedback(missing_msg.format(fname)))  # test file exists
        if p.is_dir():
            state.report(Feedback(is_dir_msg.format(fname)))  # test its not a dir

        code = p.read_text()
    else:
        code = _get_fname(state, "student_code", fname)

        if code is None:
            state.report(Feedback(missing_msg.format(fname)))  # test file exists

    sol_kwargs = {"solution_code": None, "solution_ast": None}
    if use_solution:
        sol_code = _get_fname(state, "solution_code", fname)
        if sol_code is None:
            raise Exception("Solution code does not have file named: %s" % fname)
        sol_kwargs["solution_code"] = sol_code
        sol_kwargs["solution_ast"] = (
            state.parse(sol_code, test=False) if parse else None
        )

    return state.to_child(
        student_code=code,
        student_ast=state.parse(code) if parse else None,
        fname=fname,
        **sol_kwargs
    )


def _get_fname(state, attr, fname):
    code_dict = getattr(state, attr)
    if not isinstance(code_dict, Mapping):
        raise TypeError(
            "Can't get {} from state.{}, which must be a " "dictionary or Mapping."
        )

    return code_dict.get(fname)


def has_dir(state, fname, incorrect_msg="Did you create a directory named `{}`?"):
    """Test whether a directory exists."""
    if not Path(fname).is_dir():
        state.report(Feedback(incorrect_msg.format(fname)))

    return state
