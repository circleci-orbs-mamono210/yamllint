#!/bin/bash
yamllint --version \
| GREP_COLORS='mt=01;34' egrep --color=always '[[:digit:]]' \
| GREP_COLORS='mt=01;34' egrep --color=always '\.' \
| GREP_COLORS='mt=01;33' egrep --color=always 'yamllint.* '
