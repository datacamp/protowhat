import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from protowhat.Feedback import InstructorError
from protowhat.Reporter import Reporter
from protowhat.State import State
from protowhat.Test import TestFail as TF
from protowhat.checks.check_bash_history import (
    BASH_HISTORY_PATH_ENV,
    BASH_HISTORY_INFO_PATH_ENV,
    update_bash_history_info,
    get_bash_history_info,
    get_bash_history,
    has_command,
)


@contextmanager
def setup_workspace():
    _environ = os.environ.copy()
    try:
        with tempfile.NamedTemporaryFile() as bash_history_path:
            os.environ[BASH_HISTORY_PATH_ENV] = bash_history_path.name
            with tempfile.NamedTemporaryFile() as bash_history_info_path:
                os.environ[BASH_HISTORY_INFO_PATH_ENV] = bash_history_info_path.name
                yield bash_history_path, bash_history_info_path
    finally:
        os.environ.clear()
        os.environ.update(_environ)


@pytest.fixture
def state():
    return State(
        # only Reporter and Dispatcher are used
        student_code="",
        solution_code="",
        reporter=Reporter(),
        pre_exercise_code="",
        student_result="",
        solution_result="",
        student_conn=None,
        solution_conn=None,
    )


def test_update_bash_history_info():
    with setup_workspace() as (bash_history_path, bash_history_info_path):
        update_bash_history_info()
        assert Path(bash_history_info_path.name).read_text() == "0"

        Path(bash_history_path.name).write_text("a command\nanother one")
        update_bash_history_info()
        assert Path(bash_history_info_path.name).read_text() == "2"


def test_update_bash_history_info_custom_location():
    with setup_workspace() as (bash_history_path, bash_history_info_path):
        with tempfile.NamedTemporaryFile() as custom_bash_history_path:
            update_bash_history_info(bash_history_path=custom_bash_history_path.name)
            assert Path(bash_history_info_path.name).read_text() == "0"

            Path(custom_bash_history_path.name).write_text("a command\nanother one")
            update_bash_history_info(bash_history_path=custom_bash_history_path.name)
            assert Path(bash_history_info_path.name).read_text() == "2"


def test_get_bash_history_info():
    with setup_workspace() as (bash_history_path, bash_history_info_path):
        Path(bash_history_path.name).write_text("a command\nanother one")
        update_bash_history_info()
        assert get_bash_history_info() == 2


def test_get_bash_history():
    with setup_workspace() as (bash_history_path, bash_history_info_path):
        Path(bash_history_path.name).write_text("old command")
        update_bash_history_info()
        assert get_bash_history() == []

        Path(bash_history_path.name).write_text("old command\na command\nanother one")
        assert get_bash_history() == ["a command\n", "another one"]


def test_get_bash_history_failure():
    with setup_workspace() as (bash_history_path, bash_history_info_path):
        os.environ[BASH_HISTORY_INFO_PATH_ENV] = 'info_file_not_created'
        Path(bash_history_path.name).write_text("old command\na command\nanother one")
        with pytest.raises(InstructorError, match="update_bash_history_info"):
            get_bash_history()


def test_get_bash_history_full():
    with setup_workspace() as (bash_history_path, bash_history_info_path):
        Path(bash_history_path.name).write_text("old command")
        update_bash_history_info()
        assert get_bash_history(full_history=True) == ["old command"]

        Path(bash_history_path.name).write_text("old command\na command\nanother one")
        assert get_bash_history(full_history=True) == [
            "old command\n",
            "a command\n",
            "another one",
        ]


def test_get_bash_history_custom_location():
    with setup_workspace():
        with tempfile.NamedTemporaryFile() as custom_bash_history_path:
            Path(custom_bash_history_path.name).write_text("old command")
            update_bash_history_info(bash_history_path=custom_bash_history_path.name)
            assert (
                get_bash_history(bash_history_path=custom_bash_history_path.name) == []
            )

            Path(custom_bash_history_path.name).write_text(
                "old command\na command\nanother one"
            )
            assert get_bash_history(
                bash_history_path=custom_bash_history_path.name
            ) == ["a command\n", "another one"]


def test_get_bash_history_absent():
    assert get_bash_history() == []


def test_has_command(state):
    with setup_workspace() as (bash_history_path, bash_history_info_path):
        update_bash_history_info()
        Path(bash_history_path.name).write_text("old command")
        has_command(state, "(a|b)+", "a and b are the best letters")


def test_has_command_no_commands(state):
    with setup_workspace():
        update_bash_history_info()
        with pytest.raises(TF, match="didn't find any"):
            has_command(state, "(a|b)+", "a and b are the best letters")


def test_has_command_failure(state):
    with setup_workspace() as (bash_history_path, bash_history_info_path):
        update_bash_history_info()
        Path(bash_history_path.name).write_text("wrong")
        with pytest.raises(TF, match="a and b"):
            has_command(state, "(a|b)+", "a and b are the best letters")


def test_has_command_fixed(state):
    with setup_workspace() as (bash_history_path, bash_history_info_path):
        update_bash_history_info()
        Path(bash_history_path.name).write_text("(a|b)+")
        has_command(state, "(a|b)+", "a and b are the best letters", fixed=True)


def test_has_command_custom_commands(state):
    with setup_workspace():
        update_bash_history_info()
        has_command(
            state, "(a|b)+", "a and b are the best letters", commands=["old command"]
        )
