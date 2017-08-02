import re
import _ast

class Feedback(object):

   def __init__(self, message, astobj = None, strict=False):
        self.message = message
        self.line_info = {}
        try:
            if astobj is not None:
                self.line_info = astobj._get_pos()
        except Exception as e:
            if strict: raise e

class TestFail(Exception):
    pass
