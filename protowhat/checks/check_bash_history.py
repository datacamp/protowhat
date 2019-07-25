import os
import re

from pathlib import Path

# env vars
from protowhat.Feedback import InstructorError

BASH_HISTORY_PATH_ENV = "BASH_HISTORY_PATH"
BASH_HISTORY_INFO_PATH_ENV = "BASH_HISTORY_INFO"

# env var defaults
os.environ[BASH_HISTORY_PATH_ENV] = os.environ.get(
    BASH_HISTORY_PATH_ENV, "/home/repl/.bash_history"
)
os.environ[BASH_HISTORY_INFO_PATH_ENV] = os.environ.get(
    BASH_HISTORY_INFO_PATH_ENV, "/home/repl/.bash_history_info"
)


"""
use case:
bash history used multiple times in SCT
solution:
separate bash history info update

use case:
bash history is not empty from earlier session
solution:
update info in PEC or exercise init

use case:
bash history is not empty from an exercise that didn't use this SCT
solution:
update info in PEC or exercise init

If updating info in PEC, only use bash history in check_correct
as it only has access to the latest commands
"""


def update_bash_history_info(bash_history_path=None):
    """Store initial info about the bash history

    ``get_bash_history`` can use this info to get the relevant commands

    This function can be called when starting an exercise or every time it is submitted
    """
    if bash_history_path is None:
        bash_history_path = os.environ[BASH_HISTORY_PATH_ENV]
    with open(bash_history_path, encoding="utf-8") as f:
        Path(os.environ[BASH_HISTORY_INFO_PATH_ENV]).write_text(
            str(len(f.readlines())), encoding="utf-8"
        )


def get_bash_history(
    full_history=False, bash_history_path=None
):
    """Get the commands in the bash history

    :param full_history: if true, returns all commands in the bash history,
        else only return the relevant commands based on bash history info
    :param bash_history_path: path to the bash history file
    :return: a list of commands (empty if the file is not found)
    """
    if bash_history_path is None:
        bash_history_path = os.environ[BASH_HISTORY_PATH_ENV]
    try:
        with open(bash_history_path, encoding="utf-8") as f:
            history = f.readlines()
            old_history_length = int(
                Path(os.environ[BASH_HISTORY_INFO_PATH_ENV]).read_text()
            )
            return history if full_history else history[old_history_length:]
    except FileNotFoundError:
        return []


def has_command(state, pattern, msg, fixed=False, commands=None):
    """Test whether the bash history has a command matching the pattern

    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        pattern : text that command must contain (can be a regex pattern or a simple string)
        msg: feedback message if no matching command is found
        fixed: whether to match text exactly, rather than using regular expressions
        commands: the bash history commands to check against

    Note:
        If the bash history info is updated every time code is submitted,
        it's advised to only use this function as the second part of a check_correct
        to help students debug the command they haven't correctly run yet.
        If the bash history info is updated at the start of an exercise,
        this can be used everywhere as the (cumulative) commands from all submissions are known.

    """
    if commands is None:
        commands = get_bash_history()
    if not commands:
        state.report("Looking for an executed shell command, we didn't find any.")
    if not state.is_root:
        raise InstructorError(
            "`has_command()` should only be called from the root state, `Ex()`."
        )

    correct = False
    for command in commands:
        # similar to has_code
        if pattern in command if fixed else re.search(pattern, command):
            correct = True
            break

    if not correct:
        state.report(msg)

    return state


"""
Other SCTs using bash history as the code?

Option 1
- only 'multi': all commands need to pass SCT
- ugly code using internals

commands = get_bash_history()
for command in commands:
    Ex(Ex()._state.to_child(student_code=command)).has_code()

Option 2
new general (dangerous?) SCT to solve limitations:
alternative: override() SCT with optional student_code argument (safer?)

def update(state, **kwargs):
    return state.to_child(**kwargs)

Use cases:
equivalent of `Ex().has_command(commands, pattern)`:
Ex().check_or(*[update(student_code=command).has_code(pattern) for command in commands])


shellwhat parsing of bash history:
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

"""
SCT hooks?
let backend call an init function on exercise start
+ xwhat calls protowhat init / register init handlers
"""
