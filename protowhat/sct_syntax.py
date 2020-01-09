import inspect
import builtins
from functools import wraps, reduce
from importlib import import_module
from itertools import chain as chain_iters
from typing import Type, Tuple, Callable, Dict, Any, Optional, List

from protowhat.Reporter import Reporter
from protowhat.State import State
from protowhat.failure import Failure, InstructorError, _debug
from protowhat.utils import get_class_parameters


def state_dec_gen(sct_dict: Dict[str, Callable]):
    def state_dec(f):
        """Decorate check_* functions to return F chain if no state passed"""

        @wraps(f)
        def wrapper(*args, **kwargs):
            state = kwargs.get("state", args[0] if len(args) else None)
            if isinstance(state, State):
                return f(*args, **kwargs)
            else:
                return LazyChain(
                    ChainedCall(f, args, kwargs), chainable_functions=sct_dict
                )

        return wrapper

    return state_dec


def get_check_name(check) -> str:
    # Probe objects have a test_name
    return getattr(check, "__name__", getattr(check, "test_name", type(check).__name__))


def link_to_state(check: Callable[..., State]) -> Callable[..., State]:
    @wraps(check)
    def wrapper(state, *args, **kwargs):
        new_state = None
        error = None
        should_debug = False
        try:
            new_state = check(state, *args, **kwargs)
        except Failure as exception:
            error = exception
            # TODO: add debug information to student failure in correct environment
            # Prevent double debugging
            # - by a manual debug call
            # - by a logic function capturing an inner debug (keeping only the debug conclusion)
            should_debug = (isinstance(error, InstructorError)) and get_check_name(
                check
            ) not in ["_debug", "multi", "check_correct", "check_or", "check_not"]

            if should_debug:
                # Try creating a child state to set creator info
                # without overriding earlier creator info
                try:
                    new_state = state.to_child(error.feedback.conclusion)
                except InstructorError:
                    pass

        if not new_state:
            new_state = state

        if new_state != state and hasattr(new_state, "creator"):
            ba = inspect.signature(check).bind(state, *args, **kwargs)
            ba.apply_defaults()
            new_state.creator = {
                "type": get_check_name(check),
                "args": {**(new_state.creator or {}).get("args", {}), **ba.arguments},
            }

        if error:
            if should_debug:
                # The force flag prevents elevating a student failure with debugging info
                # to InstructorError, which would break SCTs
                _debug(
                    new_state,
                    "\n\nDebug on error:",
                    force=isinstance(error, InstructorError),
                )

            raise error

        return new_state

    return wrapper


class ChainedCall:
    strict = False
    __slots__ = ("callable", "args", "kwargs")

    def __init__(
        self,
        callable_: Callable,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
    ):
        """
        Data for a function call that can be chained
        This means the chain state should only be provided when calling.
        """
        self.callable = link_to_state(callable_)
        self.args = args or ()
        self.kwargs = kwargs or {}
        if self.strict:
            self.validate()

    def validate(self):
        pass

    def __call__(self, state: State) -> State:
        return self.callable(state, *self.args, **self.kwargs)

    def __str__(self):
        if isinstance(self.callable, LazyChain):
            return str(self.callable)
        else:
            return (
                self.callable.__name__
                + "("
                + ", ".join(
                    chain_iters(
                        (str(arg) for arg in self.args),
                        (
                            "{}={}".format(kwarg, value)
                            for kwarg, value in self.kwargs.items()
                        ),
                    )
                )
                + ")"
            )


class Chain:
    empty_call_str = ""

    def __init__(
        self,
        chained_call: Optional[Callable] = None,
        previous: Optional["Chain"] = None,
        chainable_functions: Dict[str, Callable] = None,
    ):
        if not chained_call and previous:
            raise ValueError("After the start of a chain a call is required")

        self.call = chained_call
        self.previous = previous
        self.next = []

        if self.previous:
            previous.next.append(self)

        if chainable_functions:
            self.chainable_functions = chainable_functions
        elif previous:
            self.chainable_functions = previous.chainable_functions
        else:
            self.chainable_functions = {}

    @property
    def _history(self) -> list:
        return getattr(self.previous, "_history", []) + [self]

    def __getattr__(self, attr):
        chainable_functions = self.chainable_functions
        if attr not in chainable_functions:
            if attr not in ("_history",):  # todo
                raise AttributeError("No function named %s" % attr)
            return self.__getattribute__(attr)
        else:
            # in case someone does: a = chain.a; a(...); a(...)
            return ChainExtender(self, chainable_functions[attr])

    def __rshift__(self, f: Callable) -> "Chain":
        if isinstance(f, EagerChain):
            raise BaseException(
                "did you use a result of the Ex() function on the right hand side of the >> operator?"
            )
        elif not callable(f):
            raise BaseException("right hand side of >> operator should be callable!")

        # wrapping the lazy chain makes it possible to reuse lazy chains
        # while still keeping a unique upstream chain (needed to lazily execute chains)
        # during execution, the state provides access to the full upstream context for an invocation
        return type(self)(f, self)

    def __call__(self, state) -> State:
        # running the chain (multiple runs possible)
        return reduce(
            lambda s, call: call(s),
            (chain.call for chain in self._history if chain.call is not None),
            state,
        )

    def __str__(self):
        return ".".join(
            str(step.call) for step in self._history if step.call is not None
        )


