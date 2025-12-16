# 多 GPU 配置指南

## 问题描述

当服务器有多张 GPU（例如 2 张或更多）时，如果配置不当，会导致：
- ⚠️ 只使用一张 GPU，其他 GPU 闲置
- ⚠️ 显存 OOM（out of memory）
- ⚠️ 性能浪费

## 根本原因

Qwen Image Edit 模型使用 `device_map` 参数来控制如何加载模型到 GPU：

| 配置 | 行为 | 结果 |
|------|------|------|
| `DEVICE_MAP=cuda` | 整个模型加载到单个 GPU | ❌ 单卡 OOM |
| `DEVICE_MAP=balanced` | 模型层分散到多个 GPU | ✅ 充分利用所有 GPU |

## 解决方案

### ✅ 推荐配置

对于有多张 GPU 的环境，**必须**设置：

```bash
DEVICE_MAP=balanced
```

### 配置方法

#### 1. 使用 .env 文件

```bash
# .env
QWEN_MODEL_DIR=/mnt/models
DEVICE_MAP=balanced
```

#### 2. Docker 环境变量

```bash
docker run --gpus all \
  -e QWEN_MODEL_DIR=/mnt/models \
  -e DEVICE_MAP=balanced \
  -v /path/to/models:/mnt/models \
  -p 8000:8000 \
  liudonghua123/qwen-image-edit
```

#### 3. Docker Compose

```yaml
version: '3.8'
services:
  qwen-image-edit:
    image: liudonghua123/qwen-image-edit
    environment:
      QWEN_MODEL_DIR: /mnt/models
      DEVICE_MAP: balanced
    volumes:
      - /path/to/models:/mnt/models
    ports:
      - "8000:8000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

#### 4. Kubernetes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: qwen-image-edit
spec:
  containers:
  - name: qwen-image-edit
    image: liudonghua123/qwen-image-edit
    env:
    - name: QWEN_MODEL_DIR
      value: "/mnt/models"
    - name: DEVICE_MAP
      value: "balanced"
    resources:
      limits:
        nvidia.com/gpu: 2  # 请求 2 个 GPU
    volumeMounts:
    - name: models
      mountPath: /mnt/models
  volumes:
  - name: models
    hostPath:
      path: /path/to/models
```

## 验证配置

### 1. 启动服务后检查日志

```bash
docker logs <container-id> | grep -i device
```

应该看到：
```
INFO - Loading model from /mnt/models...
INFO - Model loaded successfully
```

### 2. 检查 GPU 使用情况

```bash
# 查看 GPU 利用率
nvidia-smi

# 监控实时 GPU 使用
watch -n 1 nvidia-smi
```

**正确配置（多 GPU 均衡使用）：**
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 525.00       Driver Version: 525.00      CUDA Version: 12.0     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA RTX A100      On   | 00:1E.0     Off |                    0 |
| 30%   45C    P0    150W / 250W |  20000MiB / 40960MiB |     95%      Default |
|   1  NVIDIA RTX A100      On   | 00:1F.0     Off |                    0 |
| 30%   42C    P0    140W / 250W |  18000MiB / 40960MiB |     92%      Default |
+-------------------------------+----------------------+----------------------+
```

**错误配置（DEVICE_MAP=cuda，只用 1 张卡）：**
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 525.00       Driver Version: 525.00      CUDA Version: 12.0     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA RTX A100      On   | 00:1E.0     Off |                    0 |
| 85%   89C    P0    240W / 250W |  39000MiB / 40960MiB |     99%      Default |  ← OOM!
|   1  NVIDIA RTX A100      On   | 00:1F.0     Off |                    0 |
|  5%   25C    P0      0W / 250W |      0MiB / 40960MiB |      0%      Default |  ← 闲置
+-------------------------------+----------------------+----------------------+
```

### 3. 测试 API 响应

```bash
curl -X POST http://localhost:8000/v1/images/edits \
  -F "prompt=test" \
  -F "images=@test.jpg"
```

如果配置正确，应该正常返回结果，不会出现 OOM 错误。

## 性能对比

### 配置 A：单 GPU（DEVICE_MAP=cuda）
- GPU 0：99% 使用，温度 89°C，即将 OOM
- GPU 1：0% 使用，闲置
- **总体效率：50%**（只用了 1 张）

### 配置 B：多 GPU（DEVICE_MAP=balanced）
- GPU 0：95% 使用，温度 45°C，稳定
- GPU 1：92% 使用，温度 42°C，稳定
- **总体效率：100%**（充分利用）

## 常见问题

### Q: 为什么还是 OOM？
**A:** 检查 DEVICE_MAP 是否正确设置为 `balanced`

```bash
# 查看环境变量
echo $DEVICE_MAP

# 应该输出：balanced
```

### Q: 能同时使用 3 张 GPU 吗？
**A:** 可以，只需设置 `DEVICE_MAP=balanced` 即可。系统会自动检测并利用所有可用的 GPU。

### Q: 能指定只用某些 GPU 吗？
**A:** 可以，通过 `CUDA_VISIBLE_DEVICES` 环境变量：

```bash
# 只使用 GPU 0 和 GPU 1
CUDA_VISIBLE_DEVICES=0,1 python main.py

# 只使用 GPU 2
CUDA_VISIBLE_DEVICES=2 python main.py
```

### Q: balanced 和 cuda 有性能差异吗？
**A:** 几乎没有。balanced 的性能等同或更优，因为：
- 充分利用所有 GPU
- 减少单卡压力
- 降低温度

### Q: 推荐的 DEVICE_MAP 设置是什么？
**A:** 
- 1 张 GPU：`DEVICE_MAP=cuda` 或 `balanced`（都可以）
- 2+ 张 GPU：**必须** `DEVICE_MAP=balanced`

## 更新日志

### v1.2.1 - 多 GPU 优化
- ✅ 默认值改为 `DEVICE_MAP=balanced`
- ✅ 添加详细的多 GPU 配置说明
- ✅ 改进文档和错误提示
- ✅ 创建本指南

## 相关资源

- [README.md](README.md) - 快速开始
- [PARAMETERS.md](PARAMETERS.md) - 完整参数参考
- [.env.example](.env.example) - 配置示例
- Hugging Face Accelerate：https://huggingface.co/docs/accelerate/

