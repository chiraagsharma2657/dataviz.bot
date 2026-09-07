"""Repairing the SQL the model writes so it runs on SQLite.

The model is asked for MySQL, but the query actually executes against an
in-memory SQLite database, and dates are stored as YYYY-MM-DD text. Two
mismatches follow from that, and both are fixed here rather than in the prompt,
because a prompt rule is a request and this needs to be a guarantee:

1. MySQL's YEAR()/MONTH()/DAY()/DATE_FORMAT() do not exist in SQLite. These at
   least fail loudly ("no such function: YEAR").

2. strftime() returns TEXT, and SQLite does not compare TEXT to INTEGER by
   value, so `strftime('%Y', d) = 2025` matches nothing at all - no error, just
   an empty result. This is the one that silently returns zero rows.
"""

import re

# MySQL date part -> the strftime format string that does the same job.
_DATE_PARTS = {
    "YEAR": "%Y",
    "MONTH": "%m",
    "DAY": "%d",
    "DAYOFMONTH": "%d",
    "HOUR": "%H",
    "MINUTE": "%M",
    "SECOND": "%S",
}

# MySQL DATE_FORMAT specifiers -> strftime equivalents.
_FORMAT_MAP = {
    "%Y": "%Y", "%y": "%Y", "%m": "%m", "%c": "%m", "%d": "%d", "%e": "%d",
    "%H": "%H", "%k": "%H", "%i": "%M", "%s": "%S", "%S": "%S", "%j": "%j",
}

_COMPARISON = re.compile(r"\s*(=|==|!=|<>|>=|<=|>|<)\s*(-?\d+)\b")


def _split_args(text):
    """Split a call's argument list on top-level commas."""
    args, depth, current, quote = [], 0, [], None
    for ch in text:
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "'\"`":
            quote = ch
            current.append(ch)
        elif ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        args.append("".join(current).strip())
    return args


def _find_call(sql, name):
    """Locate `name(...)` outside string literals.

    Returns (start, end, args) where end is just past the closing paren, or
    None. Matching parens are counted so nested calls survive intact.
    """
    pattern = re.compile(rf"\b{name}\s*\(", re.IGNORECASE)
    for match in pattern.finditer(sql):
        # Skip a match that sits inside a quoted string or a quoted identifier.
        prefix = sql[:match.start()]
        if prefix.count("'") % 2 or prefix.count('"') % 2 or prefix.count("`") % 2:
            continue

        depth, quote = 0, None
        for i in range(match.end() - 1, len(sql)):
            ch = sql[i]
            if quote:
                if ch == quote:
                    quote = None
                continue
            if ch in "'\"`":
                quote = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    inner = sql[match.end():i]
                    return match.start(), i + 1, _split_args(inner)
    return None


def _translate_format(mysql_format):
    """Convert a DATE_FORMAT() format string to the strftime equivalent."""
    body = mysql_format.strip()
    quote = body[0] if body[:1] in ("'", '"') else None
    if quote:
        body = body[1:-1]
    out = re.sub(r"%.", lambda m: _FORMAT_MAP.get(m.group(0), m.group(0)), body)
    return f"'{out}'"


def _rewrite_date_parts(sql):
    """YEAR(d) -> CAST(strftime('%Y', d) AS INTEGER), and friends.

    The CAST is what keeps the result comparable to a bare number, which is how
    the model naturally writes a filter.
    """
    for name, fmt in _DATE_PARTS.items():
        while True:
            found = _find_call(sql, name)
            if not found:
                break
            start, end, args = found
            if len(args) != 1:
                break
            replacement = f"CAST(strftime('{fmt}', {args[0]}) AS INTEGER)"
            sql = sql[:start] + replacement + sql[end:]
    return sql


def _rewrite_date_format(sql):
    """DATE_FORMAT(d, '%Y-%m') -> strftime('%Y-%m', d)."""
    while True:
        found = _find_call(sql, "DATE_FORMAT")
        if not found:
            break
        start, end, args = found
        if len(args) != 2:
            break
        replacement = f"strftime({_translate_format(args[1])}, {args[0]})"
        sql = sql[:start] + replacement + sql[end:]
    return sql


def _cast_numeric_comparisons(sql):
    """Wrap strftime() in CAST when it is compared against a bare number.

    This is the fix for the silent empty result: strftime() yields TEXT, so
    `strftime('%Y', d) = 2025` is false for every row until the value is cast
    to an integer.
    """
    search_from = 0
    while True:
        found = _find_call(sql[search_from:], "strftime")
        if not found:
            return sql
        start, end, args = found
        start, end = start + search_from, end + search_from

        comparison = _COMPARISON.match(sql, end)
        if not comparison:
            search_from = end
            continue

        call = sql[start:end]
        sql = f"{sql[:start]}CAST({call} AS INTEGER){sql[end:]}"
        search_from = start + len(call) + len("CAST( AS INTEGER)")


def repair_sql(sql):
    """Make the model's MySQL run correctly on SQLite date text."""
    if not sql:
        return sql
    sql = _rewrite_date_format(sql)
    sql = _rewrite_date_parts(sql)
    sql = _cast_numeric_comparisons(sql)
    return sql