class LazyChain(Chain):
    """
    This is an alias for Chain
    It is useful to refer to 'pure' chains in instance checks and type hints
    """

    pass


class EagerChain(Chain):
    def __init__(
        self,
        chained_call: Optional[Callable] = None,
        previous: Optional["EagerChain"] = None,
        chainable_functions: Dict[str, Callable] = None,
        state: Optional[State] = None,
    ):
        super().__init__(chained_call, previous, chainable_functions)
        if previous is not None and state is not None:
            raise ValueError(
                "State should be set at the start. "
                "After that a reference to the previous part of the chain is needed."
            )

        if previous:
            state = previous._state

        if state and chained_call:
            self._state = chained_call(state)
        else:
            self._state = state

    def __str__(self):
        if self.call is None:
            result = "Ex()"
        else:
            result = str(self.call)

        if len(result) and len(self.next) > 0:
            result += "."

        if len(self.next) == 1:
            result += str(self.next[0])
        elif len(self.next) > 1:
            result += "multi({})".format(", ".join(map(str, self.next)))

        return result


class ChainExtender:
    """
    This handles branching off (multiple next)
    either from a Chain or a chain attribute
    """

    def __init__(self, chain: Chain, function: Callable):
        self.chain = chain
        self.function = function

    def __call__(self, *args, **kwargs) -> Chain:
        return type(self.chain)(
            ChainedCall(self.function, args, kwargs), previous=self.chain
        )

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


def get_chain_ends(chain: Chain) -> List[Chain]:
    if chain.next:
        return [*chain_iters(*(get_chain_ends(branch) for branch in chain.next))]
    else:
        return [chain]


class ChainStart:
    """Create new chains and keep track of the created chains"""

    def __init__(self, chainable_functions: Dict[str, Callable]):
        self.chain_roots = []
        self.chainable_functions = chainable_functions

    def __call__(self) -> Chain:
        """Create a new chains and store it"""
        raise NotImplementedError()

    def register_chainable_function(self, function: Callable, name: str = None):
        name = name if name is not None else function.__name__
        self.chainable_functions[name] = function


class LazyChainStart(ChainStart):
    def __call__(self) -> LazyChain:
        chain_root = LazyChain(chainable_functions=self.chainable_functions)
        self.chain_roots.append(chain_root)

        return chain_root

    def __str__(self):
        return "\n".join(
            str(chain_end)
            for chain_end in chain_iters(
                *(get_chain_ends(root) for root in self.chain_roots)
            )
        )


class ExGen(ChainStart):
    def __init__(self, sct_dict: Dict[str, Callable], root_state, strict=True):
        super().__init__(sct_dict)
        self.root_state = root_state
        self.strict = strict

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
        if self.strict and state is None and self.root_state is None:
            raise Exception("explicitly pass state to Ex, or set Ex.root_state")

        chain_root = EagerChain(
            chainable_functions=self.chainable_functions,
            state=state or self.root_state,
        )
        self.chain_roots.append(chain_root)

        return chain_root

    def __str__(self):
        return "\n".join(str(root) for root in self.chain_roots)


def get_checks_dict(checks_module) -> Dict[str, Callable]:
    return {
        k: v
        for k, v in vars(checks_module).items()
        if k not in builtins.__dict__
        if not k.startswith("__")
        if callable(v)
    }


def create_sct_context(sct_dict, root_state: State = None) -> Dict[str, Callable]:
    """
    Create the globals that will be available when running the SCT.

    Args:
        sct_dict: a dictionary of the functions to make available
        root_state: a State instance with the exercise information available to the SCT

    Returns:
        dict: the globals available to the SCT code
    """
    state_dec = state_dec_gen(sct_dict)
    sct_ctx = {k: state_dec(v) for k, v in sct_dict.items()}

    ctx = {
        **sct_ctx,
        "state_dec": state_dec,  # needed by ext packages
        "Ex": ExGen(sct_dict, root_state),
        "F": LazyChainStart(sct_dict),
    }

    return ctx


def create_embed_state(
    xstate: Type[State],
    parent_state: State,
    derive_custom_state_args: Callable[[State], Dict[str, Any]] = None,
) -> State:
    """
    Create the state for running checks in the embedded technology.

    This function also connects the created state with the state of the host technology.

    Args:
        xstate: the State class of the embedded technology
        parent_state: state of the host technology to derive the embedded state from
        derive_custom_state_args: function to calculate instructor ovextra arguments to pass to the constructor of the embedded state

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
    args["reporter"] = Reporter(parent_state.reporter)

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


def create_embed_context(technology: str, context: EagerChain, **kwargs):
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

    return create_sct_context(xwhat_scts, root_state=embed_state)


def get_embed_chain_constructors(*args, **kwargs) -> Tuple[Type, Type]:
    """
    Get the chain constructors for the embedded technology.

    This is a wrapper around create_embed_context

    Returns:
        tuple: Ex and F for the embedded xwhat
    """
    new_context = create_embed_context(*args, **kwargs)
    return new_context["Ex"], new_context["F"]
