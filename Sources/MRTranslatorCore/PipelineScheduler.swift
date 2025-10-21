import Foundation

/// Runs translation pipelines in the background to keep the UI responsive.
public final class PipelineScheduler {
    public typealias Job<T> = @Sendable () async throws -> T
    public typealias Completion<T> = @Sendable (Result<T, Error>) -> Void

    private let executionQueue: DispatchQueue

    public init(label: String = "com.mrtranslator.pipeline", qos: DispatchQoS.QoSClass = .userInitiated) {
        self.executionQueue = DispatchQueue(label: label, qos: DispatchQoS(qosClass: qos, relativePriority: 0), attributes: .concurrent)
    }

    /// Enqueues an asynchronous job that will execute off the main thread.
    /// The completion handler is always called on the main actor.
    public func run<T>(_ job: @escaping Job<T>, completion: Completion<T>? = nil) {
        executionQueue.async {
            Task(priority: .userInitiated) {
                do {
                    let value = try await job()
                    if let completion {
                        await MainActor.run { completion(.success(value)) }
                    }
                } catch {
                    if let completion {
                        await MainActor.run { completion(.failure(error)) }
                    }
                }
            }
        }
    }
}
