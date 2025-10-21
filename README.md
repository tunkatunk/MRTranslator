# MRTranslator

Utilities for running OCR on cropped manga panels using Tesseract with Japanese language support.

## Installation

1. Install [Tesseract OCR](https://tesseract-ocr.github.io/). On Debian/Ubuntu systems:

   ```bash
   sudo apt-get update
   sudo apt-get install tesseract-ocr tesseract-ocr-jpn
   ```

2. Install the Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

```python
from PIL import Image
from mrtranslator.ocr.processor import OCRProcessor, CroppedRegion

processor = OCRProcessor(cache_size=10)
image = Image.open("panel.png")
regions = [CroppedRegion(image=image)]
results = processor.run(regions)

for result in results:
    print(result.text, result.confidence)
```

The processor automatically detects text orientation (vertical vs. horizontal), rotates the image when necessary, and deduplicates repeated OCR outputs by caching the most recent results.
