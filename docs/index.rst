protowhat
---------

protowhat is a utility package required by

- `sqlwhat <https://sqlwhat.readthedocs.io>`_ to write SCTs for SQL exercises, and
- `protowhat <https://shellwhat.readthedocs.io>`_ to write SCTs for Shell exercises.

protowhat contains functionality that is shared between these packages, including:

- SCT function chaining and syntactical sugar,
- State management,
- AST element selection, dispatching and message generation,
- Basic SCT functions such as ``success_msg()`` and ``has_chosen()``.

All relevent documentation to write SCTs for SQL and Shell exercises,
including functions that reside in ``protowhat``, can be found in the `sqlwhat <https://sqlwhat.readthedocs.io>`_ and `protowhat <https://shellwhat.readthedocs.io>`_ documentation.

.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference