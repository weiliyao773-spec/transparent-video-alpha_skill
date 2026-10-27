# Transparent Video Alpha

将带有真实 Alpha 通道的 After Effects `.mov` 视频，转换为适用于 Unity、Android 和 PICO 的上下双层 Alpha `.mp4` 视频。

## 功能

- 自动查找本机 FFmpeg 和 FFprobe
- 未安装时自动下载并缓存 FFmpeg
- 检查 MOV 是否包含真实 Alpha 通道
- 将彩色画面与 Alpha 遮罩合成为上下双层视频
- 输出 H.264 编码的 MP4
- 自动保留源视频中的音频
- 默认输出宽度为 1500px
- 输出 Unity Render Texture、Raw Image 和 Shader 参数
- 对无 Alpha 通道的视频进行转换前拦截

## 工作原理

输出 MP4 本身不是传统意义上的透明视频，而是由两部分组成：

```text
上半部分：彩色画面
下半部分：黑白 Alpha 遮罩
```

Unity 通过专用 Shader 读取两部分内容：

```text
上半部分 RGB → 视频颜色
下半部分灰度 → 视频透明度
```

因此，不能直接把输出 MP4 拖到普通 Raw Image 中使用，否则会看到下半部分的灰色或黑白遮罩。

## 输入要求

建议使用 After Effects 按以下设置导出源视频：

- 格式：QuickTime `.mov`
- 编码：Apple ProRes 4444
- 通道：RGB + Alpha
- 深度：Millions of Colors+
- Alpha：Straight / Unmatted
- 背景：透明

源文件示例：

```text
c919时间轴.mov
导入页视频+音频.mov
进气道.mov
```

## 使用方式

将本目录作为 Skill 提供给支持 Skill 的 AI 工作流，然后提供一个 MOV 文件，例如：

```text
使用 transparent-video-alpha 转换这个视频：
C:\项目素材\c919时间轴.mov
```

如果视频中包含较多文字，可以指定更高输出宽度：

```text
使用 transparent-video-alpha 转换这个视频，输出宽度使用 1920：
C:\项目素材\导入页视频+音频.mov
```

默认输出文件会生成在源视频同一目录，命名为：

```text
c919时间轴_packed.mp4
```

也可以在终端中直接运行内置脚本：

```bash
python scripts/convert_alpha_video.py "/path/to/c919时间轴.mov"
```

常用参数：

```bash
# 指定输出宽度
python scripts/convert_alpha_video.py input.mov --width 1920

# 指定输出文件和 CRF
python scripts/convert_alpha_video.py input.mov -o output_packed.mp4 --crf 16

# 不保留音频；如果没有安装 FFmpeg，不自动下载
python scripts/convert_alpha_video.py input.mov --no-audio --no-download
```

脚本会优先使用系统中的 FFmpeg；找不到时，会根据操作系统下载并缓存 FFmpeg/FFprobe。缓存目录可通过环境变量 `TRANSPARENT_VIDEO_ALPHA_CACHE` 自定义。

## 输出尺寸

输出视频的高度是彩色画面高度的两倍：

```text
彩色视频：1500×264
双层 MP4：1500×528
```

Render Texture 使用双层 MP4 的完整尺寸，但 Raw Image 的显示比例仍按照原始彩色视频比例设置。

## Unity 接入要点

### Render Texture

以输出视频 `1500×528` 为例：

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

如果源视频包含音频，需要配置 Audio Source 或 Direct 音频输出。

### Shader

Shader 需要将两个区域分别采样：

```text
颜色画面：
X = UV.x
Y = UV.y × 0.5 + 0.5

Alpha 遮罩：
X = UV.x
Y = UV.y × 0.5
```

连接关系：

```text
上半部分 RGB → Base Color
下半部分 R 通道 → Alpha
Surface Type → Transparent
```

如果画面上下颠倒，可以在 Shader 中交换两个 Y 坐标公式。

## 常见问题

### 播放器中出现灰色底

这是正常现象。普通播放器只会显示双层视频，不会自动将下半部分转换为透明度。请在 Unity 中使用专用透明 Shader。

### 转换前提示没有 Alpha

