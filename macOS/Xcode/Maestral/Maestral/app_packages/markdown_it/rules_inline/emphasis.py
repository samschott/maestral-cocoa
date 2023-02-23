# Process *this* and _that_
#

from .state_inline import Delimiter, StateInline


def tokenize(state: StateInline, silent: bool):
    """Insert each marker as a separate text token, and add it to delimiter list"""
    start = state.pos
    marker = state.srcCharCode[start]

    if silent:
        return False

    # /* _ */  /* * */
    if marker != 0x5F and marker != 0x2A:
        return False

    scanned = state.scanDelims(state.pos, marker == 0x2A)

    for i in range(scanned.length):
        token = state.push("text", "", 0)
        token.content = chr(marker)
        state.delimiters.append(
            Delimiter(
                marker=marker,
                length=scanned.length,
                jump=i,
                token=len(state.tokens) - 1,
                end=-1,
                open=scanned.can_open,
                close=scanned.can_close,
            )
        )

    state.pos += scanned.length

    return True


def _postProcess(state, delimiters):
    i = len(delimiters) - 1
    while i >= 0:
        startDelim = delimiters[i]

        # /* _ */  /* * */
        if startDelim.marker != 0x5F and startDelim.marker != 0x2A:
            i -= 1
            continue

        # Process only opening markers
        if startDelim.end == -1:
            i -= 1
            continue

        endDelim = delimiters[startDelim.end]

        # If the previous delimiter has the same marker and is adjacent to this one,
        # merge those into one strong delimiter.
        #
        # `<em><em>whatever</em></em>` -> `<strong>whatever</strong>`
        #
        isStrong = (
            i > 0
            and delimiters[i - 1].end == startDelim.end + 1
            and delimiters[i - 1].token == startDelim.token - 1
            and delimiters[startDelim.end + 1].token == endDelim.token + 1
            and delimiters[i - 1].marker == startDelim.marker
        )

        ch = chr(startDelim.marker)

        token = state.tokens[startDelim.token]
        token.type = "strong_open" if isStrong else "em_open"
        token.tag = "strong" if isStrong else "em"
        token.nesting = 1
        token.markup = ch + ch if isStrong else ch
        token.content = ""

        token = state.tokens[endDelim.token]
        token.type = "strong_close" if isStrong else "em_close"
        token.tag = "strong" if isStrong else "em"
        token.nesting = -1
        token.markup = ch + ch if isStrong else ch
        token.content = ""

        if isStrong:
            state.tokens[delimiters[i - 1].token].content = ""
            state.tokens[delimiters[startDelim.end + 1].token].content = ""
            i -= 1

        i -= 1


def postProcess(state: StateInline):
    """Walk through delimiter list and replace text tokens with tags."""
    _postProcess(state, state.delimiters)

    for token in state.tokens_meta:
        if token and "delimiters" in token:
            _postProcess(state, token["delimiters"])
