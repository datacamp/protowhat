from pathlib import Path

def check_file(state, fname,
               msg = "Did you create a file named `{}`?",
               msg_is_dir = "Want to check a file named `{}`, but found a directory."
               ):
    """Test whether file exists, and make its contents the student code.
    
    Note: this SCT fails if the file is a directory.
    """
    p = Path(fname)
    if not p.exists(fname):
        state.do_test(msg.format(fname))

    if p.isdir(fname):
        state.do_test(msg_is_dir.format(fname))

    # TODO ast parsing?
    return state.to_child(student_code = p.read_text())


def test_dir(state, fname, msg = "Did you create a directory named `{}`?"):
    """Test whether a directory exists."""
    if not Path(fname).isdir():
        state.do_test(msg.format(fname))

    return state

