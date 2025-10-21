import Foundation

/// Debounces identical OCR outputs so that repeated frames do not trigger duplicate translations.
public final class OCROutputDebouncer {
    private var lastPayload: String?
    private var lastEmissionDate: Date?
    private let debounceInterval: TimeInterval
    private let queue = DispatchQueue(label: "com.mrtranslator.ocr-debouncer", qos: .userInteractive)

    public init(interval: TimeInterval = 5) {
        self.debounceInterval = interval
    }

    /// Returns `true` when the payload should be forwarded downstream.
    /// - Parameter payload: The OCR string produced by the Vision pipeline.
    public func shouldEmit(_ payload: String) -> Bool {
        let trimmed = payload.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return false }

        var result = true
        queue.sync {
            if let lastPayload, let lastEmissionDate {
                let delta = Date().timeIntervalSince(lastEmissionDate)
                if lastPayload == trimmed && delta < debounceInterval {
                    result = false
                    return
                }
            }
            lastPayload = trimmed
            lastEmissionDate = Date()
        }
        return result
    }

    /// Clears the previously stored payload so the next emission is always forwarded.
    public func reset() {
        queue.sync {
            lastPayload = nil
            lastEmissionDate = nil
        }
    }
}
