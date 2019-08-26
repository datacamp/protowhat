import inspect
import builtins
from contextlib import contextmanager
from functools import wraps, reduce
from typing import Type, Tuple, Callable, Dict, Any, Optional

from protowhat.Reporter import Reporter
from protowhat.State import State


def state_dec_gen(state_cls: Type[State]):
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


Call = Tuple[Callable, list, dict]


def to_call(f: Callable) -> Call:
    return f, [], {}


class Chain:
    registered_scts = {}

    def __init__(self, call: Optional[Call] = None, previous: Optional["Chain"] = None):
        self.call = call
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

    def __rshift__(self, f: "LazyChain") -> "Chain":
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
        return type(self)(to_call(f), self)

    def __call__(self, *args, **kwargs) -> State:
        # running the chain (multiple runs possible)
        state = kwargs.get("state") or args[0]
        return reduce(
            lambda s, call: self._call_from_data(s, *call),
            (chain.call for chain in self._history if chain.call is not None),
            state,
        )

    @staticmethod
    def _call_from_data(state, f: Callable, args: list, kwargs: dict) -> State:
        return link_to_state(f)(state, *args, **kwargs)

    @classmethod
    def _from_func(
        cls, func: Callable, args: Optional[tuple] = None, kwargs: Optional[dict] = None
    ) -> "Chain":
        """Creates a function chain starting with the specified function and its arguments."""
        return cls((func, args or [], kwargs or {}))

    @property
    def _history(self) -> list:
        return getattr(self.previous, "_history", []) + [self]


class LazyChain(Chain):
    """
    This is an alias for Chain
    It is useful to refer to 'pure' chains in instance checks and type hints
    """

    pass


class EagerChain(Chain):
    def __init__(
        self,
        call: Optional[Call] = None,
        previous: Optional["EagerChain"] = None,
        state: Optional[State] = None,
    ):
        super().__init__(call, previous)
        if not call and previous:
            raise ValueError("After the start of a chain a call is required")
        if (previous is None) is (state is None):
            raise ValueError(
                "State should be set at the start. "
                "After that a reference to the previous part of the chain is needed."
            )

        if call:
            if previous:
                state = previous._state
            self._state = self._call_from_data(state, *call)
        else:
            self._state = state


class ChainExtender:
    """
    This handles branching off (multiple next)
    either from a Chain or a chain attribute
    """

    def __init__(self, chain: Chain, function: Callable):
        self.chain = chain
        self.function = function

    def __call__(self, *args, **kwargs) -> Chain:
        return type(self.chain)((self.function, args, kwargs), previous=self.chain)

    def __getattr__(self, item):
        self.invalid_next_step(item)

    def __rshift__(self, other):
        self.invalid_next_step(other)

    def invalid_next_step(self, next_step: str):
        raise AttributeError(
            "Expected a call of {} before {}. ".format(
                getattr(self.function, "__name__", repr(self.function)), next_step
            )
        )


class ExGen:
    def __init__(self, root_state):
        self.root_state = root_state

    def __call__(self, state=None) -> EagerChain:
        """Returns the current code state as an EagerChain instance.

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

        return EagerChain(None, state=state or self.root_state)


def get_checks_dict(checks_module):
    return {
        k: v
        for k, v in vars(checks_module).items()
        if k not in builtins.__dict__
        if not k.startswith("__")
        if callable(v)
    }


def create_sct_context(state_cls: Type[State], sct_dict, root_state=None):
    """
    Create the globals that will be available when running the SCT.

    Args:
        state_cls: the State class of the technology to create the context for
        sct_dict: a dictionary of the functions to make available
        root_state: a State instance with the exercise information available to the SCT

    Returns:
        dict: the globals available to the SCT code
    """
    state_dec = state_dec_gen(state_cls)
    LazyChain.register_scts(sct_dict)
    sct_ctx = {k: state_dec(v) for k, v in sct_dict.items()}

    ctx = {
        **sct_ctx,
        "state_dec": state_dec,  # needed by ext packages
        "Ex": ExGen(root_state),
        "F": LazyChain,
    }

    return ctx


def create_embed_state(
    parent_state: State,
    xstate: Type[State],
    state_args: Dict[str, Any] = None,
    highlight_offset: dict = None,
):
    """
    Create the state for running checks in the embedded technology.

    This function also connects the created state with the state of the host technology.

    Args:
        parent_state: state of the host technology to derive the embedded state from
        xstate: the State class of the embedded technology
        state_args: extra arguments to pass to the constructor of the embedded state
        highlight_offset: position of the embedded code in the student code

    Returns:
        an instance of xstate
    """
    # find all arguments the xstate constructor can handle
    embedded_state_params = [
        param
        for cls in [xstate, *xstate.__bases__]
        for param in inspect.signature(cls).parameters
    ]

    # gather the kwargs the xstate will be created with
    args = {}

    # copy all allowed arguments from the parent state
    for arg in embedded_state_params:
        if hasattr(parent_state, arg):
            args[arg] = getattr(parent_state, arg)

    # manually add / override arguments and
    # configure the reporter to collaborate with the parent state reporter
    args.update(
        {
            **(state_args or {}),
            "reporter": Reporter(
                parent_state.reporter, highlight_offset=highlight_offset or {}
            ),
        }
    )

    return xstate(**args)


def create_embed_context(context: EagerChain, technology: str, **kwargs):
    """
    Create the globals that will be available when running the checks for the embedded technology.

    Extra keyword arguments are passed to the constructor of the State for the embedded technology.

    Args:
        context: the Chain of the host technology
            the checks for the embedded technology will use as starting point
        technology: the name of the embedded technology (the x in xwhat)

    Returns:
        dict: the globals available to the SCT code for the embedded technology
    """
    parent_state = context._state

    xwhat = __import__("{}what".format(technology))

    xstate = xwhat.State.State

    embedded_state = create_embed_state(parent_state, xstate, **kwargs)

    return create_sct_context(
        xstate, xwhat.sct_syntax.sct_dict, root_state=embedded_state
    )


def get_embed_chain_constructors(*args, **kwargs):
    """
    Get the chain constructors for the embedded technology.

    This is a wrapper around create_embed_context
    """
    new_context = create_embed_context(*args, **kwargs)
    return new_context["Ex"], new_context["F"]


@contextmanager
def embed_xwhat(*args, **kwargs):
    """
    This context manager temporarily updates the globals to be those for the embedded technology.
    The context manager also returns the chain constructors for the embedded technology

    This is a wrapper around create_embed_context
    """
    globals_backup = globals().copy()

    new_context = create_embed_context(*args, **kwargs)
    EmbeddedEx = new_context["Ex"]
    EmbeddedF = new_context["F"]

    globals().update(new_context)
    yield EmbeddedEx, EmbeddedF
    globals().update(globals_backup)
