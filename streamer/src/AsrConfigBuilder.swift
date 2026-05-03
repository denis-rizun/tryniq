import Foundation
import FluidAudio

enum AsrConfigBuilder {
    static func fromEnvironment() -> SlidingWindowAsrConfig {
        let env = ProcessInfo.processInfo.environment
        let chunkSeconds = Double(env["ASR_CHUNK_S"] ?? "") ?? 2.0
        let rightContextSeconds = Double(env["ASR_RIGHT_CTX_S"] ?? "") ?? 1.0
        let leftContextSeconds = Double(env["ASR_LEFT_CTX_S"] ?? "") ?? 5.0
        let minConfirmSeconds = Double(env["ASR_MIN_CONFIRM_S"] ?? "") ?? 4.0
        return SlidingWindowAsrConfig(
            chunkSeconds: chunkSeconds,
            hypothesisChunkSeconds: 1.0,
            leftContextSeconds: leftContextSeconds,
            rightContextSeconds: rightContextSeconds,
            minContextForConfirmation: minConfirmSeconds,
            confirmationThreshold: 0.80
        )
    }
}
