import inspect
import copy
import builtins
from functools import wraps, reduce, partial
from importlib import import_module
from typing import Union, Type, Callable, Dict, Any, Tuple

from protowhat.Reporter import Reporter
from protowhat.State import State
from protowhat.utils import get_class_parameters


def state_dec_gen(state_cls: Type[State], attr_scts):
    def state_dec(f):
        """Decorate check_* functions to return F chain if no state passed"""

        @wraps(f)
        def wrapper(*args, **kwargs):
            state = kwargs.get("state", args[0] if len(args) else None)
            if isinstance(state, state_cls):
                return f(*args, **kwargs)
            else:
                return LazyChain._from_func(f, *args, _attr_scts=attr_scts, **kwargs)

        return wrapper

    return state_dec


def link_to_state(check: Callable[..., State]) -> Callable[..., State]:
    @wraps(check)
    def wrapper(state, *args, **kwargs):
        new_state = check(state, *args, **kwargs)
        if (
            new_state != state
            and hasattr(new_state, "creator")
            and not isinstance(check, LazyChain)
        ):
            ba = inspect.signature(check).bind(state, *args, **kwargs)
            ba.apply_defaults()
            new_state.creator = {"type": check.__name__, "args": ba.arguments}

        return new_state

    return wrapper


class Chain:
    def __init__(self, state: Union[State, None], attr_scts=None):
        self._state = state
        self._crnt_sct = None
        self._waiting_on_call = False
        self._attr_scts = {} if attr_scts is None else attr_scts

    def _double_attr_error(self):
        raise AttributeError(
            "Did you forget to call a statement? "
            "e.g. Ex().check_list_comp.check_body()"
        )

    def __getattr__(self, attr):
        # Enable fast attribute access
        if attr == "_attr_scts":
            raise AttributeError("Prevent getattr recursion on copy")
        attr_scts = self._attr_scts
        if attr not in attr_scts:
            raise AttributeError("No SCT named %s" % attr)
        elif self._waiting_on_call:
            self._double_attr_error()
        else:
            # make a copy to return,
            # in case someone does: chain = chain_of_checks; chain.a; chain.b
            return self._sct_copy(attr_scts[attr])

    def __call__(self, *args, **kwargs):
        self._state = link_to_state(self._crnt_sct)(self._state, *args, **kwargs)
        self._waiting_on_call = False
        return self

    def __rshift__(self, f):
        if self._waiting_on_call:
            self._double_attr_error()
        elif isinstance(f, Chain) and not isinstance(f, LazyChain):
            raise BaseException(
                "did you use a result of the Ex() function on the right hand side of the >> operator?"
            )
        elif not callable(f):
            raise BaseException(
                "right hand side of >> operator should be an SCT, so must be callable!"
            )
        else:
            chain = self._sct_copy(f)
            return chain()

    def _sct_copy(self, f):
        chain = copy.copy(self)
        chain._crnt_sct = f
        chain._waiting_on_call = True
        return chain


class LazyChain(Chain):
    def __init__(self, stack=None, attr_scts=None):
        super().__init__(None, attr_scts)
        self._stack = [] if stack is None else stack

    def __call__(self, *args, **kwargs):
        if self._crnt_sct:
            # calling an SCT function (after attribute access)
            call_data = (self._crnt_sct, args, kwargs)
            return self.__class__(self._stack + [call_data], self._attr_scts)
        else:
            # running the chain
            state = kwargs.get("state") or args[0]
            return reduce(
                lambda s, cd: self._call_from_data(s, *cd), self._stack, state
            )

    @staticmethod
    def _call_from_data(state, f, args, kwargs):
        return link_to_state(f)(state, *args, **kwargs)

    @classmethod
    def _from_func(cls, f, *args, _attr_scts=None, **kwargs):
        """Creates a function chain starting with the specified SCT (f), and its arguments."""
        func_chain = cls(attr_scts=_attr_scts)
        func_chain._stack.append([f, args, kwargs])
        return func_chain


