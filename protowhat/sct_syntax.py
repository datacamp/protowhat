import inspect
import copy
import builtins
from contextlib import contextmanager
from functools import wraps, reduce, partial
from typing import Union, Type, Callable, Dict, Any

from protowhat.Reporter import Reporter
from protowhat.State import State


def state_dec_gen(state_cls: Type[State], attr_scts):
    def state_dec(f):
        """Decorate check_* functions to return F chain if no state passed"""

        @wraps(f)
        def wrapper(*args, **kwargs):
            state = kwargs.get("state", args[0] if len(args) else None)
            if isinstance(state, state_cls):
                return f(*args, **kwargs)
            else:
                return F._from_func(f, *args, _attr_scts=attr_scts, **kwargs)

        return wrapper

    return state_dec


def link_to_state(check: Callable[..., State]) -> Callable[..., State]:
    @wraps(check)
    def wrapper(state, *args, **kwargs):
        new_state = check(state, *args, **kwargs)
        if (
            new_state != state
            and hasattr(new_state, "creator")
            and not isinstance(check, F)
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
        elif isinstance(f, Chain) and not isinstance(f, F):
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


class F(Chain):
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


def get_checks_dict(checks_module):
    return {
        k: v
        for k, v in vars(checks_module).items()
        if k not in builtins.__dict__
        if not k.startswith("__")
        if callable(v)
    }


def create_sct_context(state: Type[State], sct_dict, root_state=None):
    state_dec = state_dec_gen(state, sct_dict)
    sct_ctx = {k: state_dec(v) for k, v in sct_dict.items()}

    ctx = {
        **sct_ctx,
        "state_dec": state_dec,  # needed by ext packages
        "Ex": ExGen(root_state, sct_ctx),
        "F": partial(F, attr_scts=sct_ctx),
    }

    return ctx


def create_embed_state(
    parent_state: State,
    xstate: Type[State],
    state_args: Dict[str, Any] = None,
    highlight_offset: dict = None,
):
    # handle xstate args/kwargs
    embedded_state_params = [
        param
        for cls in [xstate, *xstate.__bases__]
        for param in inspect.signature(cls).parameters
    ]

    args = {}
    for arg in embedded_state_params:
        if hasattr(parent_state, arg):
            args[arg] = getattr(parent_state, arg)

    args.update(
        {
            **(state_args or {}),
            "reporter": Reporter(
                parent_state.reporter, highlight_offset=highlight_offset or {}
            ),
        }
    )

    return xstate(**args)


def create_embed_context(context: Chain, technology: str, **kwargs):
    parent_state = context._state

    xwhat = __import__("{}what".format(technology))

    xstate = xwhat.State.State

    embedded_state = create_embed_state(parent_state, xstate, **kwargs)

    return create_sct_context(
        xstate, xwhat.sct_syntax.sct_dict, root_state=embedded_state
    )


def get_embed_chain_constructors(*args, **kwargs):
    new_context = create_embed_context(*args, **kwargs)
    return new_context["Ex"], new_context["F"]


@contextmanager
def embed_xwhat(*args, **kwargs):
    globals_backup = globals().copy()

    new_context = create_embed_context(*args, **kwargs)
    EmbeddedEx = new_context["Ex"]
    EmbeddedF = new_context["F"]

    globals().update(new_context)
    yield EmbeddedEx, EmbeddedF
    globals().update(globals_backup)


# removed snippets
# parent_state_params = inspect.signature(parent_state.__class__)
# new_context = xwhat.sct_syntax.SCT_CTX
# EmbeddedEx.root_state = embedded_state
