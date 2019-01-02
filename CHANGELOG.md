# Changelog

All notable changes to the protowhat project will be documented in this file.

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


