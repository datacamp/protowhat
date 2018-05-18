protowhat
---------

``protowhat`` is a utility package required by ``sqlwhat`` and ``shellwhat`` packages,
used for writing Submission Correctness Tests SCTs for interactive Shell and SQL exercises on DataCamp.
It contains shared functionality related to SCT syntax and selectors, state manipulation and commonly used functions.

- If you are new to teaching on DataCamp, check out https://authoring.datacamp.com.
- If you want to learn what SCTs are and how they work, visit https://authoring.datacamp.com/courses/sct.html.

This documentation takes a deeper dive into the chaining syntax employed for SCTs and
contains reference documentation of all relevant SCT functions.
If you are new to writing SCSTs for SQL or Shell exercises,
read the Syntax section below first before embarking onto
the reference documentation or the ```sqlwhat`` (`link <https://sqlwhat.readthedocs.io>`_) and ``shellwhat`` (`link <https://shellwhat.readthedocs.io>`_) dedicated docs.

Syntax
======

``protowhat`` (and by extension ``sqlwhat`` and ``shellwhat``, as they depend on ``protowhat``) start from the concept of an exercise state.
This exercise state can be accessed with ``Ex()`` and contains all the information that is required to check if an exercise is correct:

1. the student submission and the solution as text and their corresponding abstract syntax trees.
2. a reference to the student coding session and the solution coding session.
3. the results, output and errors that were generated when executing the student code.

Currently, as coding sessions and result formatting and parsing is very different between SQL an Shell,
``protowhat`` is only concerned with the student submission and solution code as text and their corresponding syntax trees (AST).
For SCT functions related to checking results and output, consult the docs of ``sqlwhat`` and ``shellwhat``.

Abastract Syntax tree (AST)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The abstract syntax tree is a parsed tree representations of a code submission. To better understand what this means, visit `this AST viewer app <https://ast-viewer.new.datacamp.com>`_
In editor mode, you can include a snippet of code, specify the parser it should use, and generate the parse tree. As an example, this PostgreSQL code

.. code:: sql

    SELECT id FROM artists WHERE id > 100

is first parsed into a complex-looking parse tree, and then restructured into an abstract syntax tree that looks like this:

.. image:: ast_example.png
   :align: center

Notice how the statement is neatly chopped up into its consituents: the ``SELECT`` statement is chopped up into three parts:
the ``target_list`` (which columsnt o select), the ``from_clause`` (from which table to select) and the ``where_clause`` (the condition that has to be satisfied).
Next, the ``where_caluse`` is a ``BinaryExpr`` that is further chopped up.

Chaining
~~~~~~~~

The root exercise state, that contains the entire student submission and solution and their corresponding ASTs, is accessed with ``Ex()``.
From this ``Ex()`` call, you can 'chain together' SCT functions with the ``.`` operator.
As SCT functions are chained, the ``Ex()`` state is copied and adapted into so-called child states that zoom in on particular parts of the code.
In other words, by chaining calls, you're instructing ``protowhat`` how to walk down the AST.

Example
~~~~~~~

Consider the example above again and suppose you want to check whether students have correctly specified the table from which to select columns (the ``FROM artists`` part).
This SCT script does that:

.. code:

    Ex().check_node(state, "SelectStmt").check_field("from_clause").has_equal_ast()

We'll now explain step by step what happens when a student submits the following (incorrect) code:

.. code:: 

    SELECT id FROM producers WHERE id > 100

When the SCT executes:

- ``Ex()`` runs first, and fetches the root state that considers the entire student submission and solution:

    .. code::

        -- solution
        SELECT id FROM artists WHERE id > 100

        -- student
        SELECT id FROM producers WHERE id > 100

  This is the corresponding AST of the solution.
  This is the same tree as included earlier in this article.
  The AST for the student submission will look very similar.

  .. image:: ast_example2.png
     :align: center
     :scale: 80%

- Next, ``check_node()`` chains off of the state produced by ``Ex()`` and
  produces a child state that focuses on the ``SelectStmt`` portion of the submission and solution:

    .. code::

        -- solution
        SELECT id FROM artists WHERE id > 100

        -- student
        SELECT id FROM producers WHERE id > 100

  The corresponding AST of the solution is the following. Notice that although the textual representation is the same as ``Ex()``,
  the AST representation no longer includes the ``Script`` node. The AST for the student submission will look very similar.

  .. image:: ast_example2.png
     :align: center
     :scale: 80%

- Next, ``check_field()`` chains off of the state produced by ``check_node()`` and zooms in on the ``from_clause`` branch of the AST:

    .. code::

        -- solution
        artists 

        -- student
        producers

  The corresponding ASTs for solution and student are as follows:

  .. image:: ast_example3_combi.png
     :align: center
     :width: 300px

- Finally, ``has_equal_ast()`` chains off of the state produced by ``check_field()`` and
  checks whether the student submission and solution sub-ASTs correspond.
  As the solution expects ``artists`` while the student specified ``producers`` the SCT fails
  and ``protowhat`` will generate a meaningful feedback message.

.. note::

    Notice that we are using two different functions here: ``check_node()`` and ``check_field()``.
    As a rule, ``check_node()`` is used to select a `node` of the AST tree (a circle in the image).
    while ``check_field()`` is used to walk down a `branch` of the AST tree (a line in the image).

Reference Documentation
=======================

.. toctree::
   :maxdepth: 2

   reference
