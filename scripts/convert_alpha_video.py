#!/usr/bin/env python3
"""Convert an Alpha-channel MOV into a packed color-plus-mask MP4."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path


APP_NAME = "transparent-video-alpha"
DEFAULT_WIDTH = 1500
DEFAULT_CRF = 16
ALPHA_PIXEL_FORMATS = ("yuva", "rgba", "argb", "bgra", "abgr")


def log(message: str) -> None:
    print(f"[transparent-video-alpha] {message}", file=sys.stderr)


def fail(message: str) -> "NoReturn":
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def find_binary(name: str) -> str | None:
    return shutil.which(name)


def cache_root() -> Path:
    override = os.environ.get("TRANSPARENT_VIDEO_ALPHA_CACHE")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / APP_NAME / "ffmpeg"


def platform_package() -> tuple[str, str, str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "windows":
        return (
            "windows",
            "ffmpeg-release-essentials.zip",
            "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
            "zip",
        )
    if system == "linux":
        return (
            "linux",
            "ffmpeg-master-latest-linux64-gpl.tar.xz",
            "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-linux64-gpl.tar.xz",
            "tar.xz",
        )
    if system == "darwin":
        if machine not in {"x86_64", "amd64", "arm64", "aarch64"}:
            fail(f"Unsupported macOS architecture: {machine}")
        return (
            "macos",
            "ffmpeg.zip",
            "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip",
            "zip",
        )
    fail(f"Unsupported operating system: {system}")


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    log(f"Downloading FFmpeg from {url}")
    try:
        with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)
    except Exception as exc:
        destination.unlink(missing_ok=True)
        fail(f"FFmpeg download failed: {exc}")


def extract_archive(archive: Path, destination: Path, archive_type: str) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if archive_type == "zip":
        with zipfile.ZipFile(archive) as package:
            package.extractall(destination)
    else:
        with tarfile.open(archive, "r:xz") as package:
            try:
                package.extractall(destination, filter="data")
            except TypeError:
                package.extractall(destination)


def locate_extracted_binary(root: Path, name: str) -> Path | None:
    candidates = list(root.rglob(name)) + list(root.rglob(f"{name}.exe"))
    return next((item for item in candidates if item.is_file()), None)


def ensure_ffmpeg(no_download: bool) -> tuple[str, str]:
    ffmpeg = find_binary("ffmpeg")
    ffprobe = find_binary("ffprobe")
    if ffmpeg and ffprobe:
        return ffmpeg, ffprobe
    if no_download:
        fail("FFmpeg/FFprobe were not found. Install them or remove --no-download.")

    system_name, archive_name, url, archive_type = platform_package()
    destination = cache_root() / system_name
    cached_ffmpeg = locate_extracted_binary(destination, "ffmpeg")
    cached_ffprobe = locate_extracted_binary(destination, "ffprobe")
    if not cached_ffmpeg or not cached_ffprobe:
        archive = destination / archive_name
        if not archive.exists():
            download(url, archive)
        extract_archive(archive, destination / "extracted", archive_type)
        cached_ffmpeg = locate_extracted_binary(destination, "ffmpeg")
        cached_ffprobe = locate_extracted_binary(destination, "ffprobe")
        if system_name == "macos" and not cached_ffprobe:
            probe_archive = destination / "ffprobe.zip"
            if not probe_archive.exists():
                download("https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip", probe_archive)
            extract_archive(probe_archive, destination / "extracted", "zip")
            cached_ffprobe = locate_extracted_binary(destination, "ffprobe")
    if not cached_ffmpeg or not cached_ffprobe:
        fail(f"Downloaded FFmpeg package did not contain both ffmpeg and ffprobe: {destination}")
    for binary in (cached_ffmpeg, cached_ffprobe):
        binary.chmod(binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(cached_ffmpeg), str(cached_ffprobe)


def probe(ffprobe: str, path: Path) -> dict:
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ],
        capture=True,
    )
    if result.returncode != 0:
        fail(f"Could not read video metadata:\n{result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"FFprobe returned invalid JSON: {exc}")


def video_stream(metadata: dict) -> dict:
    streams = [stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "video"]
    if not streams:
        fail("The input does not contain a video stream.")
    return streams[0]


def has_alpha(stream: dict) -> bool:
    pixel_format = str(stream.get("pix_fmt", "")).lower()
    return any(token in pixel_format for token in ALPHA_PIXEL_FORMATS)


def output_path_for(source: Path, requested: str | None) -> Path:
    if requested:
        return Path(requested).expanduser().resolve()
    return source.with_name(f"{source.stem}_packed.mp4")


def convert(
    ffmpeg: str,
    source: Path,
    output: Path,
    width: int,
    crf: int,
    include_audio: bool,
) -> None:
    filter_graph = (
        f"[0:v]split=2[color][alpha];"
        f"[color]scale={width}:-2,format=rgb24[colorout];"
        f"[alpha]alphaextract,scale={width}:-2,format=gray[alphaout];"
        "[colorout][alphaout]vstack=inputs=2,format=yuv420p[v]"
    )
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-filter_complex",
        filter_graph,
        "-map",
        "[v]",
    ]
    if include_audio:
        command.extend(["-map", "0:a?"])
    else:
        command.append("-an")
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
        ]
    )
    if include_audio:
        command.extend(["-c:a", "aac", "-b:a", "128k"])
    command.extend(["-movflags", "+faststart", str(output)])
    log("Converting video")
    result = run(command)
    if result.returncode != 0 or not output.exists() or output.stat().st_size == 0:
        fail("FFmpeg conversion failed or produced an empty output file.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Alpha-channel MOV input")
    parser.add_argument("-o", "--output", help="Output MP4 path; defaults to <input>_packed.mp4")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help=f"Output width, default: {DEFAULT_WIDTH}")
    parser.add_argument("--crf", type=int, default=DEFAULT_CRF, help=f"H.264 CRF, default: {DEFAULT_CRF}")
    parser.add_argument("--no-audio", action="store_true", help="Do not include source audio")
    parser.add_argument("--no-download", action="store_true", help="Do not download FFmpeg if missing")
    args = parser.parse_args()

    source = args.input.expanduser().resolve()
    if not source.is_file():
        fail(f"Input file does not exist: {source}")
    if source.suffix.lower() != ".mov":
        fail("The input must be a .mov file exported with an Alpha channel.")
    if args.width < 2 or args.width % 2:
        fail("--width must be a positive even number.")
    if not 0 <= args.crf <= 51:
        fail("--crf must be between 0 and 51.")

    ffmpeg, ffprobe = ensure_ffmpeg(args.no_download)
    metadata = probe(ffprobe, source)
    stream = video_stream(metadata)
    if not has_alpha(stream):
        pixel_format = stream.get("pix_fmt", "unknown")
        fail(
            "The MOV does not appear to contain an Alpha plane "
            f"(pixel format: {pixel_format}). Re-export from After Effects as ProRes 4444, RGB + Alpha."
        )

    output = output_path_for(source, args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    source_has_audio = any(item.get("codec_type") == "audio" for item in metadata.get("streams", []))
    convert(ffmpeg, source, output, args.width, args.crf, source_has_audio and not args.no_audio)
    result_metadata = probe(ffprobe, output)
    result_stream = video_stream(result_metadata)
    source_width = int(stream.get("width", 0))
    source_height = int(stream.get("height", 0))
    output_width = int(result_stream.get("width", 0))
    output_height = int(result_stream.get("height", 0))
    if output_width != args.width or output_height % 2 != 0:
        fail(f"Unexpected output dimensions: {output_width}×{output_height}")
    audio_present = any(item.get("codec_type") == "audio" for item in result_metadata.get("streams", []))
    print(json.dumps({
        "status": "success",
        "source": str(source),
        "output": str(output),
        "source_dimensions": f"{source_width}x{source_height}",
        "packed_dimensions": f"{output_width}x{output_height}",
        "video_codec": result_stream.get("codec_name"),
        "pixel_format": result_stream.get("pix_fmt"),
        "audio": audio_present,
        "unity_render_texture": {"width": output_width, "height": output_height, "color_format": "ARGB32"},
        "raw_image_aspect_ratio": f"{source_width}:{source_height}",
        "shader": "top-half RGB + bottom-half R channel Alpha",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    main()
