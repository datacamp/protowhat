from pathlib import Path


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

    path_obj = Path(path)
    if not path_obj.exists():
        state.report(missing_msg.format(path))  # test file exists
    if path_obj.is_dir():
        state.report(is_dir_msg.format(path))  # test its not a dir

    code = get_file_content(path_obj)

    sol_kwargs = {"solution_code": solution_code, "solution_ast": None}
    if solution_code:
        sol_kwargs["solution_ast"] = (
            state.parse(solution_code, test=False) if parse else False
        )

    child_state = state.to_child(
        append_message="We checked the file `{}`. ".format(path),
        student_code=code,
        student_ast=state.parse(code) if parse else False,
        **sol_kwargs
    )

    child_state.path = path_obj  # .parent + .name

    return child_state


def has_dir(state, path, incorrect_msg="Did you create a directory `{}`?"):
    """Test whether a directory exists."""
    if not Path(path).is_dir():
        state.report(incorrect_msg.format(path))

    return state


# helper functions
def load_file(relative_path, prefix=""):
    # the prefix can be partialed
    # so it's not needed to copy the common part of paths
    path = Path(prefix, relative_path)

    return get_file_content(path)


def get_file_content(path):
    if not isinstance(path, Path):
        path = Path(path)

    try:
        content = path.read_text(encoding="utf-8")
    except:
        content = None

    return content
