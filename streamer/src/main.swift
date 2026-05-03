import Foundation
import FluidAudio

let workingDir = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let projectRoot = URL(fileURLWithPath: #filePath)
    .deletingLastPathComponent()
    .deletingLastPathComponent()
    .deletingLastPathComponent()

EnvLoader.load(from: workingDir.appendingPathComponent(".env"))
EnvLoader.load(from: projectRoot.appendingPathComponent(".env"))

let env = ProcessInfo.processInfo.environment
let backendUrl = env["BACKEND_WS_URL"] ?? "ws://localhost:8000"
guard let authToken = env["WORKER_TOKEN"], !authToken.isEmpty else {
    FileHandle.standardError.write(Data("WORKER_TOKEN env var is required\n".utf8))
    exit(1)
}

let workerId = env["WORKER_ID"] ?? UUID().uuidString

print("loading parakeet-tdt-v2 via FluidAudio…")

let asrModels: AsrModels
do {
    asrModels = try await AsrModels.downloadAndLoad(version: .v2)
} catch {
    FileHandle.standardError.write(Data("model load failed: \(error)\n".utf8))
    exit(2)
}

print("models loaded; connecting to \(backendUrl)")

let socket = BackendSocket(
    backendBaseUrl: backendUrl,
    authToken: authToken,
    workerId: workerId,
    asrModels: asrModels
)
await socket.runForever()
