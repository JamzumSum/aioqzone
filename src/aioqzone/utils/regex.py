"""
some patterns for matching html and so on.
"""

import re

# use this to match qzone api response
response_callback = re.compile(r"callback\(\s*([\{\[].*[\}\]])\s*\)", re.S | re.I)
# use this to get unikey & curkey of a html
uni_cur_key = re.compile(r'data-unikey="([^"]*)"[^d]*data-curkey="([^"]*)"')

MATCH_PAIR = {"{": "}", "[": "]"}


def entire_closing(string: str, inc="{"):
    dec = MATCH_PAIR[inc]
    cnt = 0
    for i, c in enumerate(string):
        if c == inc:
            cnt += 1
        elif c == dec:
            cnt -= 1
        if cnt == 0:
            return i
    return -1
