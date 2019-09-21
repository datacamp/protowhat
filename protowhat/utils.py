from functools import wraps


def legacy_signature(**kwargs_mapping):
    """
    This decorator makes it possible to call a function using old argument names
    when they are passed as keyword arguments.

    @legacy_signature(old_arg1='arg1', old_arg2='arg2')
    def func(arg1, arg2=1):
        return arg1 + arg2

    func(old_arg1=1) == 2
    func(old_arg1=1, old_arg2=2) == 3
    """

    def signature_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            redirected_kwargs = {
                kwargs_mapping[k] if k in kwargs_mapping else k: v
                for k, v in kwargs.items()
            }
            return f(*args, **redirected_kwargs)

        return wrapper

    return signature_decorator
