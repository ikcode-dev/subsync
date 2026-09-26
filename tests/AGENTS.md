# tests — test suite

Rules for writing and running tests. Project-wide rules are in the [root AGENTS.md](../AGENTS.md).

## Conventions

- pytest. One file per module: `tests/test_<module>.py` covers `src/subsync/<module>.py`. Most files group tests into `Test<Thing>` classes; follow the file you are in.
- Write tests with every piece of logic, especially edge cases. Prefer unit tests for pure functions.
- Tests are deterministic and make no network calls. yt-dlp and Whisper are replaced with `unittest.mock` stand-ins (`@patch("subsync.transcriber.whisper")`); the default run never downloads a model or a video.
- Use pytest's `tmp_path` for files; never write into the repository.
- Run everything with `task test`; one test with `uv run pytest tests/test_file.py::TestClass::test_name`. `task lint` must pass too.

## Test layers from slice S1

Slice S1 adds the layers agreed in E7: integration tests with real FFmpeg on media generated at test time, an SRT invariant checker written from the requirements (not from the processor), and an opt-in end-to-end run (`pytest -m e2e`) with Whisper `tiny` on a clip made with macOS `say`. The e2e tests are skipped by default and wherever `say` or FFmpeg is missing. Details: [phase 4 plan, Testing Strategy (E7)](../spec/plan/phase-4-cli-output.md#testing-strategy-e7). There is no CI until slice S5 ([0010](../decisions/0010-no-ci-until-s5.md)), so these checks run locally.
