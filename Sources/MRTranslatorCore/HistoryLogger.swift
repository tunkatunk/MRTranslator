import Foundation

public struct HistoryEvent: Codable {
    public enum EventType: String, Codable {
        case ocr
        case translation
        case error
    }

    public let id: UUID
    public let date: Date
    public let type: EventType
    public let message: String
    public let metadata: [String: String]?

    public init(type: EventType, message: String, metadata: [String: String]? = nil, id: UUID = .init(), date: Date = .init()) {
        self.id = id
        self.date = date
        self.type = type
        self.message = message
        self.metadata = metadata
    }
}

/// Persistent logging layer used to power the upcoming translation history feature.
public final class HistoryLogger {
    public static let shared = HistoryLogger()

    private let ioQueue = DispatchQueue(label: "com.mrtranslator.history-logger", qos: .utility)
    private let encoder: JSONEncoder
    private let fileURL: URL

    private var isEnabled: Bool {
        didSet {
            if isEnabled {
                createLogFileIfNeeded()
            }
        }
    }

    public init(fileURL: URL? = nil, isEnabled: Bool = false) {
        self.encoder = JSONEncoder()
        self.encoder.outputFormatting = [.sortedKeys]
        self.encoder.dateEncodingStrategy = .iso8601
        let directory = fileURL?.deletingLastPathComponent() ?? Self.defaultLogDirectory()
        let resolvedURL = fileURL ?? directory.appendingPathComponent("history.jsonl", isDirectory: false)
        self.fileURL = resolvedURL
        self.isEnabled = isEnabled

        if isEnabled {
            createLogFileIfNeeded()
        }
    }

    public func enableLogging() {
        ioQueue.async { [weak self] in
            self?.isEnabled = true
        }
    }

    public func disableLogging() {
        ioQueue.async { [weak self] in
            self?.isEnabled = false
        }
    }

    public func log(_ event: HistoryEvent) {
        ioQueue.async { [weak self] in
            guard let self, self.isEnabled else { return }
            do {
                createLogFileIfNeeded()
                let line = try encoder.encode(event)
                var payload = Data()
                payload.append(line)
                payload.append(Data("\n".utf8))
                if FileManager.default.fileExists(atPath: fileURL.path) {
                    let handle = try FileHandle(forWritingTo: fileURL)
                    handle.seekToEndOfFile()
                    handle.write(payload)
                    try handle.close()
                } else {
                    try payload.write(to: fileURL)
                }
            } catch {
                // Logging should never crash the app. We swallow the error for now.
            }
        }
    }

    public func fetchRecentEvents(limit: Int = 100) -> [HistoryEvent] {
        return ioQueue.sync {
            guard isEnabled, let data = try? Data(contentsOf: fileURL) else { return [] }
            let lines = data.split(separator: 0x0A)
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            return lines.suffix(limit).compactMap { line -> HistoryEvent? in
                try? decoder.decode(HistoryEvent.self, from: Data(line))
            }
        }
    }

    private func createLogFileIfNeeded() {
        let directory = fileURL.deletingLastPathComponent()
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: nil)
            if !FileManager.default.fileExists(atPath: fileURL.path(percentEncoded: false)) {
                _ = FileManager.default.createFile(atPath: fileURL.path(percentEncoded: false), contents: nil)
            }
        } catch {
            // Ignore for now.
        }
    }

    private static func defaultLogDirectory() -> URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? URL(fileURLWithPath: NSTemporaryDirectory())
        return base.appendingPathComponent("MRTranslator", isDirectory: true)
    }
}
