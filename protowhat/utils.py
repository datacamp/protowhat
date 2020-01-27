import itertools
from functools import wraps
from inspect import signature, Parameter
from typing import Type, Iterator, Callable, Dict


def get_class_parameters(cls: Type) -> Iterator[str]:
    """
    Get an iterator over all arguments that can be used to construct a class.

    This works for class hierarchies that have compatible constructors.

    Args:
        cls: class to inspect constructor parameters in class hierarchy for

    Returns:
        Iterator over parameter names
    """
    return itertools.chain(
        *(get_class_parameters(cls) for cls in cls.__bases__),
        (
            name
            for name, param in signature(cls).parameters.items()
            if param.kind is not Parameter.VAR_POSITIONAL
            and param.kind is not Parameter.VAR_KEYWORD
        )
    )


def parameters_attr(cls: Type) -> Type:
    """Add a parameters attribute to the class with all arguments that can be used to construct it.

    Why?
    - calculated once: not manual list, not built every init
    - accessible on class: not only usable on instances
    - set difference between vars() and parameters doesn't include this class attribute
    - more noticeable than manually setting attribute after class definition

    Args:
        cls: class to add parameters attribute to

    Returns:
        cls: modified class
    """
    cls.parameters = list(get_class_parameters(cls))
    return cls


def legacy_signature(
    **kwargs_mapping: Dict[str, str]
) -> Callable[[Callable], Callable]:
    """
    This decorator makes it possible to call a function using old argument names
    when they are passed as keyword arguments.

    :Example:

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
