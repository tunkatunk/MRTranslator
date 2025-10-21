import Foundation

#if canImport(Security)
import Security
public typealias KeychainStatus = OSStatus
#else
public typealias KeychainStatus = Int32
#endif

public enum KeychainServiceError: LocalizedError {
    case missingConfiguration
    case notFound
    case unexpectedStatus(KeychainStatus)
    case unavailable

    public var errorDescription: String? {
        switch self {
        case .missingConfiguration:
            return "Keychain configuration is missing."
        case .notFound:
            return "No API key is stored in the keychain."
        case .unexpectedStatus(let status):
            return "Keychain operation failed with status: \(status)."
        case .unavailable:
            return "The macOS keychain is unavailable on this platform."
        }
    }
}

public final class KeychainService {
    private let service: String
    private let account: String

    public init(service: String = "com.mrtranslator.openai", account: String = "default") {
        self.service = service
        self.account = account
    }

    public func store(apiKey: String) throws {
        #if canImport(Security)
        let encoded = Data(apiKey.utf8)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]

        var status = SecItemCopyMatching(query as CFDictionary, nil)
        switch status {
        case errSecSuccess:
            let attributesToUpdate: [String: Any] = [
                kSecValueData as String: encoded
            ]
            status = SecItemUpdate(query as CFDictionary, attributesToUpdate as CFDictionary)
        case errSecItemNotFound:
            var mutableQuery = query
            mutableQuery[kSecValueData as String] = encoded
            status = SecItemAdd(mutableQuery as CFDictionary, nil)
        default:
            break
        }

        guard status == errSecSuccess else {
            throw KeychainServiceError.unexpectedStatus(status)
        }
        #else
        throw KeychainServiceError.unavailable
        #endif
    }

    public func loadAPIKey() throws -> String {
        #if canImport(Security)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecMatchLimit as String: kSecMatchLimitOne,
            kSecReturnData as String: true
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        switch status {
        case errSecSuccess:
            guard let data = result as? Data, let key = String(data: data, encoding: .utf8) else {
                throw KeychainServiceError.unexpectedStatus(errSecInternalComponent)
            }
            return key
        case errSecItemNotFound:
            throw KeychainServiceError.notFound
        default:
            throw KeychainServiceError.unexpectedStatus(status)
        }
        #else
        throw KeychainServiceError.unavailable
        #endif
    }

    public func deleteAPIKey() throws {
        #if canImport(Security)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainServiceError.unexpectedStatus(status)
        }
        #else
        throw KeychainServiceError.unavailable
        #endif
    }
}
