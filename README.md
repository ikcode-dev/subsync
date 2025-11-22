# SubMVP

This is MVP version of the app that I'm going to use to generate subtitles for YouTube (or any other) videos.

## Run the project

### Prerequisites

To run the project it's required to have Python3 and `uv` installed.

#### Python

Check if you have Python3 installed:

```shell
python3 --version
```

In case you don't have it, install Python3 or install directly `uv` which will allow you to manage Python versions.

#### UV

Check if `uv` is installed on your OS:

```shell
uv --version
```

If it's not, install it using:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart terminal to have `uv` and `uvx` available. In my case it's ZSH:

```shell
source ~/.zshrc
```

### Run the app

To run it use:

```shell
uv run sub-mvp
```

At this stage it will output this simple message:

```text
Hello World
```
