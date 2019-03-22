from protowhat.utils import legacy_signature


def test_legacy_signature():
    @legacy_signature(old_arg1="arg1", old_arg2="arg2")
    def func(arg1, arg2=1):
        return arg1 + arg2

    assert func(1) == 2
    assert func(arg1=1) == 2
    assert func(old_arg1=1) == 2
    assert func(1, arg2=2) == 3
    assert func(1, old_arg2=2) == 3
    assert func(arg1=1, old_arg2=2) == 3
    assert func(old_arg1=1, arg2=2) == 3
    assert func(old_arg1=1, old_arg2=2) == 3
