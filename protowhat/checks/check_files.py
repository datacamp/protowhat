import re
import os

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


def has_command(state, commands, pattern, msg, fixed=False):
    # todo: verify called on root?
    #  - port assert_root from pythonwhat
    #    - as method on State?
    #    - as helper method accepting state?
    correct = False
    for command in commands:
        # similar to has_code
        if pattern in command if fixed else re.search(pattern, command):
            correct = True
            break

    if not correct:
        state.report(msg)

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


# env vars
BASH_HISTORY_PATH_ENV = "BASH_HISTORY_PATH"
BASH_HISTORY_LENGTH_ENV = "BASH_HISTORY_LENGTH"

# env var defaults
os.environ[BASH_HISTORY_PATH_ENV] = os.environ.get(
    BASH_HISTORY_PATH_ENV, "/home/repl/.bash_history"
)
os.environ[BASH_HISTORY_LENGTH_ENV] = os.environ.get(BASH_HISTORY_LENGTH_ENV, "0")


def bash_history(full_history=False,):
    # if used as a fallback in check_correct, full_history can be False

    # case:
    # history used multiple times in SCT
    # solution:
    # call this function once at SCT start (+ import it)

    # edge case:
    # bash history is not empty from earlier session
    # solution:
    # call function on module load

    # edge case:
    # bash history is not empty from an exercise that didn't use this SCT
    # solution: todo
    # let backend call an init function on exercise start
    # + xwhat calls protowhat init / register init handlers

    try:
        with open(os.environ[BASH_HISTORY_PATH_ENV], encoding="utf-8") as f:
            old_history_length = int(os.environ[BASH_HISTORY_LENGTH_ENV])
            history = f.readlines()
            new_history_length = len(history)
            os.environ[BASH_HISTORY_LENGTH_ENV] = str(new_history_length)
            return history if full_history else history[old_history_length:]
    except FileNotFoundError:
        return []


bash_history()


"""
# beyond has_command?
# - only 'multi': all commands need to pass SCT
# - ugly code using internals
commands = bash_history()
for command in commands:
    Ex(Ex()._state.to_child(student_code=command)).has_code()


# new general (dangerous?) SCT to solve limitations:
# alternative: override() SCT with optional student_code argument (safer?)
def update(state, **kwargs):
    return state.to_child(**kwargs)


# equivalent of `Ex().has_command(commands, pattern)`
Ex().check_or(*[update(student_code=command).has_code(pattern) for command in commands])


# shellwhat parsing of bash history
Ex().check_or(
    *[
        update(student_code=command)
        .check_node(node_name)
        .check_edge(edge_name)
        .has_equal_ast()
        for command in commands
    ]
)
"""
