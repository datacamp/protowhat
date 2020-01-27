import os
import re

from pathlib import Path

from protowhat.failure import InstructorError, debugger

# env vars
BASH_HISTORY_PATH_ENV = "BASH_HISTORY_PATH"
BASH_HISTORY_INFO_PATH_ENV = "BASH_HISTORY_INFO"

# env var defaults
os.environ[BASH_HISTORY_PATH_ENV] = os.environ.get(
    BASH_HISTORY_PATH_ENV, "/home/repl/.bash_history"
)
os.environ[BASH_HISTORY_INFO_PATH_ENV] = os.environ.get(
    BASH_HISTORY_INFO_PATH_ENV, "/home/repl/.bash_history_info"
)


def update_bash_history_info(bash_history_path=None):
    """Store the current number of commands in the bash history

    ``get_bash_history`` can use this info later to get only newer commands.

    Depending on the wanted behaviour this function should be called
    at the start of the exercise or every time the exercise is submitted.

    Import using ``from protowhat.checks import update_bash_history_info``.
    """
    if bash_history_path is None:
        bash_history_path = os.environ[BASH_HISTORY_PATH_ENV]
    with open(bash_history_path, encoding="utf-8") as f:
        Path(os.environ[BASH_HISTORY_INFO_PATH_ENV]).write_text(
            str(len(f.readlines())), encoding="utf-8"
        )


def get_bash_history_info():
    try:
        old_history_length = int(
            Path(os.environ[BASH_HISTORY_INFO_PATH_ENV]).read_text()
        )
    except FileNotFoundError:
        raise InstructorError.from_message("`update_bash_history_info` wasn't called")

    return old_history_length


def get_bash_history(full_history=False, bash_history_path=None):
    """Get the commands in the bash history

    Args:
        full_history (bool): if true, returns all commands in the bash history,
            else only return the commands executed after the last bash history info update
        bash_history_path (str | Path): path to the bash history file

    Returns:
        a list of commands (empty if the file is not found)

    Import from ``from protowhat.checks import get_bash_history``.
    """
    if bash_history_path is None:
        bash_history_path = os.environ[BASH_HISTORY_PATH_ENV]
    try:
        with open(bash_history_path, encoding="utf-8") as f:
            history = f.readlines()
            old_history_length = get_bash_history_info()
            return history if full_history else history[old_history_length:]
    except FileNotFoundError:
        return []


"""
Design considerations

use case:
bash history used multiple times in SCT
solution:
separate bash history info update

use case:
bash history is not empty from earlier exercise or session (that might not use this SCT)
solution:
update info in PEC or exercise init

If updating bash history info in PEC, only use bash history in check_correct
as it only has access to the latest commands
"""


def has_command(state, pattern, msg, fixed=False, commands=None):
    """Test whether the bash history has a command matching the pattern

    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        pattern: text that command must contain (can be a regex pattern or a simple string)
        msg: feedback message if no matching command is found
        fixed: whether to match text exactly, rather than using regular expressions
        commands: the bash history commands to check against.
            By default this will be all commands since the last bash history info update.
            Otherwise pass a list of commands to search through, created by calling the helper function
            ``get_bash_history()``.

    Note:
        The helper function ``update_bash_history_info(bash_history_path=None)``
        needs to be called in the pre-exercise code in exercise types that don't have
        built-in support for bash history features.

    Note:
        If the bash history info is updated every time code is submitted
        (by using ``update_bash_history_info()`` in the pre-exercise code),
        it's advised to only use this function as the second part of a ``check_correct()``
        to help students debug the command they haven't correctly run yet.
        Look at the examples to see what could go wrong.

        If bash history info is only updated at the start of an exercise,
        this can be used everywhere as the (cumulative) commands from all submissions are known.

    :Example:

        The goal of an exercise is to use ``man``.

        If the exercise doesn't have built-in support for bash history SCTs,
        update the bash history info in the pre-exercise code::

            update_bash_history_info()

        In the SCT, check whether a command with ``man`` was used::

            Ex().has_command("$man\s", "Your command should start with ``man ...``.")

    :Example:

        The goal of an exercise is to use ``touch`` to create two files.

        In the pre-exercise code, put::

            update_bash_history_info()

        This SCT can cause problems::

            Ex().has_command("touch.*file1", "Use `touch` to create `file1`")
            Ex().has_command("touch.*file2", "Use `touch` to create `file2`")

        If a student submits after running ``touch file0 && touch file1`` in the console,
        they will get feedback to create ``file2``.
        If they submit again after running ``touch file2`` in the console,
        they will get feedback to create ``file1``, since the SCT only has access
        to commands after the last bash history info update (only the second command in this case).
        Only if they execute all required commands in a single submission the SCT will pass.

        A better SCT in this situation checks the outcome first
        and checks the command to help the student achieve it::

            Ex().check_correct(
                check_file('file1', parse=False),
                has_command("touch.*file1", "Use `touch` to create `file1`")
            )
            Ex().check_correct(
                check_file('file2', parse=False),
                has_command("touch.*file2", "Use `touch` to create `file2`")
            )

    """
    if commands is None:
        commands = get_bash_history()
    if not commands:
        state.report("Looking for an executed shell command, we didn't find any.")
    if not state.is_root:
        with debugger(state):
            state.report(
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
# Other SCTs using bash history as the code?

## Option 1

use existing functionality
- ugly code using internals
- only 'multi': all commands need to pass SCT

```py
commands = get_bash_history()
for command in commands:
    Ex(Ex()._state.to_child(student_code=command)).has_code()
```

## Option 2

new general (dangerous?) ``update`` SCT to override arbitrary State attributes
alternative: update `override()` SCT with optional `student_code` argument (safer)

```py
def update(state, **kwargs):
    return state.to_child(**kwargs)
```

### Use cases:

- equivalent of `Ex().has_command(commands, pattern)`:
```py
Ex().check_or(*[update(student_code=command).has_code(pattern) for command in commands])
```


- shellwhat parsing of bash history:
```py
Ex().check_or(
    *[
        update(student_code=command)
        .check_node(node_name)
        .check_edge(edge_name)
        .has_equal_ast()
        for command in commands
    ]
)
```
"""

"""
SCT hooks?
let backend call an init function on exercise start
+ xwhat calls protowhat init / register init handlers
"""
