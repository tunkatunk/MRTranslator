# MRTranslator

Utilities for preparing Japanese text for machine translation prompts. The pipeline
normalises punctuation, performs SudachiPy tokenisation (SplitMode.B), and groups
morphemes into sentences while retaining token metadata for later use.

## Quick start

```bash
pip install -r requirements.txt
```

```python
from mrtranslator import TextProcessor

processor = TextProcessor()
processed = processor.process("テスト―です！\n次の行？")

print(processed.normalized_text)
for sentence in processed.sentences:
    print("".join(token.surface for token in sentence.tokens))
```
