// Native macOS decode of the actual offline loading movie. No browser access.
import Foundation
import AVFoundation
import CoreGraphics
import ImageIO
import CoreServices

let args = CommandLine.arguments
guard args.count == 3 else { fatalError("usage: swift check_hangzhou_loading.swift MOVIE NEW_OUTPUT") }
let input = URL(fileURLWithPath: args[1]), output = URL(fileURLWithPath: args[2], isDirectory: true)
guard !FileManager.default.fileExists(atPath: output.path) else { fatalError("Fresh review directory required") }
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
let asset = AVURLAsset(url: input)
let tracks = asset.tracks(withMediaType: .video)
guard tracks.count == 1 else { fatalError("One video track required") }
let track = tracks[0]
let duration = CMTimeGetSeconds(asset.duration)
let fps = Double(track.nominalFrameRate)
let size = track.naturalSize
let audioCount = asset.tracks(withMediaType: .audio).count
let formats = track.formatDescriptions as! [CMFormatDescription]
let codecs = formats.map { format -> String in
    let code = CMFormatDescriptionGetMediaSubType(format)
    return String(bytes: [UInt8((code >> 24) & 255), UInt8((code >> 16) & 255), UInt8((code >> 8) & 255), UInt8(code & 255)], encoding: .ascii) ?? "unknown"
}
let reader = try AVAssetReader(asset: asset)
let samples = AVAssetReaderTrackOutput(track: track, outputSettings: nil)
reader.add(samples); guard reader.startReading() else { throw reader.error! }
var frameCount = 0
while let sample = samples.copyNextSampleBuffer() { frameCount += CMSampleBufferGetNumSamples(sample) }
guard reader.status == .completed else { throw reader.error! }
let generator = AVAssetImageGenerator(asset: asset)
generator.appliesPreferredTrackTransform = true
generator.requestedTimeToleranceBefore = .zero; generator.requestedTimeToleranceAfter = .zero
var pixels: [[UInt8]] = [], previews: [[String: Any]] = []
for frame in [0, 1, 180, 360, 540, 718, 719] {
    let request = CMTime(value: Int64(frame), timescale: 30)
    var actual = CMTime.zero
    let image = try generator.copyCGImage(at: request, actualTime: &actual)
    let destination = output.appendingPathComponent(String(format: "frame-%03d.jpg", frame))
    guard let encoder = CGImageDestinationCreateWithURL(destination as CFURL, kUTTypeJPEG, 1, nil) else { fatalError("JPEG encoder unavailable") }
    CGImageDestinationAddImage(encoder, image, [kCGImageDestinationLossyCompressionQuality: 0.94] as CFDictionary)
    guard CGImageDestinationFinalize(encoder) else { fatalError("Failed to write preview") }
    var rgba = [UInt8](repeating: 0, count: 320*180*4)
    rgba.withUnsafeMutableBytes { bytes in
        let context = CGContext(data: bytes.baseAddress, width: 320, height: 180, bitsPerComponent: 8, bytesPerRow: 320*4, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        context.interpolationQuality = .high
        context.draw(image, in: CGRect(x: 0, y: 0, width: 320, height: 180))
    }
    pixels.append(rgba)
    previews.append(["frame": frame, "requestedSeconds": CMTimeGetSeconds(request), "actualSeconds": CMTimeGetSeconds(actual), "file": destination.lastPathComponent])
}
func meanDifference(_ a: [UInt8], _ b: [UInt8]) -> Double {
    var sum = 0
    for i in a.indices where i % 4 != 3 { sum += abs(Int(a[i])-Int(b[i])) }
    return Double(sum) / Double(a.count / 4 * 3)
}
let adjacentStart = meanDifference(pixels[0], pixels[1])
let adjacentEnd = meanDifference(pixels[5], pixels[6])
let seam = meanDifference(pixels[6], pixels[0])
let checks: [String: Bool] = ["h264": codecs == ["avc1"], "fullHD": size.width == 1920 && size.height == 1080,
    "fps30": abs(fps-30) < 0.0001, "seconds24": abs(duration-24) < 0.0001,
    "frames720": frameCount == 720, "silent": audioCount == 0,
    "allRequestedFramesDecoded": previews.count == 7,
    "loopJumpComparableToAdjacentFrames": seam <= max(adjacentStart, adjacentEnd)*2 + 0.1]
let result: [String: Any] = ["kind": "actual offline movie decode; no browser or in-game acceptance", "input": input.path,
    "durationSeconds": duration, "fps": fps, "videoFrames": frameCount, "width": size.width, "height": size.height,
    "audioTracks": audioCount, "codecs": codecs, "checks": checks, "pass": checks.values.allSatisfy { $0 },
    "previews": previews, "pixelMeanAbsoluteDifferenceAt320x180": ["firstAdjacent": adjacentStart, "lastAdjacent": adjacentEnd, "loopSeam": seam],
    "pending": ["human visual review of decoded views", "real browser autoplay/poster/failure/reduced-motion checks"]]
let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
try data.write(to: output.appendingPathComponent("report.json")); print(String(data: data, encoding: .utf8)!)
if !checks.values.allSatisfy({ $0 }) { exit(1) }
