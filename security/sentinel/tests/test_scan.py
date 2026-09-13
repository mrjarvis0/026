from security.sentinel.scan import (
    strip_comments_and_strings, find_matches, iter_files, python_string_literals)


def test_find_matches_literal_and_word_boundary():
    text = "x = place_order()\nbuy2 = 1\nbuy = 2\n"
    hits = find_matches(text, [r"buy"], word_boundary=True)
    assert (3, "buy") in hits
    assert (2, "buy") not in hits  # buy2 is not a word-boundary match
    hits2 = find_matches("a = eth_sendTransaction(tx)\n", ["eth_sendTransaction"], word_boundary=True)
    assert hits2 == [(1, "eth_sendTransaction")]


def test_strip_blanks_comments_and_strings_preserving_lines():
    src = 'a = 1  # sign_transaction here\nb = "eth_sendTransaction"\nc = sign_transaction()\n'
    stripped = strip_comments_and_strings(src)
    assert stripped.count("\n") == src.count("\n")
    assert "sign_transaction" in stripped.splitlines()[2]
    assert "sign_transaction" not in stripped.splitlines()[0]
    assert "eth_sendTransaction" not in stripped.splitlines()[1]


def test_python_string_literals_excludes_docstrings():
    src = '"""module doc: should buy"""\nX = "you should sell now"\n# a comment: should buy\n'
    lits = python_string_literals(src)
    vals = [v for _, v in lits]
    assert "you should sell now" in vals
    assert not any("module doc" in v for v in vals)  # docstring excluded


def test_python_string_literals_parse_error_returns_none():
    assert python_string_literals("def oops(:\n") is None


def test_iter_files_respects_exclude_dirs(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x=1")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text("x=1")
    found = {p.name for p in iter_files(tmp_path, ["**/*.py"], exclude_dirs=["tests"])}
    assert found == {"a.py"}
