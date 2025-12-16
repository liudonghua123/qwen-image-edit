# API 快速参考指南

## 端点

- **POST** `/v1/images/edits` - 编辑图像
- **GET** `/health` - 健康检查
- **GET** `/ready` - 就绪检查

---

## `/v1/images/edits` 请求示例

### 最小请求（单张图像）

```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -F "prompt=make the sky blue" \
  -F "images=@input.png"
```

### 批量处理（多张图像）

```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -F "prompt=enhance colors" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "images=@photo3.jpg" \
  -F "n=2"
```

结果：3 张输入图像 × 2 个变体 = 6 张输出图像

### 完整请求（所有参数）

```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -H "Authorization: Basic $(echo -n 'user:api-key' | base64)" \
  -F "prompt=make the sky more vibrant blue" \
  -F "negative_prompt=dark, low quality, blurry" \
  -F "images=@input.png" \
  -F "size=1024x1024" \
  -F "n=2" \
  -F "num_inference_steps=50" \
  -F "guidance_scale=7.5" \
  -F "true_cfg_scale=4.0" \
  -F "output_type=pil" \
  -F "max_sequence_length=512"
```

---

## 参数说明

### 必需参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `prompt` | string | 图像编辑的文本提示 |
| `images` | file[] | 一个或多个待编辑的图像文件 |

### 常用可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `negative_prompt` | string | - | 不想要的内容描述 |
| `size` | string | "1024x1024" | 输出尺寸，格式：`WIDTHxHEIGHT` |
| `n` | integer | 1 | 每张输入图像生成的变体数量（1-10） |
| `num_inference_steps` | integer | 50 | 推理步数（更多=更好但更慢） |
| `guidance_scale` | float | - | 遵循提示的程度（7.5推荐） |
| `true_cfg_scale` | float | 4.0 | 分类器自由引导 |

### 高级参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `output_type` | string | "pil" | 输出格式："pil"或"pt" |
| `max_sequence_length` | integer | 512 | 文本编码最大长度 |

---

## 常见用例

### 用例 1：单张图像编辑

```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -F "prompt=make the background sunny" \
  -F "images=@photo.jpg"
```

### 用例 2：批量图像处理

```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -F "prompt=enhance colors and details" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "images=@photo3.jpg" \
  -F "negative_prompt=artifacts, distortion" \
  -F "num_inference_steps=75" \
  -F "guidance_scale=8.0"
```

### 用例 3：生成多个变体

```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -F "prompt=different artistic style" \
  -F "images=@photo.jpg" \
  -F "n=4" \
  -F "size=512x512"
```

### 用例 4：带认证的请求

```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -H "Authorization: Basic $(echo -n 'user:secret-key' | base64)" \
  -F "prompt=edit image" \
  -F "images=@photo.jpg"
```

---

## 响应格式

### 成功响应 (200 OK)

```json
{
  "created": 1702814400,
  "data": [
    {
      "b64_json": "iVBORw0KGgoAAAANSUhEUgAA..."
    }
  ],
  "usage": {
    "processing_time_seconds": 15.23,
    "input_images": 2,
    "generated_images": 4
  }
}
```

### 错误响应

#### 400 Bad Request - 无效输入

```json
{
  "detail": {
    "error": "INVALID_INPUT",
    "message": "Prompt cannot be empty"
  }
}
```

#### 401 Unauthorized - 认证失败

```json
{
  "detail": {
    "error": "UNAUTHORIZED",
    "message": "Invalid username or password"
  }
}
```

#### 503 Service Unavailable - 模型未加载

```json
{
  "detail": {
    "error": "MODEL_NOT_READY",
    "message": "Model is not ready yet"
  }
}
```

#### 500 Internal Server Error - 生成失败

```json
{
  "detail": {
    "error": "GENERATION_ERROR",
    "message": "Image generation failed: ..."
  }
}
```

---

## Python 客户端示例

```python
import requests
import base64
from PIL import Image
import io

def edit_images(image_paths, prompt, api_key=None):
    """编辑一张或多张图像"""
    
    url = "http://localhost:8000/v1/images/edits"
    
    # 准备认证（如果需要）
    auth = None
    if api_key:
        auth = ("user", api_key)
    
    # 准备请求
    files = []
    for image_path in image_paths:
        with open(image_path, "rb") as f:
            files.append(("images", (image_path, f.read(), "image/jpeg")))
    
    data = {
        "prompt": prompt,
        "negative_prompt": "low quality, blurry",
        "num_inference_steps": 50,
        "n": 2,  # 每张输入生成 2 个变体
    }
    
    # 发送请求
    response = requests.post(url, files=files, data=data, auth=auth)
    response.raise_for_status()
    
    result = response.json()
    
    # 保存结果
    for idx, item in enumerate(result["data"]):
        image_data = base64.b64decode(item["b64_json"])
        img = Image.open(io.BytesIO(image_data))
        img.save(f"output_{idx}.png")
    
    print(f"输入: {result['usage']['input_images']} 张")
    print(f"输出: {result['usage']['generated_images']} 张")
    print(f"处理时间: {result['usage']['processing_time_seconds']:.2f}s")
    return result

# 使用示例
# 单张图像
edit_images(["input.jpg"], "make the sky more blue", api_key="your-key-here")

# 多张图像批处理
edit_images(["photo1.jpg", "photo2.jpg", "photo3.jpg"], 
            "enhance colors", 
            api_key="your-key-here")
```

---

## 环境变量配置

创建 `.env` 文件来配置服务：

```bash
# 模型位置
QWEN_MODEL_DIR=/mnt/models

# API 认证（留空则禁用认证）
API_KEY=your-secret-key

# 设备配置
DEVICE_MAP=cuda          # "cuda" 或 "balanced"

# 服务配置
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
RELOAD=false
```

---

## 性能建议

| 参数 | 性能影响 | 建议 |
|------|--------|------|
| `num_inference_steps` | 线性增加时间 | 50-75为平衡，100+时非常慢 |
| `size` | 二次增加时间 | 512x512快速，1024x1024标准，2048+很慢 |
| `guidance_scale` | 小幅增加时间 | 7-8效果好 |
| `n` | 线性增加时间 | 1-2最快 |

---

## 故障排除

### 问题：模型加载失败

```
Failed to load model: ...
```

**解决方案：**
- 检查 `QWEN_MODEL_DIR` 指向正确的模型目录
- 确保模型文件完整：`ls -la /mnt/models/`
- 检查磁盘空间和权限

### 问题：CUDA 内存不足

```
CUDA out of memory
```

**解决方案：**
- 减少 `num_inference_steps`
- 减少图像 `size`
- 设置 `DEVICE_MAP=balanced`
- 使用 `torch.float16` 降低精度（已默认）

### 问题：生成速度慢

**解决方案：**
- 减少 `num_inference_steps`（50 vs 100+）
- 减少 `size`（768x768 vs 1024x1024）
- 使用 `n=1` 而不是多个生成
- 检查 GPU 占用率

---

## API 兼容性

本 API 遵循 OpenAI 图像编辑 API 的格式，但针对 Qwen 模型进行了优化。

兼容的参数子集：
- ✅ `prompt`, `image`, `size`, `n`
- ✅ OpenAI 兼容的请求和响应格式
- ⚡ 额外参数用于高级控制
