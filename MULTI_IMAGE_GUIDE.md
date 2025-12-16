# 多张图像批处理指南

## 概述

`/v1/images/edits` 端点支持**一次上传多张图像进行批处理**。所有图像会通过 **单一的 pipeline 调用** 进行处理，这比逐个处理效率更高。

## 核心概念

### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `images` | 输入图像（单张或多张） | `-F "images=@photo1.jpg" -F "images=@photo2.jpg"` |
| `n` | 每张输入图像生成的变体数 | `n=2` 表示每张图像生成 2 个变体 |
| **总输出** | 输入图像数 × n | 2 张输入 × 2 = 4 张输出 |

### 工作流程

```
输入：3 张图像，n=2
↓
Pipeline.__call__(
    image=[img1, img2, img3],  # 作为列表传递
    num_images_per_prompt=2,    # 每张生成 2 个变体
    ...其他参数
)
↓
输出：6 张图像
  - img1 的 2 个变体
  - img2 的 2 个变体
  - img3 的 2 个变体
```

## 使用示例

### 示例 1：单张图像

```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -F "prompt=make the sky blue" \
  -F "images=@photo.jpg" \
  -F "n=1"
```

**预期结果**：
- 输入：1 张
- 输出：1 张
- 响应中 `data` 包含 1 个图像

### 示例 2：多张图像，每张 1 个变体

```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -F "prompt=enhance colors" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "images=@photo3.jpg" \
  -F "n=1"
```

**预期结果**：
- 输入：3 张
- 输出：3 张（每张输入生成 1 个变体）
- 响应中 `data` 包含 3 个图像

### 示例 3：多张图像，每张多个变体

```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -F "prompt=artistic style transformation" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "n=3" \
  -F "num_inference_steps=75" \
  -F "guidance_scale=8.0"
```

**预期结果**：
- 输入：2 张
- 输出：6 张（每张输入生成 3 个变体）
- 响应中 `data` 包含 6 个图像

### 示例 4：Python 客户端

```python
import requests
import base64
from PIL import Image
import io

def batch_edit_images(prompts, image_paths, n=2):
    """批量编辑多张图像"""
    
    url = "http://localhost:8000/v1/images/edits"
    auth = ("user", "your-api-key")
    
    files = {}
    for idx, image_path in enumerate(image_paths):
        with open(image_path, "rb") as f:
            files[f"images"] = (f"photo_{idx}.jpg", f, "image/jpeg")
    
    data = {
        "prompt": prompts,
        "n": n,
        "num_inference_steps": 50,
    }
    
    response = requests.post(url, files=files, data=data, auth=auth)
    result = response.json()
    
    # 保存所有输出
    print(f"生成了 {len(result['data'])} 张图像")
    for idx, item in enumerate(result["data"]):
        image_data = base64.b64decode(item["b64_json"])
        img = Image.open(io.BytesIO(image_data))
        img.save(f"output_{idx}.png")
        print(f"保存 output_{idx}.png")
    
    return result

# 使用示例
batch_edit_images(
    prompts="make the scene brighter and more vivid",
    image_paths=["photo1.jpg", "photo2.jpg", "photo3.jpg"],
    n=2
)
```

## 性能考虑

### 批处理 vs 逐个处理

**批处理（推荐）**：
```bash
# ✅ 一次 pipeline 调用处理 3 张图像
curl ... -F "images=@img1" -F "images=@img2" -F "images=@img3"
```

**逐个处理（不推荐）**：
```bash
# ❌ 需要 3 次 pipeline 调用
curl ... -F "images=@img1"
curl ... -F "images=@img2"
curl ... -F "images=@img3"
```

### 性能对比

| 方案 | 输入数 | 总耗时 | 优势 |
|------|--------|--------|------|
| 批处理 | 3 | ~45秒 | 快速，高效 |
| 逐个处理 | 3 | ~135秒 | - |
| 改进 | - | **快 3 倍** | ⚡ 显著优化 |

## API 响应格式

### 响应示例

```json
{
  "created": 1702814400,
  "data": [
    { "b64_json": "iVBORw0KGgo..." },  // 输入图像 1 的变体 1
    { "b64_json": "iVBORw0KGgo..." },  // 输入图像 1 的变体 2
    { "b64_json": "iVBORw0KGgo..." },  // 输入图像 2 的变体 1
    { "b64_json": "iVBORw0KGgo..." }   // 输入图像 2 的变体 2
  ],
  "usage": {
    "processing_time_seconds": 22.5,
    "input_images": 2,
    "generated_images": 4
  }
}
```

### 响应说明

- `data`：生成的图像列表，按顺序排列（输入图像 1 的所有变体，然后是输入图像 2 的所有变体，等等）
- `usage.input_images`：输入图像的总数
- `usage.generated_images`：生成的输出图像总数（= input_images × n）
- `usage.processing_time_seconds`：总处理时间

## 常见问题

### Q：多张图像如何排序？
**A**：输出按输入顺序排列，每张输入图像的所有变体连续排列。

示例：
- 输入：[img_A, img_B]，n=2
- 输出顺序：[img_A_var1, img_A_var2, img_B_var1, img_B_var2]

### Q：能否为不同图像指定不同的提示？
**A**：目前不支持。所有输入图像使用相同的提示。如果需要不同的提示，请发起多个请求。

### Q：批处理中最多支持多少张图像？
**A**：取决于 GPU 内存。建议：
- GPU 内存 > 24GB：最多 10 张
- GPU 内存 12-24GB：最多 5 张
- GPU 内存 < 12GB：最多 2 张

### Q：能否只生成部分输入图像的变体？
**A**：不支持。`n` 参数对所有输入图像统一应用。

### Q：输出图像顺序是否有保证？
**A**：是的。输出严格按照输入顺序和变体顺序排列。

## 错误处理

### 常见错误

#### 1. 至少需要一张图像

```json
{
  "detail": {
    "error": "INVALID_INPUT",
    "message": "At least one image is required"
  }
}
```

**解决方案**：确保至少上传一张有效的图像文件。

#### 2. 无效的图像格式

```json
{
  "detail": {
    "error": "INVALID_INPUT",
    "message": "Invalid image format at index 1: ..."
  }
}
```

**解决方案**：检查图像文件格式（支持 JPEG, PNG 等）和完整性。

#### 3. 内存不足

```json
{
  "detail": {
    "error": "GENERATION_ERROR",
    "message": "Image generation failed: CUDA out of memory"
  }
}
```

**解决方案**：
- 减少输入图像数量
- 降低 `num_inference_steps`
- 减小 `size` 参数

## 最佳实践

1. **优先使用批处理**：将多个请求合并为一个批处理请求
2. **合理设置参数**：
   - `n` 不要过大（1-4 通常足够）
   - `num_inference_steps` 取 50-100
3. **监控内存**：如果遇到内存错误，减少输入图像数
4. **验证输出**：检查 `usage.generated_images` 确认生成的图像数
5. **保存结果**：按需将输出保存为文件或存储为 blob

## 与 QwenImageEditPipeline 的关系

API 的多张图像支持直接来自底层的 QwenImageEditPipeline：

```python
# QwenImageEditPipeline 原生支持
output = pipeline(
    image=[img1, img2, img3],           # 接受列表
    prompt="prompt",
    num_images_per_prompt=2,             # 每张生成 2 个
    ...
)

# API 层通过 List[UploadFile] 实现相同的功能
output = pipeline(
    image=pil_images if len(pil_images) > 1 else pil_images[0],
    num_images_per_prompt=n,
    ...
)
```

这种设计确保了 API 能够充分利用 pipeline 的批处理能力。