class ExGen:
    def __init__(self, root_state, attr_scts):
        self.root_state = root_state
        self.attr_scts = attr_scts

    def __call__(self, state=None):
        """Returns the current code state as a Chain instance.

        This allows SCTs to be run without including their 1st argument, ``state``.

        When writing SCTs on DataCamp, no State argument to ``Ex`` is necessary.
        The exercise State is built for you.

        Args:
            state: a State instance, which contains the student/solution code and results.

        :Example:

            code ::

                # How to write SCT on DataCamp.com
                Ex().has_code(text="SELECT id")

                # Experiment locally - chain off of Ex(), created from state
                state = SomeStateProducingFunction()
                Ex(state).has_code(text="SELECT id")

                # Experiment locally - no Ex(), create and pass state explicitly
                state = SomeStateProducingFunction()
                has_code(state, text="SELECT id")

        """
        if state is None and self.root_state is None:
            raise Exception("explicitly pass state to Ex, or set Ex.root_state")

        return Chain(state or self.root_state, attr_scts=self.attr_scts)


Ex = ExGen(None, {})


def get_checks_dict(checks_module) -> Dict[str, Callable]:
    return {
        k: v
        for k, v in vars(checks_module).items()
        if k not in builtins.__dict__
        if not k.startswith("__")
        if callable(v)
    }


def create_sct_context(
    state_cls: Type[State], sct_dict, root_state: State = None
) -> Dict[str, Callable]:
    """
    Create the globals that will be available when running the SCT.

    Args:
        state_cls: the State class of the technology to create the context for
        sct_dict: a dictionary of the functions to make available
        root_state: a State instance with the exercise information available to the SCT

    Returns:
        dict: the globals available to the SCT code
    """
    state_dec = state_dec_gen(state_cls, sct_dict)
    sct_ctx = {k: state_dec(v) for k, v in sct_dict.items()}

    ctx = {
        **sct_ctx,
        "state_dec": state_dec,  # needed by ext packages
        "Ex": ExGen(root_state, sct_ctx),
        "F": partial(LazyChain, attr_scts=sct_ctx),
    }

    return ctx


def create_embed_state(
    xstate: Type[State],
    parent_state: State,
    derive_custom_state_args: Callable[[State], Dict[str, Any]] = None,
    highlight_offset: dict = None,
) -> State:
    """
    Create the state for running checks in the embedded technology.

    This function also connects the created state with the state of the host technology.

    Args:
        xstate: the State class of the embedded technology
        parent_state: state of the host technology to derive the embedded state from
        derive_custom_state_args: function to calculate instructor ovextra arguments to pass to the constructor of the embedded state
        highlight_offset: position of the embedded code in the student code

    Returns:
        an instance of xstate
    """
    # gather the kwargs the xstate will be created with
    args = {}

    # find all arguments the xstate constructor can handle
    embedded_state_parameters = getattr(
        xstate, "parameters", get_class_parameters(xstate)
    )

    # copy all allowed arguments from the parent state
    for arg in embedded_state_parameters:
        if hasattr(parent_state, arg):
            args[arg] = getattr(parent_state, arg)

    # configure the reporter to collaborate with the parent state reporter
    args["reporter"] = Reporter(
        parent_state.reporter, highlight_offset=highlight_offset or {}
    )

    custom_args = (
        derive_custom_state_args(parent_state) if derive_custom_state_args else {}
    )

    # manually add / override arguments
    args.update(**custom_args)

    embed_state = xstate(**args)
    # TODO: other params? set manually through chain constructor or add State args
    # to pass: path, debug; don't pass: highlight, ast_dispatcher, params
    embed_state.creator = {"type": "embed", "args": {"state": parent_state}}

    return embed_state


def create_embed_context(technology: str, context: Chain, **kwargs):
    """
    Create the globals that will be available when running the checks for the embedded technology.

    Extra keyword arguments are passed to the constructor of the State for the embedded technology.

    Args:
        technology: the name of the embedded technology (the x in xwhat)
        context: the Chain of the host technology
            the checks for the embedded technology will use as starting point

    Returns:
        dict: the variables available to the SCT code for the embedded technology
    """
    parent_state = context._state

    xwhat = import_module("{}what".format(technology))
    xwhat_checks = import_module("{}what.checks".format(technology))
    xwhat_state = xwhat.State.State

    xwhat_scts = get_checks_dict(xwhat_checks)

    embed_state = create_embed_state(xwhat_state, parent_state, **kwargs)

    return create_sct_context(xwhat_state, xwhat_scts, root_state=embed_state)


def get_embed_chain_constructors(*args, **kwargs) -> Tuple[Type, Type]:
    """
    Get the chain constructors for the embedded technology.

    This is a wrapper around create_embed_context

    Returns:
        tuple: Ex and F for the embedded xwhat
    """
    new_context = create_embed_context(*args, **kwargs)
    return new_context["Ex"], new_context["F"]
