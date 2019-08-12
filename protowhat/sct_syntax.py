import inspect
import builtins
from functools import wraps, reduce
from importlib import import_module
from typing import Union, Type, Callable, Dict, Any, Tuple, Optional

from protowhat.Reporter import Reporter
from protowhat.State import State
from protowhat.utils import get_class_parameters


def state_dec_gen(state_cls: Type[State], attr_scts):
    Chain.register_scts(attr_scts)  # todo

    def state_dec(f):
        """Decorate check_* functions to return F chain if no state passed"""

        @wraps(f)
        def wrapper(*args, **kwargs):
            state = kwargs.get("state", args[0] if len(args) else None)
            if isinstance(state, state_cls):
                return f(*args, **kwargs)
            else:
                return LazyChain._from_func(f, args, kwargs)

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


def to_sct_call(f: Callable):
    return f, [], {}


class Chain:
    registered_scts = {}

    def __init__(self, sct_call=None, previous: "Chain" = None):
        self.sct_call = sct_call
        self.previous = previous
        self.next = []

        if self.previous:
            previous.next.append(self)

    @classmethod
    def register_scts(cls, scts: Dict[str, Callable]):
        # todo: check for overrides?
        # this updates the attribute on Chain
        # registering through subclasses updates Chain
        cls.registered_scts.update(scts)

    def __getattr__(self, attr):
        registered_scts = self.registered_scts
        if attr not in registered_scts:
            if attr not in ("_history",):  # todo
                raise AttributeError("No SCT named %s" % attr)
            return self.__getattribute__(attr)
        else:
            # in case someone does: a = chain.a; a(...); a(...)
            return ChainExtender(self, registered_scts[attr])

    def __rshift__(self, f: "LazyChain"):
        if isinstance(f, EagerChain):
            raise BaseException(
                "did you use a result of the Ex() function on the right hand side of the >> operator?"
            )
        elif not callable(f):
            raise BaseException(
                "right hand side of >> operator should be an SCT, so must be callable!"
            )

        # wrapping the lazy chain makes it possible to reuse lazy chains
        # while still keeping a unique upstream chain (needed to lazily execute chains)
        return type(self)(to_sct_call(f), self)

    def __call__(self, *args, **kwargs) -> State:
        # running the chain (multiple runs possible)
        state = kwargs.get("state") or args[0]
        return reduce(
            lambda s, sct_call: self._call_from_data(s, *sct_call), self._history, state
        )

    @staticmethod
    def _call_from_data(state, f, args, kwargs):
        return link_to_state(f)(state, *args, **kwargs)

    @classmethod
    def _from_func(
        cls, func, args: Optional[tuple] = None, kwargs: Optional[dict] = None
    ):
        """Creates a function chain starting with the specified SCT (f), and its arguments."""
        return cls((func, args or [], kwargs or {}))

    @property
    def _history(self) -> list:
        if not self.sct_call:
            return []

        history = [self]
        previous = history[-1].previous
        while previous is not None and getattr(previous, "sct_call", None):
            history.append(previous)
            previous = history[-1].previous

        return list(reversed(list(map(lambda chain: chain.sct_call, history))))


class LazyChain(Chain):
    """
    This is an alias for Chain
    It is useful to refer to 'pure' chains in instance checks and type hints
    """
    pass


class EagerChain(Chain):
    def __init__(
        self,
        sct_call=None,
        previous: Optional["EagerChain"] = None,
        state: Optional[State] = None,
    ):
        super().__init__(sct_call, previous)
        if not sct_call and previous:
            raise ValueError("After the start of a chain a call is required")
        if (previous is None) is (state is None):
            raise ValueError(
                "State should be set at the start. "
                "After that a reference to the previous part of the chain is needed."
            )

        if sct_call:
            if previous:
                state = previous._state
            self._state = self._call_from_data(state, *sct_call)
        else:
            self._state = state


class ChainExtender:
    """
    This handles branching off (multiple next)
    either from a Chain or a chain attribute
    """

    def __init__(self, chain: Chain, sct: Callable):
        self.chain = chain
        self.sct = sct

    def __call__(self, *args, **kwargs) -> Chain:
        return type(self.chain)((self.sct, args, kwargs), previous=self.chain)

    def __getattr__(self, item):
        self.invalid_next_step(item)

    def __rshift__(self, other):
        self.invalid_next_step(other)

    def invalid_next_step(self, next_step):
        raise AttributeError(
            "Expected a call of {} before {}. ".format(
                getattr(self.sct, "__name__", repr(self.sct)), next_step
            )
        )


class ExGen:
    def __init__(self, root_state, attr_scts):
        self.root_state = root_state
        self.attr_scts = attr_scts  # todo

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

        Chain.register_scts(self.attr_scts)

        return EagerChain(None, state=state or self.root_state)


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
        "F": LazyChain,
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
