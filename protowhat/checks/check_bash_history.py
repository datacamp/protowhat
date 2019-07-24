import os
import re

from pathlib import Path

# env vars
from protowhat.Feedback import InstructorError

BASH_HISTORY_PATH_ENV = "BASH_HISTORY_PATH"
BASH_HISTORY_INFO_PATH = "BASH_HISTORY_INFO"

# env var defaults
os.environ[BASH_HISTORY_PATH_ENV] = os.environ.get(
    BASH_HISTORY_PATH_ENV, "/home/repl/.bash_history"
)
os.environ[BASH_HISTORY_INFO_PATH] = os.environ.get(
    BASH_HISTORY_INFO_PATH, "/home/repl/.bash_history_info"
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


def update_bash_history_info():
    """Store initial info about the bash history

    ``get_bash_history`` can use this info to get the relevant commands

    This function can be called when starting an exercise or every time it is submitted
    """
    with open(os.environ[BASH_HISTORY_PATH_ENV], encoding="utf-8") as f:
        Path(os.environ[BASH_HISTORY_INFO_PATH]).write_text(
            str(len(f.readlines())), encoding="utf-8"
        )


def get_bash_history(
    full_history=False, bash_history_info_path=os.environ[BASH_HISTORY_INFO_PATH]
):
    try:
        with open(os.environ[BASH_HISTORY_PATH_ENV], encoding="utf-8") as f:
            history = f.readlines()
            old_history_length = int(Path(bash_history_info_path).read_text())
            return history if full_history else history[old_history_length:]
    except FileNotFoundError:
        return []


def has_command(state, pattern, msg, fixed=False, commands=get_bash_history()):
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

# SCT hooks?
let backend call an init function on exercise start
+ xwhat calls protowhat init / register init handlers
"""
