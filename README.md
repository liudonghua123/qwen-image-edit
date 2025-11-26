# Qwen Image Edit API

一个基于 FastAPI 的高性能图像编辑服务，使用 Qwen Image Edit 模型实现 OpenAI 兼容的 API。

## 功能特性

- ✅ **OpenAI 兼容 API**：`/v1/images/edits` 端点与 OpenAI 接口兼容
- ✅ **健康检查端点**：支持 `/health` 和 `/ready` 用于容器编排
- ✅ **可选 API 认证**：Bearer Token 身份验证（可选）
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

**注意**：`API_KEY` 是可选的：
- 如果设置了 `API_KEY`，所有请求都需要提供有效的 Bearer Token
- 如果不设置 `API_KEY`，所有请求都无需认证

### Docker 运行

构建镜像：

```bash
docker build -t liudonghua123/qwen-image-edit .
```

运行容器：

```bash
# 无认证模式（推荐用于开发）
docker run --gpus all \
  -e QWEN_MODEL_DIR=/mnt/models \
  -v /path/to/models:/mnt/models \
  -p 8000:8000 \
  liudonghua123/qwen-image-edit

# 启用认证模式（推荐用于生产）
docker run --gpus all \
  -e QWEN_MODEL_DIR=/mnt/models \
  -e API_KEY=your-secret-key \
  -v /path/to/models:/mnt/models \
  -p 8000:8000 \
  liudonghua123/qwen-image-edit
```

### 本地开发运行

安装依赖：

```bash
pip install fastapi uvicorn diffusers transformers accelerate pillow python-multipart python-dotenv
```

运行服务：

```bash
uvicorn image_edit_server:app --host 0.0.0.0 --port 8000
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

**请求头**:
```
Authorization: Bearer your-api-key  # 仅当设置了 API_KEY 环境变量时需要
```

**请求体** (multipart/form-data):
- `prompt` (string, 必需): 编辑描述
- `image` (file, 必需): 原始图像文件
- `mask` (file, 可选): 掩码图像文件
- `size` (string, 可选): 输出大小，默认 "1024x1024"
- `n` (integer, 可选): 生成数量，默认 1，范围 1-10

**示例请求**:

```bash
# 无认证模式
curl -X POST "http://localhost:8000/v1/images/edits" \
  -F "prompt=a beautiful landscape" \
  -F "image=@image.jpg" \
  -F "n=1"

# 启用认证模式
curl -X POST "http://localhost:8000/v1/images/edits" \
  -H "Authorization: Bearer your-api-key" \
  -F "prompt=a beautiful landscape" \
  -F "image=@image.jpg" \
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
    "processing_time_seconds": 12.34
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

def edit_image(prompt, image_path, mask_path=None):
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    files = {
        'prompt': (None, prompt),
        'n': (None, '1'),
    }
    
    with open(image_path, 'rb') as f:
        files['image'] = ('image.jpg', f, 'image/jpeg')
        
        if mask_path:
            with open(mask_path, 'rb') as m:
                files['mask'] = ('mask.jpg', m, 'image/jpeg')
                response = requests.post(API_URL, headers=headers, files=files)
        else:
            response = requests.post(API_URL, headers=headers, files=files)
    
    if response.status_code == 200:
        result = response.json()
        b64_image = result['data'][0]['b64_json']
        image_bytes = base64.b64decode(b64_image)
        return Image.open(io.BytesIO(image_bytes))
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# 使用示例
image = edit_image("add a red flower", "input.jpg")
if image:
    image.save("output.jpg")
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
  initialDelaySeconds: 40
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 40
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
