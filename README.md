# MRTranslator

Core infrastructure for a macOS menu bar utility that performs on-device OCR and streams the result through OpenAI for fast translations.

## Highlights

- **Debounced OCR** – identical OCR results within a configurable interval are ignored so the translation queue stays lean.
- **Responsive pipelines** – translation work executes on background queues; callbacks always marshal onto the main actor for UI updates.
- **Secure credentials** – the OpenAI API key is persisted in the macOS Keychain and fetched on-demand.
- **Opt-in history** – lightweight JSONL logging captures OCR, translation, and error events when users enable the history feature.
- **User-facing errors** – network or API failures surface via macOS notifications/alerts with actionable suggestions.

## Usage overview

```swift
let keychain = KeychainService()
try keychain.store(apiKey: "sk-...")

let pipeline = TranslatorPipeline<CGImage> { image in
    try await visionClient.extractText(from: image)
}
pipeline.onTranslation = { result in
    print("Translated: \(result.translatedText)")
}
HistoryLogger.shared.enableLogging()

pipeline.process(frame, targetLanguage: "English")
```

The pipeline automatically debounces duplicate OCR frames, logs events when history is enabled, and notifies the user when recoverable errors occur.
