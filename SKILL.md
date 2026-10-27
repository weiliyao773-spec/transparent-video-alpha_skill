---
name: transparent-video-alpha
description: Convert a single After Effects Alpha MOV, typically Apple ProRes 4444 with RGB plus Alpha, into a Unity/PICO-ready packed Alpha H.264 MP4. Automatically find or download and cache FFmpeg/FFprobe, validate that the source contains Alpha, preserve optional audio, keep the default 1500px width, double the video height for the color-plus-mask layout, and report the exact Unity Render Texture and Shader settings. Use when a user provides one transparent MOV and asks for a transparent video, packed Alpha MP4, Unity video, PICO video, or FFmpeg conversion.
---

# Transparent Video Alpha

Convert one genuine Alpha-channel MOV into a packed Alpha MP4 that can be decoded reliably in Unity on Android/PICO.

When this Skill is available as a local GitHub directory, prefer running `scripts/convert_alpha_video.py` instead of reconstructing the FFmpeg command manually. The script handles FFmpeg discovery, download, caching, Alpha validation, conversion, metadata verification, and the final Unity handoff report.

## Core rule

The output MP4 is not intrinsically transparent. It contains two vertically stacked images:

- Top half: RGB color image.
- Bottom half: grayscale Alpha mask.

Unity must use a transparent Shader to read the top half as color and the bottom half as Alpha.

Do not present the packed MP4 as a normal transparent video, and do not test it only with a regular video player. A gray or black lower half in a normal player is expected.

## Required input

Accept one local `.mov` file. Prefer an After Effects export with:

- QuickTime MOV.
- Apple ProRes 4444.
- RGB + Alpha / Millions of Colors+.
- Straight or Unmatted Alpha.
- Transparent composition background.

Before conversion, inspect the video with `ffprobe`. The video pixel format should normally include an Alpha plane, such as `yuva444p10le` or `yuva444p`. Do not silently convert a video that has no Alpha channel. Stop and tell the user to re-export the MOV from After Effects.

## FFmpeg acquisition

When the bundled script is available, run:

```bash
python scripts/convert_alpha_video.py "/path/to/input.mov"
```

Use `--width 1920` for text-heavy footage, `--no-audio` for silent output, and `--no-download` to forbid automatic FFmpeg acquisition.

If running without the bundled script:

1. Search the system for `ffmpeg` and `ffprobe` first.
2. If both tools are unavailable, download a current static FFmpeg build appropriate for the host operating system and CPU architecture from a reputable official or project-maintained source.
3. Store the archive and extracted binaries in a user-level cache directory, not beside the input video and not inside the user's project unless requested.
4. Reuse the cached binaries on later runs.
5. Verify both binaries by running `-version` before processing.
6. Never require the user to manually install FFmpeg when the runtime can download it.

If network access is unavailable, explain that automatic acquisition cannot proceed and provide the exact manual installation requirement. Do not claim that conversion succeeded without an output file and a successful probe.

## Output naming and size

Use the source filename stem and append `_packed.mp4` in the same directory by default.

Default output width: `1500` pixels.

Preserve the source aspect ratio. The packed output height must be exactly twice the converted color-video height. For example:

```text
Source color video: 1500×264
Packed MP4:        1500×528
```

If the user requests another width, use that width while preserving aspect ratio. For videos containing small Chinese text, allow a higher width such as `1920`, but warn that Unity UI scaling and video compression can still reduce text sharpness. Recommend TextMeshPro for important UI text.

## Conversion procedure

Use one deterministic FFmpeg filter graph. The graph must:

1. Split the source video into a color branch and an Alpha branch.
2. Scale both branches to the same output width and even height.
3. Convert the color branch to RGB.
4. Extract the Alpha branch with `alphaextract` and convert it to grayscale.
5. Stack the color branch above the grayscale Alpha branch.
6. Encode the result as H.264 with `yuv420p`.
7. Preserve audio when present; encode audio as AAC.

If the bundled script is unavailable, use the following command template. Replace the input and output paths with safely quoted paths and choose the requested width.

