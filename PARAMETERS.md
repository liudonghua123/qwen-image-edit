# QwenImageEditPipeline 参数分析

## 概述

本文档列出了 `QwenImageEditPipeline` 支持的所有参数，以及 `/v1/images/edits` API 端点如何支持这些参数。

---

## QwenImageEditPipeline 支持的参数

### 必需参数

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `image` | PIL.Image / numpy.ndarray / torch.Tensor / List | 输入图像 |
| `prompt` | str / List[str] | 编辑提示文本 |

### 可选参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `negative_prompt` | str / List[str] | None | 负面提示文本（描述不想要的内容） |
| `true_cfg_scale` | float | 4.0 | 分类器自由引导的尺度 |
| `height` | int | None | 输出图像的高度（像素） |
| `width` | int | None | 输出图像的宽度（像素） |
| `num_inference_steps` | int | 50 | 推理步数（越高越精准但更慢） |
| `sigmas` | List[float] | None | 自定义 sigma 值 |
| `guidance_scale` | float | None | 引导尺度（控制遵循提示的程度） |
| `num_images_per_prompt` | int | 1 | 每个提示生成的图像数 |
| `generator` | torch.Generator / List | None | 随机数生成器 |
| `latents` | torch.Tensor | None | 预定义的潜在向量 |
| `prompt_embeds` | torch.Tensor | None | 预计算的提示嵌入 |
| `prompt_embeds_mask` | torch.Tensor | None | 提示嵌入的掩码 |
| `negative_prompt_embeds` | torch.Tensor | None | 预计算的负面提示嵌入 |
| `negative_prompt_embeds_mask` | torch.Tensor | None | 负面提示嵌入的掩码 |
| `output_type` | str | "pil" | 输出类型："pil" 或 "pt"（torch张量） |
| `return_dict` | bool | True | 返回 StableDiffusionPipelineOutput 对象 |
| `attention_kwargs` | Dict[str, Any] | None | 注意力机制的额外参数 |
| `callback_on_step_end` | Callable | None | 每个推理步骤结束时的回调函数 |
| `callback_on_step_end_tensor_inputs` | List[str] | ["latents"] | 回调函数的张量输入 |
| `max_sequence_length` | int | 512 | 分词器的最大序列长度 |

---

## API 端点 `/v1/images/edits` 支持的参数

### 请求参数（FormData）

| 参数名 | 类型 | 是否必需 | 默认值 | 说明 |
|--------|------|--------|--------|------|
| `prompt` | string | ✓ | - | 编辑提示文本 |
| `images` | files | ✓ | - | 输入图像文件（支持单张或多张，作为整体批处理） |
| `negative_prompt` | string | ✗ | null | 负面提示文本 |
| `size` | string | ✗ | "1024x1024" | 图像尺寸，格式为 "WIDTHxHEIGHT" |
| `n` | integer | ✗ | 1 | 每张输入图像生成的变体数量（1-10） |
| `num_inference_steps` | integer | ✗ | 50 | 推理步数 |
| `guidance_scale` | float | ✗ | null | 引导尺度 |
| `true_cfg_scale` | float | ✗ | 4.0 | 分类器自由引导尺度 |
| `output_type` | string | ✗ | "pil" | 输出格式："pil" 或 "pt" |
| `max_sequence_length` | integer | ✗ | 512 | 最大序列长度 |

### 认证

- 类型：HTTP Basic Auth（可选，仅在设置 `API_KEY` 环境变量时需要）
- 用户名：任意
- 密码：`API_KEY` 环境变量的值

### 响应格式

```json
{
  "created": 1234567890,
  "data": [
    {
      "b64_json": "base64编码的图像数据"
    }
  ],
  "usage": {
    "processing_time_seconds": 12.34,
    "input_images": 2,
    "generated_images": 4
  }
}
```

### 多张图片处理说明

**关键特性**：
- `images` 参数接受**单张或多张图像**，作为一个**整体**传递给 pipeline
- Pipeline 会一次性处理所有输入图像（批处理），而不是逐个处理
- `n` 参数控制每张输入图像生成的变体数量
- **总生成数 = 输入图像数 × n**

**示例**：
- 输入 2 张图像，`n=2` → 生成 4 张图像（每张输入生成 2 个变体）
- 输入 1 张图像，`n=3` → 生成 3 张图像（1 张输入生成 3 个变体）

---

## 使用示例

### cURL 示例

#### 单张图像

```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -H "Authorization: Basic $(echo -n 'user:your-api-key' | base64)" \
  -F "prompt=make the sky more blue" \
  -F "images=@input.png" \
  -F "size=1024x1024" \
  -F "n=1" \
  -F "num_inference_steps=50" \
  -F "guidance_scale=7.5" \
  -F "negative_prompt=low quality, blurry"
```

#### 多张图像（批处理）

```bash
# 传递 3 张图像，每张生成 2 个变体，总共 6 张输出
curl -X POST http://localhost:8000/v1/images/edits \
  -H "Authorization: Basic $(echo -n 'user:your-api-key' | base64)" \
  -F "prompt=make the sky more blue" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "images=@photo3.jpg" \
  -F "n=2" \
  -F "num_inference_steps=50" \
  -F "guidance_scale=7.5"
```

