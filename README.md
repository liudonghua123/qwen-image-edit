# Qwen Image Edit API

一个基于 FastAPI 的高性能图像编辑服务，使用 Qwen Image Edit 模型实现 OpenAI 兼容的 API。

## 功能特性

- ✅ **批量处理**：支持单张或多张图像的批量处理
- ✅ **OpenAI 兼容 API**：`/v1/images/edits` 端点与 OpenAI 接口兼容
- ✅ **健康检查端点**：支持 `/health` 和 `/ready` 用于容器编排
- ✅ **可选 API 认证**：HTTP Basic Auth（可选，密码为 `API_KEY`）
- ✅ **完善的错误处理**：标准化错误响应和详细日志
- ✅ **结构化日志**：便于监控和调试
- ✅ **GPU 加速**：支持 CUDA 加速推理

## 快速开始

### 环境变量配置

复制 `.env.example` 到 `.env`：

```bash
cp .env.example .env
```

编辑 `.env` 文件配置以下变量：

```bash
QWEN_MODEL_DIR=/path/to/qwen/models    # 模型目录路径
API_KEY=your-secret-key                # API 密钥（可选，不设置则禁用认证）
```

你也可以设置 `DEVICE_MAP`（可选）：
- `balanced`：将模型层分散在多个 GPU 上（**推荐用于多 GPU 环境**）
- `cuda`：将模型放在单个 GPU 上（仅用于单 GPU 环境）

**⚠️ 重要提示**：如果有多张 GPU（2 张或更多）：
- **必须** 使用 `DEVICE_MAP=balanced`
- 使用 `DEVICE_MAP=cuda` 会导致只使用一张卡，其他卡闲置，容易 OOM

例如：

```bash
# 单张 GPU
DEVICE_MAP=cuda

# 双张或多张 GPU（推荐）
DEVICE_MAP=balanced
```

**注意**：`API_KEY` 是可选的：
- 如果设置了 `API_KEY`，所有请求都需要提供有效的 Bearer Token
- 如果不设置 `API_KEY`，所有请求都无需认证

### Docker 运行

构建镜像：

```bash
docker build -t liudonghua123/qwen-image-edit .
```

运行容器（推荐多 GPU 配置）：

```bash
# 无认证模式，单 GPU
docker run --gpus all \
  -e QWEN_MODEL_DIR=/mnt/models \
  -e DEVICE_MAP=cuda \
  -v /path/to/models:/mnt/models \
  -p 8000:8000 \
  liudonghua123/qwen-image-edit

# 无认证模式，多 GPU（推荐）
docker run --gpus all \
  -e QWEN_MODEL_DIR=/mnt/models \
  -e DEVICE_MAP=balanced \
  -v /path/to/models:/mnt/models \
  -p 8000:8000 \
  liudonghua123/qwen-image-edit

# 启用认证模式，多 GPU
docker run --gpus all \
  -e QWEN_MODEL_DIR=/mnt/models \
  -e DEVICE_MAP=balanced \
  -e API_KEY=your-secret-key \
  -v /path/to/models:/mnt/models \
  -p 8000:8000 \
  liudonghua123/qwen-image-edit
```

### 本地开发运行

安装并本地开发运行：

推荐使用 `pyproject.toml` 安装依赖并可选地以可编辑模式安装：

```bash
# 安装到当前环境（会使用 pyproject.toml 中的依赖声明）
pip install .

# 或者可编辑安装（便于开发）
pip install -e .
```

注意：`torch` 可能需要与目标 CUDA 版本匹配的 wheel，视你的 GPU 环境而定；如果需要，请参考 PyTorch 官方安装命令以选择合适的 CUDA 轮子。

运行服务（推荐使用 `main.py` 入口或直接用 `uvicorn`）：

```bash
# 使用 uvicorn 指向 main:app
uvicorn main:app --host 0.0.0.0 --port 8000

# 或直接用 python
python main.py
```

## API 文档

### 1. 健康检查

**端点**: `GET /health`

检查服务是否正在运行。

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-26T10:00:00.000000",
  "version": "1.0.0"
}
```

### 2. 就绪检查

**端点**: `GET /ready`

检查服务是否已加载模型并准备好处理请求。

**响应**:
```json
{
  "status": "ready",
  "model_loaded": true,
  "timestamp": "2025-11-26T10:00:00.000000"
}
```

**错误响应** (503):
```json
{
  "error": "MODEL_NOT_READY",
  "message": "Model is not ready yet"
}
```

### 3. 图像编辑

**端点**: `POST /v1/images/edits`

使用文本提示编辑图像。

**认证**:

本项目使用 HTTP Basic Auth（当设置了 `API_KEY` 时启用）。用户名可以是任意字符串，密码必须是 `API_KEY` 的值。

示例：使用 `curl` 提供 Basic Auth（用户名 `user`，密码为 `API_KEY`）

```bash
# 启用认证模式（使用 -u username:password）
curl -X POST "http://localhost:8000/v1/images/edits" \
  -u "user:your-secret-key" \
  -F "prompt=a beautiful landscape" \
  -F "images=@image.jpg" \
  -F "n=1"
