import Foundation

struct HandshakeMessage: Encodable {
    let kind = "hello"
    let worker_id: String
    let models: [String]
    let capacity: Int
}

struct SpeakerInfo: Decodable {
    let display_name: String?
    let is_local_user: Bool
}

struct StreamOpenMessage: Decodable {
    let kind: String
    let meeting_id: String
    let stream_id: String
    let stream_idx: Int
    let participant_id: String?
    let speaker: SpeakerInfo
    let sample_rate: Int
    let encoding: String
}

struct StreamCloseMessage: Decodable {
    let kind: String
    let stream_id: String
}

struct PingMessage: Codable {
    let kind: String
}

struct PartialTranscriptMessage: Encodable {
    let kind = "partial"
    let stream_id: String
    let text: String
    let timestamp: String?
}

struct FinalTranscriptMessage: Encodable {
    let kind = "final"
    let stream_id: String
    let text: String
    let t_start: Double
    let t_end: Double
    let client_utterance_id: String?
    let timestamp: String?
}

struct IncomingMessageEnvelope: Decodable {
    let kind: String
}
