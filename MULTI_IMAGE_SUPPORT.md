# 多张图像支持完整说明

## 概述

Qwen Image Edit API 现已全面支持**多张图像批量处理**。用户可以在单个 API 请求中上传多张图像进行并行编辑。

## 关键变更

### API 参数变更

| 属性 | v1.1.0 | v1.2.0 |
|------|--------|--------|
| 参数名 | `image` | `images` |
| 参数类型 | `UploadFile` | `List[UploadFile]` |
| 支持图像数 | 1 张 | 1-N 张 |
| 破坏兼容性 | - | ⚠️ 是 |

### 响应格式变更

**v1.1.0:**
```json
{
  "usage": {
    "processing_time_seconds": 12.34
  }
}
```

**v1.2.0:**
```json
{
  "usage": {
    "processing_time_seconds": 12.34,
    "input_images": 2,        // 新增
    "generated_images": 4     // 新增
  }
}
```

## 使用指南

### 批量处理公式

```
总输出数 = 输入图像数 × n 参数

示例：
  3 张输入 × 1 个变体 = 3 张输出
  3 张输入 × 2 个变体 = 6 张输出
  3 张输入 × 4 个变体 = 12 张输出
```

### cURL 示例

#### 单张图像
```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -F "prompt=enhance colors" \
  -F "images=@photo.jpg"
```

#### 多张图像
```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -F "prompt=enhance colors" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "images=@photo3.jpg" \
  -F "n=2"
```

### Python 客户端

```python
import requests
import base64
from PIL import Image
import io

def batch_edit_images(image_paths, prompt, n=1):
    """批量编辑多张图像"""
    
    url = "http://localhost:8000/v1/images/edits"
    
    # 准备多个文件
    files = []
    for image_path in image_paths:
        with open(image_path, "rb") as f:
            files.append(("images", (image_path, f.read(), "image/jpeg")))
    
    data = {
        "prompt": prompt,
        "negative_prompt": "low quality, blurry",
        "num_inference_steps": 50,
        "n": n,
    }
    
    # 发送请求
    response = requests.post(url, files=files, data=data)
    result = response.json()
    
    # 保存结果
    for idx, item in enumerate(result["data"]):
        image_data = base64.b64decode(item["b64_json"])
        img = Image.open(io.BytesIO(image_data))
        img.save(f"output_{idx}.png")
    
    # 显示统计
    print(f"输入: {result['usage']['input_images']} 张")
    print(f"输出: {result['usage']['generated_images']} 张")
    print(f"用时: {result['usage']['processing_time_seconds']:.2f}s")
    
    return result

# 使用示例
batch_edit_images(
    ["photo1.jpg", "photo2.jpg", "photo3.jpg"],
    prompt="enhance colors and details",
    n=2  # 每张生成 2 个变体
)
```

## 实现细节

### 内部处理流程

```
上传多张图像
     ↓
[为每张图像创建一个列表副本]
     ↓
[对于每张图像，调用 pipeline n 次]
     ↓
[收集所有输出结果]
     ↓
[返回所有生成的图像的 base64 编码]
```

### 代码示例

```python
# API 端点接收多张图像
images: List[UploadFile] = File(...)

# 加载所有图像为 PIL Image
pil_images: List[Image.Image] = []
for image_file in images:
    img = Image.open(io.BytesIO(await image_file.read())).convert("RGB")
    pil_images.append(img)

# 对每张图像生成 n 个变体
results = []
for input_image in pil_images:
    for _ in range(n):
        output = pipe(
            prompt=prompt,
            image=input_image,
            # ... 其他参数 ...
        )
        results.append({"b64_json": pil_to_b64(output.images[0])})
```

## 性能考虑

### 建议配置

| 输入数量 | n 值 | 推荐配置 |
|---------|------|---------|
| 1 张 | 1-4 | 1024×1024 @ 50 步 |
| 1 张 | 5-10 | 512×512 @ 50 步 |
| 2-3 张 | 1-2 | 1024×1024 @ 50 步 |
| 4+ 张 | 1 | 768×768 @ 30 步 |

### 内存预估

```
GPU 内存需求 ≈ (输入数 + n) × 图像尺寸

示例：
  单张 1024×1024 @ n=1: ~4-6 GB
  单张 1024×1024 @ n=2: ~6-8 GB
  2 张 1024×1024 @ n=1: ~6-8 GB
  3 张 1024×1024 @ n=1: ~8-10 GB
```

## 故障排除

### 问题：上传多张时出现错误

**症状：** `"At least one image is required"`

**原因：** 图像列表为空或格式不正确

**解决方案：**
```bash
# ✓ 正确：使用 -F 'images=@file' 多次
curl ... -F 'images=@photo1.jpg' -F 'images=@photo2.jpg'

# ✗ 错误：不要这样做
curl ... -F 'image=@photo1.jpg' -F 'image=@photo2.jpg'
```

### 问题：批量处理时速度慢

**原因：** 总处理数太多 = 输入数 × n

**解决方案：**
1. 减少输入图像数
2. 减少 `n` 值
3. 减少 `num_inference_steps`
4. 减少图像尺寸

### 问题：内存不足

**原因：** 批量处理消耗更多内存

**解决方案：**
```python
# 分批处理，而不是一次全部
batch_size = 2

for i in range(0, len(all_images), batch_size):
    batch = all_images[i:i+batch_size]
    result = batch_edit_images(batch, prompt)
```

## 迁移指南

### 从 v1.1.0 升级到 v1.2.0

#### 更新 cURL 命令

```bash
# v1.1.0
curl ... -F "image=@photo.jpg"

# v1.2.0
curl ... -F "images=@photo.jpg"
```

#### 更新 Python 代码

```python
# v1.1.0
with open("photo.jpg", "rb") as f:
    files = {"image": f}
    response = requests.post(url, files=files, data=data)

# v1.2.0
files = []
for image_path in image_paths:
    with open(image_path, "rb") as f:
        files.append(("images", (image_path, f.read(), "image/jpeg")))
response = requests.post(url, files=files, data=data)
```

## 限制和约束

| 约束项 | 限制值 |
|--------|--------|
| 最大输入图像数 | 无硬限制（取决于内存） |
| 最大 n 值 | 10 |
| 最大图像尺寸 | 2048×2048 |
| 最大推理步数 | 100（建议） |
| API 超时 | 根据服务器配置 |

## 最佳实践

### ✅ 推荐做法

1. **合理分批** - 3-5 张图像为一批
2. **合理选择 n** - 大批量时使用 n=1，少量时用 n=2-3
3. **预设尺寸** - 所有输入图像使用相同的尺寸
4. **异步处理** - 在应用中实现异步队列处理多个批次

### ❌ 避免做法

1. **一次上传数百张** - 会导致内存溢出
2. **使用极高参数** - 10 张 × 10 个变体 = 100 张输出很慢
3. **混合不同尺寸** - 会导致内存分配不均
4. **同步等待所有结果** - 考虑实现后台任务队列

## 参考资源

- [README.md](README.md) - API 使用文档
- [PARAMETERS.md](PARAMETERS.md) - 完整参数参考
- [API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md) - 快速参考指南
- [test_multi_images.py](test_multi_images.py) - 验证测试脚本

