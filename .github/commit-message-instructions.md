# Commit Message Instructions

Generate commit messages following the Conventional Commits specification (https://www.conventionalcommits.org/).

## Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

## Type Prefixes

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (formatting, missing semi-colons, etc.)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `build`: Changes that affect the build system or external dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files
- `revert`: Reverts a previous commit

## Rules

1. Always include a scope in parentheses after the type
2. Use the imperative mood in the subject line ("add" not "added" or "adds")
3. Do not capitalize the first letter of the description
4. Do not end the subject line with a period
5. Limit the subject line to 50 characters when possible, max 72
6. Separate subject from body with a blank line (if body is present)
7. Use the body to explain what and why, not how
8. Wrap the body at 72 characters

## Common Scopes for This Project

- `cli`: CLI interface changes
- `transcribe`: Transcription functionality
- `subtitles`: Subtitle generation and formatting
- `audio`: Audio extraction and processing
- `deps`: Dependency updates
- `config`: Configuration changes

## Breaking Changes

Indicate breaking changes by:
- Adding `!` after the type/scope: `feat(api)!: remove deprecated endpoint`
- Adding `BREAKING CHANGE:` footer in the body

## Examples

### feat - New features
feat(cli): add --output flag for custom output path
feat(transcribe): implement whisper model selection
feat(subtitles): add support for VTT output format

### fix - Bug fixes
fix(cli): resolve crash when URL contains special characters
fix(audio): correct sample rate conversion for mono files
fix(subtitles): prevent overlapping subtitle timestamps

### docs - Documentation
docs(readme): update installation instructions for uv
docs(api): add docstrings to public functions
docs(algorithm): clarify Netflix compliance requirements

### style - Code style (no logic changes)
style(cli): format code with ruff
style(models): fix indentation in data classes
style(transcribe): remove trailing whitespace

### refactor - Code restructuring
refactor(cli): extract argument parsing to separate module
refactor(subtitles): simplify timestamp calculation logic
refactor(audio): rename extraction functions for clarity

### perf - Performance improvements
perf(transcribe): enable batch processing for long videos
perf(subtitles): optimize line breaking algorithm
perf(audio): reduce memory usage during extraction

### test - Tests
test(cli): add unit tests for argument validation
test(subtitles): add edge cases for timestamp formatting
test(e2e): add integration test for full pipeline

### build - Build system
build(deps): upgrade yt-dlp to latest version
build(pyproject): configure ruff linting rules
build(docker): add Dockerfile for containerized execution

### ci - CI/CD changes
ci(github): add pytest workflow for PR validation
ci(release): configure automatic PyPI publishing
ci(lint): add ruff check to CI pipeline

### chore - Maintenance tasks
chore(deps): bump minor dependency versions
chore(gitignore): add .ruff_cache to ignored files
chore(config): update taskfile commands

### revert - Reverting changes
revert(cli): revert "feat(cli): add --output flag"
revert(subtitles): undo breaking change to SRT format

### Breaking changes
feat(cli)!: change default output format to VTT

BREAKING CHANGE: Default subtitle format changed from SRT to VTT. Use --format srt for previous behavior.

refactor(subtitles)!: rename SubtitleEntry to SubtitleCue
