import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

public enum OpenAIServiceError: LocalizedError {
    case missingAPIKey
    case invalidResponse
    case transport(Error)
    case httpStatus(Int, String?)

    public var errorDescription: String? {
        switch self {
        case .missingAPIKey:
            return "An OpenAI API key is required before performing translations."
        case .invalidResponse:
            return "The translation service returned an invalid response."
        case .transport(let error):
            return error.localizedDescription
        case .httpStatus(let status, let message):
            if let message, !message.isEmpty {
                return message
            }
            return "The translation service failed with HTTP status \(status)."
        }
    }
}

public struct TranslationResult: Codable {
    public let originalText: String
    public let translatedText: String
    public let sourceLanguage: String
    public let targetLanguage: String
}

public final class OpenAIService {
    private let session: URLSession
    private let keychain: KeychainService

    public init(session: URLSession = .shared, keychain: KeychainService = KeychainService()) {
        self.session = session
        self.keychain = keychain
    }

    public func translate(text: String, targetLanguage: String, sourceLanguage: String? = nil) async throws -> TranslationResult {
        guard let apiKey = try? keychain.loadAPIKey(), !apiKey.isEmpty else {
            throw OpenAIServiceError.missingAPIKey
        }

        let endpoint = URL(string: "https://api.openai.com/v1/responses")!
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.addValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")

        let payload = requestBody(text: text, targetLanguage: targetLanguage, sourceLanguage: sourceLanguage)
        request.httpBody = try JSONSerialization.data(withJSONObject: payload, options: [])

        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                throw OpenAIServiceError.invalidResponse
            }
            guard 200..<300 ~= http.statusCode else {
                let message = try? decodeErrorMessage(from: data)
                throw OpenAIServiceError.httpStatus(http.statusCode, message)
            }

            let translatedText = try decodeTranslatedText(from: data)
            return TranslationResult(
                originalText: text,
                translatedText: translatedText,
                sourceLanguage: sourceLanguage ?? "auto",
                targetLanguage: targetLanguage
            )
        } catch {
            if let error = error as? OpenAIServiceError {
                throw error
            }
            throw OpenAIServiceError.transport(error)
        }
    }

    private func requestBody(text: String, targetLanguage: String, sourceLanguage: String?) -> [String: Any] {
        var instructions = "You are a translation engine. Translate the user text into \(targetLanguage)."
        if let sourceLanguage {
            instructions += " The source language is \(sourceLanguage)."
        }
        return [
            "model": "gpt-4o-mini",
            "input": [
                [
                    "role": "system",
                    "content": instructions
                ],
                [
                    "role": "user",
                    "content": text
                ]
            ]
        ]
    }

    private func decodeTranslatedText(from data: Data) throws -> String {
        struct Response: Decodable {
            struct Content: Decodable {
                let type: String
                let text: String?
            }

            struct Output: Decodable {
                let content: [Content]
            }

            let output: [Output]
        }

        let decoder = JSONDecoder()
        guard let response = try? decoder.decode(Response.self, from: data) else {
            throw OpenAIServiceError.invalidResponse
        }

        for output in response.output {
            for content in output.content where content.type == "output_text" {
                if let text = content.text?.trimmingCharacters(in: .whitespacesAndNewlines), !text.isEmpty {
                    return text
                }
            }
        }
        throw OpenAIServiceError.invalidResponse
    }

    private func decodeErrorMessage(from data: Data) throws -> String? {
        struct ErrorEnvelope: Decodable {
            struct Inner: Decodable {
                let message: String?
            }

            let error: Inner?
        }

        let decoder = JSONDecoder()
        let envelope = try? decoder.decode(ErrorEnvelope.self, from: data)
        return envelope?.error?.message
    }
}
