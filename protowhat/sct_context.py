import builtins

from functools import wraps
from importlib import import_module
from typing import Dict, Callable, Type, Any, Tuple

from protowhat.Reporter import Reporter
from protowhat.State import State
from protowhat.sct_syntax import (
    ExGen,
    LazyChainStart,
    EagerChain,
    state_dec_gen,
)
from protowhat.utils import get_class_parameters


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
        derive_custom_state_args: function to calculate instructor extra arguments to pass to the constructor of the embedded state

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
