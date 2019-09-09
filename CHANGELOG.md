# Changelog

All notable changes to the protowhat project will be documented in this file.

## 1.12.0

- Add messaging helpers

## 1.11.2

- Proper handling of `ast.get_text` returning `None` in `has_code`

## 1.11.1

- Handle highlight position absence (in combination with `antlr-ast` v0.7.0)

## 1.11.0

- Add bash history SCTs
- Add `State.is_root` property
- Return file path in feedback if set

## 1.10.0

- Pass file path to SCT chain after `check_file`

## 1.9.0

- Add `allow_errors`

## 1.8.2

- Support unicode when checking files
- Fix disabling parsing file content

## 1.8.0

- `Feedback` doesn't need to be subclassed in depending SCT libraries.
- `_debug` now has an `on_error` argument which can be set to `True` to show debugging info
on the next failure or before finishing.
- No NumPy dependency
- Simplified `State.report`

## 1.7.0

This release improves the base functionality for all depending SCT libraries.

- Add `_debug` SCT introspection function
- Add `State.parent_state` and `State.state_history` as a general state linking mechanism (using `State.creator`)
- Add `TestRunner` and `TestRunnerProxy` and make `Reporter` a `TestRunnerProxy`
- Add AST and text offset support in `Runner`
- Improve `Dispatcher`, `Feedback` and `Test` interfaces

## 1.6.0

This release enables protowhat to be the base for pythonwhat.

- `do_test` now runs a `Test` as in pythonwhat, instead of accepting a feedback string.
- the explicit Fail subclass should be used instead of relying on the old default implementation of `Test`
- the `report(feedback: Feedback)` method on the `State` class reintroduces a short way to gather exercise feedback,
  equivalent to `do_test(Fail(Feedback(msg)))`, while also setting highlight info.
- the `legacy_signature` decorator enables to call a function using old argument names
  when they are passed as keyword arguments
- AST utils to dump and load a tree structure to be used in e.g. dispatching are improved

## 1.5.0

- Update parsing class interface for compatibility with antlr-ast
- Support finding dynamic nodes in AST tree (instead of just custom defined nodes)
- Change `ckeck_edge` default value of `index` argument from `None` to `0`
  - This is done to break less content
  - Now: explicitly define the value of the `index` argument
  - Later: revert default change and remove unnecessary explicit setting of the `index` argument

## 1.4.0

- Refactor based on refactor in `antlr-ast>=0.4.1`, `antlr-plsql>=0.7.0` and `antlr-tsql>=0.11.0`

## 1.3.0

- Support `force_diagnose` State option to force passing `diagnose` tests in `check_correct`.

## 1.2.0

- Update to work with new ANTLR library versions

## 1.1.2

- Fix in `has_code()` that was causing issues in some cases.

## 1.1.1

- Maintenance on docs.

## 1.1.0

- Update argument names and argument defaults for file-related checks.

## 1.0.2

- Re-exposing the `state_dec` object in the SCT context so it can be used by `shellwhat_ext` and `sqlwhat_ext`.

## 1.0.1

- In `shellwhat`, it is possible that `_msg` is None after calling `state.ast_dispatcher.describe`. This is now handled by including a default message for `_msg`.

## 1.0.0

**Contains breaking changes!**

### Added

- More tests
- `State` now has functionality to stack messages in an array, so you can prepend messages from earlier `check` functions, similar to `pythonwhat` (using Jinja)

### Changed

- `check_field` renamed to `check_edge`.
- `test_student_typed` renamed to `has_code`.
- `test_or`, `test_correct` and `test_not` renamed to `check_or`, `check_correct` and `check_not`.
- `has_equal_ast` messaging improved (more suggestive).
- `check_node` and `check_edge` mesaging improved (more suggestive).
- `has_equal_ast` argument names and defaults changed.
- The way the reporter raises errors has been improved, allowing for interactive experimentation with SCT functions in the future and easier testing.
- Error handling in the reporter has been cleaned up

### Removed

- Most of the AST-related documentation has been moved to `sqlwhat`.