```

**请求体** (multipart/form-data):
- `prompt` (string, 必需): 编辑描述
- `images` (files, 必需): 一个或多个原始图像文件（支持批处理）
- `size` (string, 可选): 输出大小，默认 "1024x1024"
- `n` (integer, 可选): 每张输入图像生成的变体数，默认 1，范围 1-10
- `negative_prompt` (string, 可选): 负面提示文本
- `num_inference_steps` (integer, 可选): 推理步数，默认 50
- `guidance_scale` (float, 可选): 引导尺度

**示例请求**:

```bash
# 单张图像编辑
curl -X POST "http://localhost:8000/v1/images/edits" \
  -F "prompt=a beautiful landscape" \
  -F "images=@image.jpg" \
  -F "n=1"

# 批量处理多张图像（一次 pipeline 调用处理所有图像）
curl -X POST "http://localhost:8000/v1/images/edits" \
  -F "prompt=enhance colors" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "images=@photo3.jpg" \
  -F "n=2"
```
说明：上面的批量请求会处理 3 张图像，每张生成 2 个变体，总共产生 6 张输出。
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "images=@photo3.jpg" \
  -F "n=2"

# 启用认证模式
curl -X POST "http://localhost:8000/v1/images/edits" \
  -H "Authorization: Basic $(echo -n 'user:your-secret-key' | base64)" \
  -F "prompt=a beautiful landscape" \
  -F "images=@image.jpg" \
  -F "n=1"
```

**成功响应** (200):
```json
{
  "created": 1700000000,
  "data": [
    {
      "b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    }
  ],
  "usage": {
    "processing_time_seconds": 12.34,
    "input_images": 2,
    "generated_images": 4
  }
}
```

**错误响应示例**:

401 - 未授权:
```json
{
  "error": "UNAUTHORIZED",
  "message": "Invalid API key"
}
```

400 - 无效输入:
```json
{
  "error": "INVALID_INPUT",
  "message": "Image is required"
}
```

500 - 服务器错误:
```json
{
  "error": "GENERATION_ERROR",
  "message": "Image generation failed: ..."
}
```

## 错误代码

| 错误代码 | HTTP 状态 | 说明 |
|---------|----------|------|
| `UNAUTHORIZED` | 401 | API 密钥无效或缺失（仅在启用认证时） |
| `INVALID_INPUT` | 400 | 输入参数无效 |
| `MODEL_NOT_READY` | 503 | 模型未加载 |
| `GENERATION_ERROR` | 500 | 图像生成失败 |
| `INTERNAL_ERROR` | 500 | 内部服务器错误 |

## Python 客户端示例

```python
import requests
import base64
from PIL import Image
import io

API_URL = "http://localhost:8000/v1/images/edits"
API_KEY = None  # 不需要认证时设为 None

def edit_images(image_paths, prompt, n=1):
    """编辑一张或多张图像"""
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    files = []
    for image_path in image_paths:
        with open(image_path, 'rb') as f:
            files.append(('images', (image_path, f.read(), 'image/jpeg')))
    
    data = {
        'prompt': prompt,
        'n': n,
    }
    
    response = requests.post(API_URL, headers=headers, files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        for idx, item in enumerate(result['data']):
            b64_image = item['b64_json']
            image_bytes = base64.b64decode(b64_image)
            img = Image.open(io.BytesIO(image_bytes))
            img.save(f"output_{idx}.jpg")
        
        print(f"输入: {result['usage']['input_images']} 张图像")
        print(f"输出: {result['usage']['generated_images']} 张图像")
        return result['data']
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# 使用示例
# 单张图像
edit_images(["input.jpg"], "add a red flower")

# 多张图像
edit_images(["photo1.jpg", "photo2.jpg"], "enhance colors", n=2)
```

## 监控

### 健康检查集成

适用于 Docker Compose 和 Kubernetes：

**Docker Compose**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**Kubernetes**:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 600
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 600
  periodSeconds: 10
```

## 日志输出

所有请求和错误都会输出结构化日志：

```
2025-11-26 10:00:00 - image_edit_server - INFO - Loading model from /mnt/models...
2025-11-26 10:00:30 - image_edit_server - INFO - Model loaded successfully
2025-11-26 10:00:45 - image_edit_server - INFO - Processing image edit request: prompt='a beautiful landscape', n=1
2025-11-26 10:01:00 - image_edit_server - INFO - Image edit completed in 15.23s, generated 1 image(s)
```

## 许可证

见 LICENSE 文件。
