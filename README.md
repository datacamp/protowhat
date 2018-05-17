# protowhat

[![Build Status](https://travis-ci.org/datacamp/protowhat.svg?branch=master)](https://travis-ci.org/datacamp/protowhat)
[![codecov](https://codecov.io/gh/datacamp/protowhat/branch/master/graph/badge.svg)](https://codecov.io/gh/datacamp/protowhat)
[![PyPI version](https://badge.fury.io/py/protowhat.svg)](https://badge.fury.io/py/protowhat)

`protowhat` is a utility package required by `shellwhat` and `sqlwhat` packages, used for writing Submission Correctness Tests SCTs for interactive Shell and SQL exercises on DataCamp. It contains shared functionality related to SCT syntax, selectors and state manipulation.

- If you are new to teaching on DataCamp, check out https://authoring.datacamp.com.
- If you want to learn what SCTs are and how they work, visit https://authoring.datacamp.com/courses/sct.html.
- For a deep dive in `protowhat`, consult https://protowhat.readthedocs.io.

## Installation

```
pip install protowhat   # install from pypi
make install            # install from source
```

## Testing

```
pip install -e .
pytest
```
