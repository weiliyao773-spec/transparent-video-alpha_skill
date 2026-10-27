# Transparent Video Alpha

将带有真实 Alpha 通道的 After Effects `.mov` 视频，转换为适用于 Unity、Android 和 PICO 的上下双层 Alpha `.mp4` 视频。

本项目同时提供 FFmpeg 自动化转换脚本和 Unity 透明视频材质包，适合透明视频在实时交互项目、沉浸式展示和移动端设备中的使用。

## 功能

- 自动查找本机 FFmpeg 和 FFprobe
- 未安装时自动下载并缓存 FFmpeg
- 检查源 MOV 是否包含真实 Alpha 通道
- 将彩色画面和 Alpha 遮罩合成为上下双层视频
- 输出 H.264 编码的 MP4 文件
- 可选择保留或移除源视频音频
- 默认输出宽度为 1500px
- 自动验证输出视频尺寸、编码和音频信息
- 提供 Unity Render Texture、Raw Image 和 Shader 设置说明
- 提供可直接导入 Unity 的透明视频材质包

## 工作原理

输出的 MP4 不是传统意义上的原生透明视频，而是由上下两部分组成：

- 上半部分：彩色画面
- 下半部分：灰度 Alpha 遮罩

Unity 通过透明 Shader 分别采样这两个区域：上半部分的 RGB 连接到颜色，下半部分的 R 通道连接到 Alpha。

因此，直接使用普通播放器打开输出视频时，看到下半部分的灰色或黑白遮罩是正常现象。

## 输入要求

建议使用 After Effects 按以下设置导出源视频：

- 格式：QuickTime `.mov`
- 编码：Apple ProRes 4444
- 通道：RGB + Alpha
- 深度：Millions of Colors+
- Alpha：Straight / Unmatted
- 背景：透明

如果源视频不包含真实 Alpha 通道，脚本会在转换前停止并提示重新导出。

## 使用方式

### 作为 Skill 使用

将本目录作为 Skill 提供给支持 Skill 的 AI 工作流，然后提供一个带 Alpha 的 MOV 文件，例如：

```text
使用 transparent-video-alpha 转换这个视频：
C:\项目素材\透明动画.mov
```

如果视频包含较多文字，可以指定更高的输出宽度：

```text
使用 transparent-video-alpha 转换这个视频，输出宽度使用 1920。
```

### 直接运行脚本

在项目根目录执行：

```bash
python scripts/convert_alpha_video.py "/path/to/input.mov"
```

常用参数：

```bash
# 指定输出宽度
python scripts/convert_alpha_video.py input.mov --width 1920

# 指定输出文件和 CRF
python scripts/convert_alpha_video.py input.mov -o output_packed.mp4 --crf 16

# 不保留音频
python scripts/convert_alpha_video.py input.mov --no-audio

# 不自动下载 FFmpeg
python scripts/convert_alpha_video.py input.mov --no-download
```

默认输出文件会生成在源视频同一目录，命名为：

```text
原文件名_packed.mp4
```

## Unity 配套资源

Unity 透明视频材质包位于：

[下载 transparent-video-materials.unitypackage](./unity/transparent-video-materials.unitypackage)

### 导入 Unity

1. 打开 Unity 项目。
2. 选择 `Assets > Import Package > Custom Package`。
3. 选择下载的 `transparent-video-materials.unitypackage`。
4. 点击 `Import` 导入资源。
5. 将导入的透明视频材质拖到 `Raw Image` 的 `Material` 属性。

该材质用于读取上下双层 Alpha 视频：上半部分提供颜色，下半部分提供透明度。

## Unity 设置

### Render Texture

Render Texture 使用输出视频的完整尺寸。例如，输出视频为 `1500×528` 时：

```text
Width：1500
Height：528
Color Format：ARGB32
Depth Buffer：No Depth Buffer
```

### Video Player

```text
Source：Video Clip
Render Mode：Render Texture
Target Texture：对应的 Render Texture
```

### Raw Image

Raw Image 使用完整尺寸的 Render Texture，但显示比例仍按照原始彩色视频比例设置。

例如：

```text
原始彩色视频：1500×264
双层 MP4：1500×528
Raw Image 显示比例：1500:264
```

### Shader Graph

使用 URP Unlit Shader Graph 时，建议设置：

```text
Surface：Transparent
Blend：Alpha
```

添加两个 `Sample Texture 2D` 节点，并让它们读取同一个视频 Render Texture：

```text
颜色采样：X = UV.x，Y = UV.y × 0.5 + 0.5
Alpha采样：X = UV.x，Y = UV.y × 0.5
```

连接方式：

```text
上半部分采样 RGB → Base Color
下半部分采样 R → Alpha
```

如果出现上下颠倒、透明区域反转或底部异常，可以交换两个 Y 坐标公式。不同视频播放器和平台可能存在纹理上下方向差异。

## 输出尺寸

默认输出宽度为 `1500px`，输出高度是彩色画面高度的两倍：

```text
彩色视频：1500×264
双层 MP4：1500×528
```

如果视频中包含较小文字，可以使用 `--width 1920`，但 H.264 压缩和 Unity 缩放仍可能影响清晰度。重要界面文字建议使用 Unity TextMeshPro 单独渲染。

## 目录结构

```text
transparent-video-alpha_skill/
├── agents/
│   └── openai.yaml
├── scripts/
│   └── convert_alpha_video.py
├── unity/
│   └── transparent-video-materials.unitypackage
├── .gitignore
├── LICENSE
├── README.md
└── SKILL.md
```

文件说明：

- `SKILL.md`：AI 工作流使用的核心 Skill 说明
- `agents/openai.yaml`：Skill 的显示信息和默认提示词配置
- `scripts/convert_alpha_video.py`：FFmpeg 检测、下载、转换和验证脚本
- `unity/transparent-video-materials.unitypackage`：Unity 透明视频材质资源
- `README.md`：项目说明和使用文档

## 常见问题

### 普通播放器中出现灰色底

这是正常现象。输出视频的下半部分是 Alpha 遮罩，普通播放器不会自动将其转换为透明度。请在 Unity 中使用配套透明 Shader 或材质。

### 转换前提示没有 Alpha

说明源 MOV 可能不是带透明通道的 ProRes 4444 文件。请重新从 After Effects 导出，并确认使用 `RGB + Alpha` 和 `Millions of Colors+`。

### Unity 中仍然有灰色背景

请依次检查：

1. Raw Image 是否使用透明材质；
2. 材质的 Surface 是否设置为 Transparent；
3. 上半部分是否连接到 Base Color；
4. 下半部分是否连接到 Alpha；
5. Render Texture 是否使用完整的双层尺寸；
6. 源 MOV 是否确实包含 Alpha 通道。

## 注意事项

- 输出 MP4 不是原生透明视频，必须配合透明 Shader 使用。
- 只有带真实 Alpha 通道的 MOV 才能生成正确遮罩。
- 转换成功必须以输出文件存在且 FFprobe 检查通过为准。
- 如果网络不可用且本机没有 FFmpeg，则无法自动下载转换工具。
- 重要界面文字建议使用 TextMeshPro，而不是直接压进视频。

## License

本项目采用 MIT License，详见 [LICENSE](./LICENSE)。
