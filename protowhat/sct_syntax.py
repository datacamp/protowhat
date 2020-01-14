import inspect
from functools import wraps, reduce
from itertools import chain as chain_iters
from typing import Callable, Dict, Optional, List

from protowhat.State import State
from protowhat.failure import Failure, InstructorError, _debug


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
