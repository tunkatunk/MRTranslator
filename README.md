# MRTranslator

Utilities for building structured prompts and interacting with the OpenAI API
for machine translation workflows.

## Features

- Prompt template with sections for the original text, token analysis, and
  desired translation outputs.
- Rate-limited OpenAI API client with automatic retries and exponential
  backoff.
- Streaming support that yields partial responses for faster UI updates and
  helpers to parse Markdown/JSON output.
- Lightweight line cache that skips re-processing unchanged text segments.

## Installation

```bash
pip install -e .
```

## Usage

```python
from mrt import build_translation_prompt, OpenAITranslatorClient, LineCache

prompt = build_translation_prompt(
    "吾輩は猫である",
    tokens=[
        {"surface": "吾輩", "lemma": "吾輩", "reading": "わがはい", "pos": "noun"},
        {"surface": "猫", "lemma": "猫", "reading": "ねこ", "pos": "noun"},
    ],
)

client = OpenAITranslatorClient(api_key="sk-...", model="gpt-4o-mini")
result = client.complete(prompt)
print(result.text)
```
