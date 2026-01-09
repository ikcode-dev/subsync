Generate commit messages following the Conventional Commits specification (https://www.conventionalcommits.org/).

## Format

<type>[optional scope]: <description>

[optional body]

[optional footer(s)]

## Type Prefixes

Choose the type based on the nature of changes:

- `feat`: A new feature or functionality
- `fix`: A bug fix
- `docs`: Documentation only changes (README.md, docs/, *.md files, docstrings)
- `style`: Changes that do not affect the meaning of the code (formatting, whitespace)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `build`: Changes to build system, dependencies, or pyproject.toml
- `ci`: Changes to CI configuration files and scripts (GitHub Actions, Taskfile.yml)
- `chore`: Other changes that don't modify src or test files
- `revert`: Reverts a previous commit

## File-Based Type Selection

Apply these rules when determining the commit type:

| Files Changed | Type |
|---------------|------|
| `README.md`, `docs/**`, `*.md` (documentation) | `docs` |
| `src/**/*.py` (new functionality) | `feat` |
| `src/**/*.py` (bug fixes) | `fix` |
| `tests/**`, `test_*.py`, `*_test.py` | `test` |
| `pyproject.toml`, `uv.lock` | `build` |
| `.github/workflows/**`, `Taskfile.yml` | `ci` |
| `spec/**`, `ai/**` | `docs` |

## Rules

1. Use the imperative mood in the subject line ("add" not "added" or "adds")
2. Do not capitalize the first letter of the subject line
3. Do not end the subject line with a period
4. Limit the subject line to 50 characters when possible, max 72
5. Separate subject from body with a blank line (if body is present)
6. Use the body to explain what and why, not how
7. Wrap the body at 72 characters

## Breaking Changes

Indicate breaking changes by:
- Adding `!` after the type/scope: `feat!: remove deprecated API`
- Adding `BREAKING CHANGE:` footer in the body

## Examples

```
feat(cli): add transcribe command with language selection
```

```
fix: resolve audio extraction failure for long videos
```

```
docs: update installation instructions in README
```

```
docs(algorithm): add subtitle generation specification
```

```
test: add unit tests for SRT formatter
```

```
build: add yt-dlp dependency
```

```
ci: configure GitHub Actions for automated testing
```

```
refactor(transcriber): extract audio processing to separate module
```
