import copy
from functools import wraps, reduce, partial


def state_dec_gen(State, attr_scts):
    def state_dec(f):
        """Decorate check_* functions to return F chain if no state passed"""

        @wraps(f)
        def wrapper(*args, **kwargs):
            state = kwargs.get("state", args[0] if len(args) else None)
            if isinstance(state, State):
                return f(*args, **kwargs)
            else:
                return F._from_func(f, *args, _attr_scts=attr_scts, **kwargs)

        return wrapper

    return state_dec


class Chain:
    def __init__(self, state, attr_scts=None):
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
            # in case someone does: a = chain.a; b = chain.b
            return self._sct_copy(attr_scts[attr])

    def __call__(self, *args, **kwargs):
        # NOTE: the only change from python what is that state is now 1st pos arg below
        self._state = self._crnt_sct(self._state, *args, **kwargs)
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
        self._crnt_sct = None
        self._stack = [] if stack is None else stack
        self._waiting_on_call = False
        self._attr_scts = {} if attr_scts is None else attr_scts

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
        return f(state, *args, **kwargs)

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


def create_sct_context(State, sct_dict, root_state=None):
    state_dec = state_dec_gen(State, sct_dict)
    sct_ctx = {k: state_dec(v) for k, v in sct_dict.items()}

    ctx = {
        **sct_ctx,
        "state_dec": state_dec,  # needed by ext packages
        "Ex": ExGen(root_state, sct_ctx),
        "F": partial(F, attr_scts=sct_ctx),
    }

    return ctx
