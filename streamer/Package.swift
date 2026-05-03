// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "streamer",
    platforms: [
        .macOS(.v14),
    ],
    products: [
        .executable(name: "streamer", targets: ["streamer"]),
    ],
    dependencies: [
        .package(url: "https://github.com/FluidInference/FluidAudio", branch: "main"),
    ],
    targets: [
        .executableTarget(
            name: "streamer",
            dependencies: [
                .product(name: "FluidAudio", package: "FluidAudio"),
            ],
            path: "src"
        ),
    ]
)
