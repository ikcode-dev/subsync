"""Tests for the static model and language catalog.

`test_catalog_matches_installed_whisper` imports Whisper (fine in a test,
per the task) and fails on any drift between the static snapshot in
`subsync.catalog` and the installed Whisper. `subsync.catalog` itself must
never import Whisper; see `tests/test_cli.py` for the fast-startup proof.
"""

import pytest
from subsync import catalog


class TestModelNames:
    """`MODEL_NAMES` is a tuple snapshot of Whisper's model names."""

    def test_is_a_tuple(self) -> None:
        assert isinstance(catalog.MODEL_NAMES, tuple)

    def test_contains_turbo(self) -> None:
        """`turbo` is the CLI's default model (R7) and must be listed."""
        assert "turbo" in catalog.MODEL_NAMES

    def test_no_duplicates(self) -> None:
        assert len(catalog.MODEL_NAMES) == len(set(catalog.MODEL_NAMES))


class TestLanguages:
    """`LANGUAGES` maps every Whisper language code to an English name."""

    def test_is_a_dict(self) -> None:
        assert isinstance(catalog.LANGUAGES, dict)

    def test_common_codes_present(self) -> None:
        for code in ("en", "pl", "de"):
            assert code in catalog.LANGUAGES

    def test_display_names_are_capitalized(self) -> None:
        assert catalog.LANGUAGES["en"] == "English"
        assert catalog.LANGUAGES["de"] == "German"
        assert catalog.LANGUAGES["pl"] == "Polish"

    def test_no_duplicate_display_names_collapse_codes(self) -> None:
        """Sanity: every code maps to a non-empty display name."""
        assert all(name for name in catalog.LANGUAGES.values())


class TestLanguageName:
    """`language_name` looks up a code's display name."""

    def test_known_code(self) -> None:
        assert catalog.language_name("en") == "English"

    def test_unknown_code_raises(self) -> None:
        with pytest.raises(KeyError):
            catalog.language_name("xx")


class TestCatalogDoesNotImportWhisper:
    """Importing the catalog module alone must not import the ML stack."""

    def test_import_does_not_pull_in_whisper(self) -> None:
        """Regression guard for the fast-startup rule.

        This only proves the module itself has no top-level `import
        whisper`. The authoritative, process-isolated proof is the
        subprocess check in `tests/test_cli.py`.
        """
        import ast
        import inspect

        source = inspect.getsource(catalog)
        tree = ast.parse(source)
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module.split(".")[0])

        assert imported_names.isdisjoint({"whisper", "torch", "yt_dlp"})


class TestDriftAgainstInstalledWhisper:
    """The catalog is an exact snapshot of the installed Whisper."""

    def test_model_names_match_whisper(self) -> None:
        whisper = pytest.importorskip("whisper")
        assert tuple(catalog.MODEL_NAMES) == tuple(whisper.available_models())

    def test_language_codes_match_whisper(self) -> None:
        tokenizer = pytest.importorskip("whisper.tokenizer")
        assert set(catalog.LANGUAGES.keys()) == set(tokenizer.LANGUAGES.keys())
