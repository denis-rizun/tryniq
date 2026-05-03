import Foundation
import FluidAudio

actor SessionManager {
    private let asrModels: AsrModels
    private let publisher: TranscriptPublisher
    private var transcribersByIdx: [UInt32: SpeakerTranscriber] = [:]
    private var streamIdsByIdx: [UInt32: String] = [:]

    init(asrModels: AsrModels, publisher: TranscriptPublisher) {
        self.asrModels = asrModels
        self.publisher = publisher
    }

    func handleControlText(_ text: String) async {
        guard let data = text.data(using: .utf8),
              let envelope = try? JSONDecoder().decode(IncomingMessageEnvelope.self, from: data) else {
            return
        }
        switch envelope.kind {
        case "stream_open":
            guard let open = try? JSONDecoder().decode(StreamOpenMessage.self, from: data) else { return }
            await openStream(open)
        case "stream_close":
            guard let close = try? JSONDecoder().decode(StreamCloseMessage.self, from: data) else { return }
            await closeStream(streamId: close.stream_id)
        default:
            break
        }
    }

    func feedPCM(frame: BinaryAudioFrame) async {
        guard let transcriber = transcribersByIdx[frame.streamIdx] else { return }
        await transcriber.feedPCM(frame.pcm)
    }

    func closeAll() async {
        for (_, transcriber) in transcribersByIdx {
            await transcriber.finish()
        }
        transcribersByIdx.removeAll()
        streamIdsByIdx.removeAll()
    }

    private func openStream(_ open: StreamOpenMessage) async {
        let idx = UInt32(open.stream_idx)
        let streamId = open.stream_id
        let publisher = self.publisher
        do {
            let transcriber = try await SpeakerTranscriber(
                streamId: streamId,
                streamIdx: idx,
                sampleRate: open.sample_rate,
                asrModels: asrModels,
                onPartial: { text in
                    await publisher.publishPartial(streamId: streamId, text: text)
                },
                onFinal: { text, tStart, tEnd in
                    await publisher.publishFinal(
                        streamId: streamId,
                        text: text,
                        tStart: tStart,
                        tEnd: tEnd
                    )
                }
            )
            transcribersByIdx[idx] = transcriber
            streamIdsByIdx[idx] = streamId
        } catch {
            FileHandle.standardError.write(Data("stream \(streamId) open failed: \(error)\n".utf8))
        }
    }

    private func closeStream(streamId: String) async {
        guard let idx = streamIdsByIdx.first(where: { $0.value == streamId })?.key else { return }
        let transcriber = transcribersByIdx.removeValue(forKey: idx)
        streamIdsByIdx.removeValue(forKey: idx)
        if let transcriber { await transcriber.finish() }
    }
}
