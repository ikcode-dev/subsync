# SubSync

SubSync is a CLI application written in Python that generates Netflix-compliant subtitles for YouTube videos. It uses local AI models to transcribe audio and will support translation to other languages in the future.

The main goal of SubSync is to quickly prepare professional-quality subtitles and their translations for YouTube videos.

## About This Project

SubSync is being developed following the [Subtitle Generation Algorithm](docs/SUBTITLE_GENERATION_ALGORITHM.md), which defines the complete technical specification for generating Netflix-compliant subtitles from YouTube videos. The algorithm covers:

- YouTube URL validation and audio extraction
- AI-powered speech transcription using OpenAI Whisper
- Subtitle processing to meet Netflix Timed Text Style Guide requirements
- Output generation in SRT and VTT formats compatible with YouTube

## Development Workflow

SubSync uses a **Spec-Driven Development** approach that separates **what** to build from **how** to implement it. This ensures stable specifications, clear requirements, and developer freedom to find the best solutions.

### Spec-Driven Development Process

Our development follows this iterative workflow:

```
Context → Plan → Tasks → Implementation → PR & Review
    ↑         ↓      ↓          ↓              ↓
    └─────────────────────────────────────────┘
              (Continuous refinement)
```

#### 1. **Gather Context** (`spec/context/`)

Context files capture domain knowledge, constraints, and research findings:
- Netflix compliance requirements
- YouTube API compatibility
- External documentation references
- Technical decisions and their rationale

**Purpose:** What do we know, and why does it matter?

#### 2. **Develop Plan** (`spec/plan/`)

Plans define implementation strategies organized by features or phases:
- Goals and objectives
- Architecture decisions with rationale
- Component breakdown and responsibilities
- Data flow descriptions
- Risk identification and mitigation

**Purpose:** What are we building, and what's our approach?

**Key principle:** Plans describe **what** and **why**, never **how**. They use pseudo-code, diagrams, and interface definitions to illustrate concepts without locking in implementation details.

#### 3. **Prepare Tasks** (`spec/tasks/`)

Tasks are atomic, verifiable work units:
- Clear objectives and functional requirements
- Input/output specifications
- Acceptance criteria (observable, testable outcomes)
- Test scenarios to verify completion
- Links to relevant context and plans

**Purpose:** What does success look like?

**Key principle:** Tasks are self-contained and describe outcomes, not steps. Each task should be implementable independently with clear verification criteria.

#### 4. **Evolve & Update**

As implementation progresses:
- **Update context** when discovering new domain knowledge
- **Refine plans** based on implementation insights
- **Adjust tasks** to reflect learnings and changed requirements
- Maintain separation: specs define **what**, code defines **how**

#### 5. **Implementation & PR**

For each task:
1. Implement the functionality
2. Write/update tests to verify acceptance criteria
3. Run linters and ensure code quality
4. Verify all acceptance criteria are met
5. Prepare pull request with description linking to task
6. Start code review process

**Definition of Done:**
- ✅ All acceptance criteria met
- ✅ Tests pass (green)
- ✅ Linter checks pass (green)
- ✅ Documentation updated (if needed)
- ✅ Code reviewed and approved

### Directory Structure

```
spec/
├── context/      # Domain knowledge, constraints, research
├── plan/         # Feature/phase implementation strategies
└── tasks/        # Atomic, verifiable work units

src/
└── subsync/      # Application code

tests/            # Test suite

docs/             # Algorithm documentation
└── SUBTITLE_GENERATION_ALGORITHM.md  # Detailed technical spec
```

## Getting Started

### Prerequisites

To run SubSync, you need Python 3.13+ and `uv` installed.

#### Python

Check if you have Python3 installed:

```shell
python3 --version
```

If not, install Python3 or install `uv` directly, which can manage Python versions.

#### UV Package Manager

Check if `uv` is installed:

```shell
uv --version
```

Install `uv` if needed:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your terminal to make `uv` and `uvx` available:

```shell
source ~/.zshrc  # or ~/.bashrc for Bash
```

### Installation

Install project dependencies:

```shell
task install
```

Or using `uv` directly:

```shell
uv sync
```

### Running the Application

Run the CLI:

```shell
task run
```

Or using `uv` directly:

```shell
uv run subsync
```

### Development Commands

Use Taskfile for common operations:

```shell
task install   # Install dependencies
task run       # Run the application
task test      # Run tests
task lint      # Lint code
task format    # Format code
```

**Important:** Always use `uv` for package management, never `pip`:

```shell
uv add <package>              # Add dependency
uv add --group dev <package>  # Add dev dependency
uv run <command>              # Run command
```

## Contributing

We follow Spec-Driven Development:

1. **Understand the context** — Read relevant files in `spec/context/`
2. **Review the plan** — Check `spec/plan/` for the feature you're working on
3. **Pick a task** — Find a task in `spec/tasks/` that's ready for implementation
4. **Implement** — Write code that meets the task's acceptance criteria
5. **Test** — Ensure all tests pass and linting is clean
6. **Submit PR** — Reference the task and plan in your pull request

Questions? Check the [Copilot Instructions](.github/copilot-instructions.md) for detailed coding conventions and architecture patterns.

## License

See [LICENSE](LICENSE) for details.