说明：上面的请求会处理 3 张图像，每张生成 2 个变体，总共产生 6 张输出图像。
所有 3 张图像会通过**一次** pipeline 调用进行批处理。
  -F "prompt=enhance colors" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "n=2" \
  -F "num_inference_steps=50"
```

### Python 示例

```python
import requests
from PIL import Image
import base64
import io

url = "http://localhost:8000/v1/images/edits"
auth = ("user", "your-api-key")

# 单张或多张图像处理
image_files = ["input1.png", "input2.png"]  # 支持多个

files = {}
with open(image_files[0], "rb") as f:
    files["images"] = (image_files[0], f, "image/png")
    
    if len(image_files) > 1:
        # 处理多张图像
        # FastAPI List[UploadFile] 需要特殊处理
        files = {"images": []}
        for fname in image_files:
            with open(fname, "rb") as img:
                files["images"].append((fname, img.read(), "image/png"))
    
    data = {
        "prompt": "make the sky more blue",
        "negative_prompt": "low quality, blurry",
        "size": "1024x1024",
        "n": 2,
        "num_inference_steps": 50,
        "guidance_scale": 7.5,
        "true_cfg_scale": 4.0,
        "max_sequence_length": 512,
        "output_type": "pil"
    }
    
    response = requests.post(url, files=files, data=data, auth=auth)
    result = response.json()
    
    # 保存结果
    for idx, item in enumerate(result["data"]):
        image_data = base64.b64decode(item["b64_json"])
        img = Image.open(io.BytesIO(image_data))
        img.save(f"output_{idx}.png")
    
    print(f"生成了 {result['usage']['generated_images']} 张图像")
    print(f"处理时间: {result['usage']['processing_time_seconds']:.2f}s")
```

---

## 参数映射关系

| API 参数 | Pipeline 参数 | 说明 |
|---------|--------------|------|
| `prompt` | `prompt` | 直接传递 |
| `images` | `image` | 单张或批量处理：逐个传递给 pipeline |
| `negative_prompt` | `negative_prompt` | 可选，如果提供则传递 |
| `size` | `width`, `height` | 从 "WIDTHxHEIGHT" 格式解析 |
| `n` | - | 每张输入图像生成 n 个变体（总输出 = input_images * n） |
| `num_inference_steps` | `num_inference_steps` | 直接传递 |
| `guidance_scale` | `guidance_scale` | 可选，如果提供则传递 |
| `true_cfg_scale` | `true_cfg_scale` | 直接传递 |
| `output_type` | `output_type` | 直接传递，支持 "pil" 和 "pt" |
| `max_sequence_length` | `max_sequence_length` | 直接传递 |

---

## 实现细节

### 参数验证

- `prompt` 和 `image` 是必需的
- `n` 必须在 1-10 之间
- `num_inference_steps` 必须 >= 1
- `output_type` 必须是 "pil" 或 "pt"
- `size` 必须符合 "WIDTHxHEIGHT" 格式，且宽度和高度都必须 > 0

### 输出处理

- 当 `output_type` 为 "pil" 时，直接从输出的 PIL 图像生成 base64
- 当 `output_type` 为 "pt" 时，先将张量转换为 PIL 图像，再生成 base64

### 可选参数处理

- `negative_prompt` 和 `guidance_scale` 仅在提供时才传递给 pipeline
- 其他参数始终传递，使用默认值

---

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `QWEN_MODEL_DIR` | 模型目录路径 | "/mnt/models" |
| `API_KEY` | API 密钥（可选） | 未设置 |
| `DEVICE_MAP` | 设备映射策略 | "balanced" |
| `HOST` | 服务绑定地址 | "0.0.0.0" |
| `PORT` | 服务端口 | 8000 |
| `LOG_LEVEL` | 日志级别 | "info" |
| `RELOAD` | 是否启用代码重载 | false |

### DEVICE_MAP 详细说明

**`DEVICE_MAP=cuda`**
- 将整个模型放在单个 GPU 上
- 适用于：单 GPU 环境
- 问题：多 GPU 时只使用一张卡，导致 OOM

**`DEVICE_MAP=balanced`** ⭐ **推荐**
- 将模型层分散到多个可用的 GPU 上
- 适用于：多 GPU 环境（2 张或更多）
- 优势：充分利用所有 GPU，避免单卡 OOM

**配置示例：**

```bash
# 单张 GPU 服务器
DEVICE_MAP=cuda

# 双张 GPU 服务器（推荐）
DEVICE_MAP=balanced

# 多张 GPU 服务器（推荐）
DEVICE_MAP=balanced
```

---

## 更新日志

### v1.1.0 (当前版本)

- ✅ 添加了 `negative_prompt` 支持
- ✅ 添加了 `num_inference_steps` 支持
- ✅ 添加了 `guidance_scale` 支持
- ✅ 添加了 `true_cfg_scale` 支持
- ✅ 添加了 `output_type` 支持
- ✅ 添加了 `max_sequence_length` 支持
- ✅ 添加了 `height` 和 `width` 参数（通过解析 `size` 参数）
- ✅ 改进了参数验证
- ✅ 改进了输出处理（支持多种输出类型）

### v1.0.0

- 初始版本
- 仅支持基础的 `prompt`, `image`, `size`, `n` 参数
