"""Read-only source scanning utilities for the sentinel."""
from __future__ import annotations

import ast
import io
import re
import tokenize
from collections.abc import Iterator
from pathlib import Path


def iter_files(root: Path, globs: list[str], exclude_dirs: list[str] | None = None,
               exclude_globs: list[str] | None = None) -> Iterator[Path]:
    exclude_dirs = set(exclude_dirs or [])
    exclude_globs = exclude_globs or []
    seen: set[Path] = set()
    for pattern in globs:
        for path in root.glob(pattern):
            if not path.is_file() or path in seen:
                continue
            parts = set(path.relative_to(root).parts)
            if parts & exclude_dirs:
                continue
            if any(path.match(g) for g in exclude_globs):
                continue
            seen.add(path)
            yield path


def _line_starts(src: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(src):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def strip_comments_and_strings(src: str) -> str:
    """Replace comment/string token characters with spaces; keep newlines + offsets."""
    chars = list(src)
    starts = _line_starts(src)

    def offset(row: int, col: int) -> int:
        return starts[row - 1] + col

    string_types = {tokenize.STRING, tokenize.COMMENT}
    for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        t = getattr(tokenize, name, None)
        if t is not None:
            string_types.add(t)
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in string_types:
                start = offset(tok.start[0], tok.start[1])
                end = offset(tok.end[0], tok.end[1])
                for i in range(start, min(end, len(chars))):
                    if chars[i] != "\n":
                        chars[i] = " "
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Unparseable file: fall back to raw text (caller still gets line-accurate hits).
        return src
    return "".join(chars)


def python_string_literals(src: str) -> list[tuple[int, str]] | None:
    """Return (lineno, value) for str literals that are NOT docstrings.

    A docstring is documentation, not emitted output, so it is excluded — this is
    what lets the deviation check tell "we never say buy/sell" (a docstring) apart
    from an actual advice string the agent would emit. Returns ``None`` if the
    source cannot be parsed, so the caller can fall back to a raw-text scan.
    """
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return None
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    results: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            results.append((node.lineno, node.value))
        elif isinstance(node, ast.JoinedStr):  # f-string constant parts
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    results.append((getattr(part, "lineno", node.lineno), part.value))
    return results


def find_matches(text: str, patterns: list[str], word_boundary: bool = False) -> list[tuple[int, str]]:
    if not patterns:
        return []
    body = "|".join(f"(?:{p})" for p in patterns)
    regex = re.compile((r"\b(?:" + body + r")\b") if word_boundary else body)
    results: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in regex.finditer(line):
            results.append((lineno, m.group(0)))
    return results
