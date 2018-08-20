# Changelog

All notable changes to the protowhat project will be documented in this file.

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


