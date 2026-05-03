import Foundation

enum EnvLoader {
    static func load(from url: URL) {
        guard let text = try? String(contentsOf: url, encoding: .utf8) else { return }
        for rawLine in text.split(whereSeparator: \.isNewline) {
            let line = rawLine.trimmingCharacters(in: .whitespaces)
            if line.isEmpty || line.hasPrefix("#") { continue }
            guard let equalsIndex = line.firstIndex(of: "=") else { continue }
            let key = String(line[..<equalsIndex]).trimmingCharacters(in: .whitespaces)
            var value = String(line[line.index(after: equalsIndex)...]).trimmingCharacters(in: .whitespaces)
            if (value.hasPrefix("\"") && value.hasSuffix("\""))
                || (value.hasPrefix("'") && value.hasSuffix("'")) {
                value = String(value.dropFirst().dropLast())
            }
            if ProcessInfo.processInfo.environment[key] != nil { continue }
            setenv(key, value, 0)
        }
    }
}
