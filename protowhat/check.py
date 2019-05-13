import re

from protowhat.State import State


class Check:
    # docs should be generated based on __init__ signature documentation (without self)
    #
    # SCT code = SCTON: SCT Object Notation
    # SCT is run lazily to get data structure, serialized to JSON, used in UI
    # UI generates JSON, JSON deserialized as DT (Data Tree), repr is SCT code
    #
    # top level = OrderedDict of chains
    # - order = code order
    # - key = variable name / Chain hash for unnamed vars
    # - value = Chain
    # Ex and lazy chain creation register chains in list
    # after SCT matching variable names to items in list to create OrderedDict
    #
    # for complex SCTs: either no UI support or... (later)
    # before running SCT to generate data structure, wrap non-reversible repr parts
    #  functions, objects...
    # AST transform: backwards compatible, easier use
    # manual wrapper: less magic, compatibility, usability?
    #
    # init unwraps, stores repr and executes (inspect.getsource | dill.source.getsource)
    # repr uses custom repr for properties that have one
    def __init__(self, properties):
        # order of arguments, positional vs kwarg and set vs default not preserved
        # solve using __new__ or decorator(*args, **kwargs) around init
        # shortcut decorator code based on Check class property for execution performance?
        #  e.g. Check.reversible = False?
        for k, v in properties.items():
            if k != "self":
                setattr(self, k, v)

        # alternative: Chain = a DT node with two properties: check and then[]?
        # + name property for the variable to which they are assigned?
        # __repr__: ".".join([repr(check) for check in checks]) + then
        # (no) difference between Chain and lazy chain in DT?
        self.then = []

    # decorator to store state check was called with
    def call(self, state: State) -> State:
        raise NotImplementedError

    def __repr__(self):
        # Ex and logic checks need a custom repr
        # that should also detect lazy chain reuse
        # and handle functions returning lazy chains
        this = "{}({})".format(
            pascal_to_snake(self.__class__.__name__),
            ",".join(
                [
                    # get code for non-xwhat objects
                    #  e.g. in single process exercise
                    # repr works for basic types (~ JSON)
                    # not for functions and objects
                    #  store code on construction?
                    "{}={}".format(k, repr(v))
                    for k, v in vars(self).items()
                    # to Chain
                    if k != "then"
                ]
            ),
        )

        # or part of Chain functionality?
        if self.then:
            if len(self.then) > 1:
                # e.g. if chain is stored in a variable
                this += ".multi({})"
            else:
                this += ".{}"

            next_chains = []
            for check in self.then:
                next_chains.append(repr(check))

            this = this.format(", ".join(next_chains))

        return this


def pascal_to_snake(cls_name):
    return re.sub("(?!^)([A-Z]+)", r"_\1", cls_name).lower()


if __name__ == "__main__":

    class A(Check):
        def __init__(self, test, one, two="3"):
            super().__init__(locals())

        def call(self, state):
            return state

    a = A("test", 1, "2")
    b = A("test", 1)

    print(a)
    a.then.append(b)
    print(a)