说明 MOV 可能不是带透明通道的 ProRes 4444 文件。请重新从 After Effects 导出，并确认使用 `RGB + Alpha` 和 `Millions of Colors+`。

### Unity 中仍然有灰色背景

依次检查：

1. Raw Image 是否使用透明材质；
2. 材质是否设置为 Transparent；
3. 上半部分是否连接 Base Color；
4. 下半部分是否连接 Alpha；
5. Render Texture 是否使用完整的双层尺寸；
6. 源 MOV 是否确实包含 Alpha 通道。

### 视频文字模糊

视频中的文字会受到缩放和 H.264 压缩影响。优先建议：

- 将文字从视频中拆出；
- 使用 Unity TextMeshPro 重新制作文字；
- 视频只保留背景和动效。

如果必须保留视频文字，可以使用更高分辨率源视频，并指定输出宽度为 1920px，但不能保证文字完全无损。

## 目录结构

```text
transparent-video-alpha/
├── SKILL.md
├── README.md
├── LICENSE
├── .gitignore
├── agents/
│   └── openai.yaml
└── scripts/
    └── convert_alpha_video.py
```

`SKILL.md` 是 AI 工作流使用的核心文件，`README.md` 用于 GitHub 项目说明。
`scripts/convert_alpha_video.py` 是实际执行 FFmpeg 检测、下载、转换和验证的脚本。

## 配套 Unity 材质包

仓库提供了一个与本 Skill 配套的 Unity 材质包：

[下载 transparent-video-materials.unitypackage](./unity/transparent-video-materials.unitypackage)

该资源包用于在 Unity 中还原双层 Alpha MP4 的透明效果。包内资源以实际导入内容为准，建议先备份当前 Unity 项目，再导入材质包。

### 导入 Unity 材质包

1. 在 GitHub 中打开 `unity/transparent-video-materials.unitypackage`，点击 **Download raw** 下载文件。
2. 打开 Unity 项目，在顶部菜单选择 **Assets → Import Package → Custom Package...**。
3. 选择下载的 `.unitypackage` 文件，勾选需要导入的资源并点击 **Import**。
4. 将导入后的透明视频材质拖到显示视频的 Raw Image 的 **Material** 属性中。
5. Raw Image 的 Texture 仍然使用 Video Player 输出的完整 Render Texture。

### Shader Graph 配置逻辑

如果需要手动检查或重新制作 Shader Graph，可按照以下流程操作：

1. 在 Project 窗口右键，选择 **Create → Shader Graph → URP → Unlit Shader Graph**。
2. 将 **Surface** 设置为 `Transparent`，将 **Blend** 设置为 `Alpha`。
3. 添加两个 **Sample Texture 2D** 节点，并让它们读取同一个视频 Render Texture。
4. 第一个采样节点读取上半部分彩色画面，将 RGB 连接到 **Base Color**。
5. 第二个采样节点读取下半部 Alpha 遮罩，将 R 通道连接到 **Alpha**。
6. 保存 Shader Graph，创建材质，并将材质拖到 Raw Image 的 **Material** 属性。

默认 UV 关系为：

```text
颜色画面：X = UV.x，Y = UV.y × 0.5 + 0.5
Alpha 遮罩：X = UV.x，Y = UV.y × 0.5
```

如果出现画面上下颠倒、透明区域反转或底部异常，需要对调两个 Y 坐标公式。不同视频播放器、Unity 版本和目标平台可能存在纹理上下方向差异。

### 使用提醒

- Render Texture 使用双层 MP4 的完整尺寸，例如 `1500×528`。
- Raw Image 显示比例按照原始彩色视频尺寸设置，例如 `1500:264`。
- 普通播放器中看到灰色或黑白下半部分属于正常现象。
- 透明材质必须设置为 Transparent，不能使用 Opaque 材质。

## 注意事项

- 输出 MP4 不是原生透明视频，必须配合 Unity Shader 使用。
- 只有带真实 Alpha 通道的 MOV 才能生成正确遮罩。
- 输出成功必须以文件存在和 FFprobe 检查通过为准。
- 如果网络不可用且本机没有 FFmpeg，则无法自动下载转换工具。
- 重要界面文字建议使用 TextMeshPro，而不是直接压进视频。
