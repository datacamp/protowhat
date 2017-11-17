from pathlib import Path

def check_file(state, fname,
               msg = "Did you create a file named `{}`?",
               msg_is_dir = "Want to check a file named `{}`, but found a directory.",
               parse = True
               ):
    """Test whether file exists, and make its contents the student code.
    
    Note: this SCT fails if the file is a directory.
    """
    p = Path(fname)
    if not p.exists():
        state.do_test(msg.format(fname))

    if p.is_dir():
        state.do_test(msg_is_dir.format(fname))

    # TODO ast parsing?
    code = p.read_text()
    return state.to_child(
                student_code = code,
                student_ast  = state.ast_dispatcher.parse(code) if parse else None,
                fname = fname
                )


def test_dir(state, fname, msg = "Did you create a directory named `{}`?"):
    """Test whether a directory exists."""
    if not Path(fname).is_dir():
        state.do_test(msg.format(fname))

    return state

