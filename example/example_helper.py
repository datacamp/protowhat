import ast
import inspect
import asttokens

class PythonAst:
    def get_text(self, code):
        atok = asttokens.ASTTokens(code, tree = self)
        return atok.get_text(self)

def patch_ast():
    # forces class to use PythonAst as a mixin
    # allows them to use get_text method
    for obj in ast.__dict__.values():
        if inspect.isclass(obj) and issubclass(obj, ast.AST):
            if obj == ast.AST or PythonAst in obj.__bases__: continue
            obj.__bases__ = obj.__bases__ + (PythonAst, )
            obj._priority = 0

    # add AstNode, and ParseError classes for Dispatcher
    ast.AstNode = PythonAst
    ast.ParseError = SyntaxError
