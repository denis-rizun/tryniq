import Foundation
import FluidAudio

enum TranscriptTiming {
    static func range(
        update: SlidingWindowTranscriptionUpdate,
        sampleRate: Double,
        samplesProcessed: Int
    ) -> (Double, Double) {
        if let first = update.tokenTimings.first, let last = update.tokenTimings.last {
            return (Double(first.startTime), Double(last.endTime))
        }
        let endSeconds = Double(samplesProcessed) / sampleRate
        return (endSeconds, endSeconds)
    }
}
