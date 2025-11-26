import base64
import io
import time
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from diffusers import QwenImageEditPipeline
from PIL import Image
import torch
import os

model_dir = os.getenv("QWEN_MODEL_DIR", "/mnt/models")

app = FastAPI()

# ----------------------------
# Load Qwen Image Edit Model
# ----------------------------
pipe = QwenImageEditPipeline.from_pretrained(
    model_dir,
    torch_dtype=torch.float16,
    local_files_only=True,
).to("cuda")

# ----------------------------
# Utility: image → base64
# ----------------------------
def pil_to_b64(image: Image.Image):
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return b64

# ----------------------------
# OpenAI-Compatible /v1/images/edits
# ----------------------------
@app.post("/v1/images/edits")
async def image_edit(
    prompt: str = Form(...),
    image: UploadFile = None,
    mask: UploadFile = None,
    size: str = Form("1024x1024"),
    n: int = Form(1),
):
    init_image = Image.open(io.BytesIO(await image.read())).convert("RGB")

    mask_image = None
    if mask:
        mask_image = Image.open(io.BytesIO(await mask.read())).convert("RGB")

    results = []
    for _ in range(n):
        out_img = pipe(
            prompt=prompt,
            image=init_image,
            mask_image=mask_image,
        ).images[0]

        results.append({"b64_json": pil_to_b64(out_img)})

    return JSONResponse(
        {
            "created": int(time.time()),
            "data": results
        }
    )
