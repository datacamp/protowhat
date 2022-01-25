# Controls
.PHONY : commands install clean test
all : commands

## commands : show all commands.
commands :
	@grep -h -E '^##' Makefile | sed -e 's/## //g'

install:
	pip3.10 install -e .
	pip3.10 install -r requirements.txt

## test     : run tests.
test :
	pytest --cov=protowhat
	codecov

## clean    : clean up junk files.
clean :
	@rm -rf bin/__pycache__
	@find . -name .DS_Store -exec rm {} \;
	@find . -name '*~' -exec rm {} \;
	@find . -name '*.pyc' -exec rm {} \;
