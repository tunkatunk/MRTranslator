import Foundation

public final class TranslatorPipeline<Input> {
    private let scheduler: PipelineScheduler
    private let debouncer: OCROutputDebouncer
    private let ocrHandler: @Sendable (Input) async throws -> String
    private let translationService: OpenAIService
    private let errorNotifier: ErrorNotifier
    private let historyLogger: HistoryLogger

    public var onTranslation: ((TranslationResult) -> Void)?
    public var onOCROutput: ((String) -> Void)?

    public init(
        ocrHandler: @escaping @Sendable (Input) async throws -> String,
        translationService: OpenAIService = OpenAIService(),
        scheduler: PipelineScheduler = PipelineScheduler(),
        debouncer: OCROutputDebouncer = OCROutputDebouncer(),
        errorNotifier: ErrorNotifier = .shared,
        historyLogger: HistoryLogger = .shared
    ) {
        self.ocrHandler = ocrHandler
        self.translationService = translationService
        self.scheduler = scheduler
        self.debouncer = debouncer
        self.errorNotifier = errorNotifier
        self.historyLogger = historyLogger
    }

    public func process(_ input: Input, targetLanguage: String, sourceLanguage: String? = nil) {
        scheduler.run({ [weak self] () async throws -> TranslationResult in
            guard let self else { throw PipelineError.pipelineDeallocated }
            let rawText = try await ocrHandler(input)

            guard self.debouncer.shouldEmit(rawText) else {
                throw PipelineError.duplicateFrame
            }

            await MainActor.run {
                self.onOCROutput?(rawText)
            }

            self.historyLogger.log(HistoryEvent(type: .ocr, message: rawText))

            let translation = try await self.translationService.translate(
                text: rawText,
                targetLanguage: targetLanguage,
                sourceLanguage: sourceLanguage
            )
            return translation
        }, completion: { [weak self] result in
            guard let self else { return }
            switch result {
            case .success(let translation):
                self.historyLogger.log(
                    HistoryEvent(
                        type: .translation,
                        message: translation.translatedText,
                        metadata: [
                            "sourceLanguage": translation.sourceLanguage,
                            "targetLanguage": translation.targetLanguage
                        ]
                    )
                )
                self.onTranslation?(translation)
            case .failure(let error):
                if let pipelineError = error as? PipelineError, pipelineError == .duplicateFrame {
                    return
                }
                self.errorNotifier.present(error: error, recoverySuggestion: Self.recoverySuggestion(for: error))
            }
        })
    }

    private static func recoverySuggestion(for error: Error) -> String? {
        if let openAIError = error as? OpenAIServiceError {
            switch openAIError {
            case .missingAPIKey:
                return "Add your OpenAI API key in Preferences to continue."
            case .httpStatus(_, _), .transport(_):
                return "Check your internet connection and API key, then try again."
            case .invalidResponse:
                return "Try again in a moment. If the issue persists, file a bug report."
            }
        }
        return nil
    }
}

public enum PipelineError: Error, Equatable {
    case pipelineDeallocated
    case duplicateFrame
}
