# Controls
.PHONY : commands clean test
all : commands

## commands : show all commands.
commands :
	@grep -h -E '^##' Makefile | sed -e 's/## //g'

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
