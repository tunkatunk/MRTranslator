import Foundation

#if canImport(AppKit)
import AppKit
#endif
#if canImport(UserNotifications)
import UserNotifications
#endif

/// Centralised user notification helper for surfacing recoverable errors.
public final class ErrorNotifier {
    public static let shared = ErrorNotifier()

    private init() {
        #if canImport(UserNotifications)
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
        #endif
    }

    public func present(error: Error, title: String = "Something went wrong", recoverySuggestion: String? = nil) {
        let message: String
        if let localized = error as? LocalizedError, let description = localized.errorDescription {
            message = description
        } else {
            message = error.localizedDescription
        }
        log(error: error, context: recoverySuggestion)

        #if canImport(UserNotifications)
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = [message, recoverySuggestion].compactMap { $0 }.joined(separator: "\n")
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request, withCompletionHandler: nil)
        #elseif canImport(AppKit)
        DispatchQueue.main.async {
            let alert = NSAlert()
            alert.alertStyle = .warning
            alert.messageText = title
            alert.informativeText = [message, recoverySuggestion].compactMap { $0 }.joined(separator: "\n")
            alert.runModal()
        }
        #else
        NSLog("[MRTranslator] %@ - %@", title, message)
        #endif
    }

    private func log(error: Error, context: String?) {
        var metadata: [String: String]? = nil
        if let context, !context.isEmpty {
            metadata = ["context": context]
        }
        HistoryLogger.shared.log(HistoryEvent(type: .error, message: error.localizedDescription, metadata: metadata))
    }
}
