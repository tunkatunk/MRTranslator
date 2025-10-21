// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MRTranslator",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .library(name: "MRTranslatorCore", targets: ["MRTranslatorCore"])
    ],
    targets: [
        .target(
            name: "MRTranslatorCore",
            path: "Sources/MRTranslatorCore"
        )
    ]
)
