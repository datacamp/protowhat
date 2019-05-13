from pathlib import Path

from protowhat.check import Check, store_call_data


class CheckFile(Check):
    """Test whether file exists, and make its contents the student code.

    Args:
        path: expected location of the file
        missing_msg: feedback message if no file is found in the expected location
        is_dir_msg: feedback message if the path is a directory instead of a file
        parse: If ``True`` (the default) the content of the file is interpreted as code in the main exercise technology.
            This enables more checks on the content of the file.
        solution_code: this argument can be used to pass the expected code for the file
            so it can be used by subsequent checks.

    Note:
        This SCT fails if the file is a directory.

    :Example:

        To check if a user created the file ``my_output.txt`` in the subdirectory ``resources``
        of the directory where the exercise is run, use this SCT::

            Ex().check_file("resources/my_output.txt", parse=False)
    """

    @store_call_data
    def __init__(
        self,
        path,
        missing_msg="Did you create the file `{}`?",
        is_dir_msg="Want to check the file `{}`, but found a directory.",
        parse=True,
        solution_code=None,
    ):
        super().__init__(locals())

    def call(self, state):
        path_obj = Path(self.path)
        if not path_obj.exists():
            state.report(self.missing_msg.format(self.path))  # test file exists
        if path_obj.is_dir():
            state.report(self.is_dir_msg.format(self.path))  # test its not a dir

        code = get_file_content(path_obj)

        sol_kwargs = {"solution_code": self.solution_code, "solution_ast": None}
        if self.solution_code:
            sol_kwargs["solution_ast"] = (
                state.parse(self.solution_code, test=False) if self.parse else False
            )

        child_state = state.to_child(
            append_message="We checked the file `{}`. ".format(self.path),
            student_code=code,
            student_ast=state.parse(code) if self.parse else False,
            **sol_kwargs
        )

        child_state.path = path_obj   # .parent + .name

        return child_state


class HasDir(Check):
    """Test whether a directory exists.

    Args:
        path: expected location of the directory
        msg: feedback message if no directory is found in the expected location

    :Example:

        To check if a user created the subdirectory ``resources``
        in the directory where the exercise is run, use this SCT::

            Ex().has_dir("resources")
    """
    @store_call_data
    def __init__(self, path, msg="Did you create a directory `{}`?"):
        super().__init__(locals())

    def call(self, state):
        if not Path(self.path).is_dir():
            state.report(self.msg.format(self.path))

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