```powershell
ffmpeg -i "INPUT.mov" -filter_complex "[0:v]split=2[color][alpha];[color]scale=1500:-2,format=rgb24[colorout];[alpha]alphaextract,scale=1500:-2,format=gray[alphaout];[colorout][alphaout]vstack=inputs=2,format=yuv420p[v]" -map "[v]" -map 0:a? -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart "OUTPUT_packed.mp4"
```

For an input that has no audio, use the same command with `-an` instead of optional audio mapping if the installed FFmpeg build does not accept optional audio mapping.

For text-heavy video, use the same filter graph with `scale=1920:-2` and retain `-crf 16`. Do not upscale a low-resolution source and describe the result as lossless.

## Verification requirements

After conversion, verify all of the following with `ffprobe`:

- Output file exists and is non-empty.
- Video codec is H.264.
- Pixel format is `yuv420p` or another format supported by the target Android/PICO decoder.
- Output width equals the requested width.
- Output height is exactly twice the color-video height.
- Audio is present when the source contained audio, unless the user requested silent output.

Probe template:

```powershell
ffprobe -v error -show_entries stream=index,codec_type,codec_name,pix_fmt,width,height -of json "OUTPUT_packed.mp4"
```

If possible, extract one frame from the packed output and inspect it. The upper half should be the color image; the lower half should be the grayscale mask. Never use the presence of a gray lower half as evidence of conversion failure.

## Unity/PICO handoff

Report these values with every successful conversion:

- Packed video dimensions: output width × output height.
- Color display aspect ratio: source color width × source color height, not the packed dimensions.
- Render Texture: packed video dimensions, `ARGB32`, no depth buffer.
- Video Player: `Video Clip` source, `Render Texture` render mode, target the full-size Render Texture.
- Raw Image: use the full-size Render Texture as its texture and use the transparent material.
- Material: `Surface Type = Transparent`, alpha blending enabled.

Shader UV mapping, assuming the packed texture is oriented normally:

```text
Color RGB UV:
X = UV.x
Y = UV.y × 0.5 + 0.5

Alpha mask UV:
X = UV.x
Y = UV.y × 0.5
```

Connect the upper sample's RGB to Base Color and the lower sample's R channel to Alpha. If the platform flips the texture vertically, test the two Y formulas in the opposite order. Do not change the source file solely because the texture orientation is reversed.

The Raw Image should preserve the original color-video ratio. For a source of `1500×264`, display it at a `1500:264` ratio even though the Render Texture is `1500×528`.

## Failure handling

### Input has no Alpha

Stop before encoding. Report that the MOV is not a real Alpha-channel export and request a new After Effects export using ProRes 4444, RGB + Alpha, and Millions of Colors+.

### Lower half is gray in a player

This is expected. The packed file is an intermediate color-plus-mask layout. Confirm that Unity uses the transparent Shader.

### Gray background remains in Unity

Check, in order:

1. The Raw Image uses the transparent material.
2. The material is Transparent, not Opaque.
3. The upper sample feeds RGB/Base Color.
4. The lower grayscale sample feeds Alpha.
5. The Render Texture contains the complete packed dimensions.
6. The source MOV really contained an Alpha plane.

### Text is blurry

Prefer moving text out of the video and rendering it with TextMeshPro. If text must remain in the video, use a sufficiently large source, avoid unnecessary scaling in Unity, and use the higher-width/CRF-16 variant. Do not promise pixel-perfect text after H.264 compression.

### Black edges or dark halos

Check whether the source was exported with Straight/Unmatted Alpha and whether the Shader is treating the mask as a linear grayscale Alpha value. Compare the extracted mask and color frame separately before changing the FFmpeg graph.

## Final response format

After a successful run, report concisely:

```text
转换完成
源文件：...
输出文件：...
输出尺寸：...
视频编码：H.264
音频：保留/无音频
Unity Render Texture：...
Raw Image显示比例：...
Shader：上半部RGB + 下半部R通道Alpha
```

Only claim success after the output file and its metadata have been verified.
