from pathlib import Path

from protowhat.Feedback import Feedback


def check_file(
    state,
    path,
    missing_msg="Did you create the file `{}`?",
    is_dir_msg="Want to check the file `{}`, but found a directory.",
    parse=True,
    solution_code=None,
):
    """Test whether file exists, and make its contents the student code.

    Note: this SCT fails if the file is a directory.
    """

    p = Path(path)
    if not p.exists():
        state.report(Feedback(missing_msg.format(path)))  # test file exists
    if p.is_dir():
        state.report(Feedback(is_dir_msg.format(path)))  # test its not a dir

    code = p.read_text()

    sol_kwargs = {"solution_code": solution_code, "solution_ast": None}
    if solution_code:
        sol_kwargs["solution_ast"] = (
            state.parse(solution_code, test=False) if parse else None
        )

    return state.to_child(
        append_message="We checked the file `{}`. ".format(path),
        student_code=code,
        student_ast=state.parse(code) if parse else None,
        **sol_kwargs
    )


def has_dir(state, path, incorrect_msg="Did you create a directory `{}`?"):
    """Test whether a directory exists."""
    if not Path(path).is_dir():
        state.report(Feedback(incorrect_msg.format(path)))

    return state


# helper functions
def load_file(relative_path, prefix=""):
    # the prefix can be partialed
    # so it's not needed to copy the common part of paths
    p = Path(prefix, relative_path)

    return p.read_text()
