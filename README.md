# 🧬 polymerase

hi there! i'm polymerase, a little tool for running lots of prompts against an AI model. i can take a dataset of prompts, and i'll run them all for you, as quickly as i can!

i was named after the enzyme that synthesizes DNA, because i help synthesize new text from your prompts. isn't that neat?

## what is it?

polymerase is a small, asynchronous tool for running a dataset of prompts against a text generation API. it's built with python, `trio` for concurrency, and `httpx` for making web requests.

it's designed to be simple to use and configure. you just give it a `config.toml` file, and it does the rest!

## how to run

1.  install the dependencies:
    ```bash
    uv sync
    ```
2.  create a `config.toml` file. you can use the example below as a starting point.
3.  run it!
    ```bash
    uv run src/main.py
    ```

## example config

here's an example `config.toml` to get you started. make sure to replace the `api_key` with your own!

```toml
[api]
base_url = "https://api.openai.com/v1"
model = "gpt-4o-mini"
api_key = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

[model]
system_prompt = """You are a helpful assistant..."""
temperature = 0.7
top_p = 0.95

[data]
path = "allura-forge/prompt_column_test"
type = "hf"
format = "prompt_column"

[processes]
parallel = 2

[output]
path = "output.jsonl"
type = "jsonl"
format = "messages_column"
checkpoint_interval = 10
```

## license

polymerase is licensed under a modified version of the [GNU General Public License v3.0](COPYING).

### output exception

[you are allowed to use the generated output of polymerase for any purpose under any license. regular copyleft rules apply to the source code.](COPYING.exception)

however, we would appreciate it if you credited polymerase in any datasets using it that are released <3
