import base64
import io
import time
import logging
from datetime import datetime
from fastapi import FastAPI, UploadFile, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from diffusers import QwenImageEditPipeline
from PIL import Image
import torch
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

model_dir = os.getenv("QWEN_MODEL_DIR", "/mnt/models")
api_key = os.getenv("API_KEY")  # Optional: if not set, authentication is disabled
require_auth = api_key is not None
model_loaded = False

app = FastAPI(title="Qwen Image Edit API", version="1.0.0")

# Security
security = HTTPBearer(auto_error=False)  # auto_error=False to make authentication optional

# ----------------------------
# Custom Exceptions
# ----------------------------
class APIError(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code

class ModelNotReadyError(APIError):
    def __init__(self, message: str = "Model is not ready yet"):
        super().__init__(message, "MODEL_NOT_READY", 503)

class InvalidInputError(APIError):
    def __init__(self, message: str):
        super().__init__(message, "INVALID_INPUT", 400)

class UnauthorizedError(APIError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, "UNAUTHORIZED", 401)

# ----------------------------
# Load Qwen Image Edit Model
# ----------------------------
try:
    logger.info(f"Loading model from {model_dir}...")
    pipe = QwenImageEditPipeline.from_pretrained(
        model_dir,
        torch_dtype=torch.float16,
        local_files_only=True,
    ).to("cuda")
    model_loaded = True
    logger.info("Model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    model_loaded = False

# ----------------------------
# Utility: image → base64
# ----------------------------
def pil_to_b64(image: Image.Image):
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return b64

# ----------------------------
# Auth: Verify API Key
# ----------------------------
async def verify_api_key(credentials: HTTPAuthCredentials = Depends(security)):
    """Verify Bearer token matches API key (optional if API_KEY is not set)"""
    # If authentication is not required, skip verification
    if not require_auth:
        return None
    
    # If authentication is required but no credentials provided
    if credentials is None:
        logger.warning("API key required but not provided")
        raise UnauthorizedError("API key is required")
    
    # Verify the API key matches
    if credentials.credentials != api_key:
        logger.warning(f"Unauthorized API key attempt: {credentials.credentials[:10]}...")
        raise UnauthorizedError("Invalid API key")
    
    return credentials.credentials

# ----------------------------
# Health Check Endpoints
# ----------------------------
@app.get("/health")
async def health_check():
    """Basic health check - service is running"""
    logger.info("Health check requested")
    return JSONResponse(
        {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    )

@app.get("/ready")
async def readiness_check():
    """Readiness check - service is ready to accept requests"""
    if not model_loaded:
        logger.error("Readiness check failed: model not loaded")
        raise ModelNotReadyError()
    
    logger.info("Readiness check passed")
    return JSONResponse(
        {
            "status": "ready",
            "model_loaded": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

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
    credentials: HTTPAuthCredentials = Depends(security),
):
    """
    Edit an image using Qwen Image Edit model.
    
    Authentication is optional (only required if API_KEY environment variable is set).
    """
    try:
        # Verify authentication (if required)
        await verify_api_key(credentials)
        
        # Check model is ready
        if not model_loaded:
            raise ModelNotReadyError()
        
        # Validate inputs
        if not image:
            raise InvalidInputError("Image is required")
        
        if not prompt or len(prompt.strip()) == 0:
            raise InvalidInputError("Prompt cannot be empty")
        
        if n < 1 or n > 10:
            raise InvalidInputError("n must be between 1 and 10")
        
        # Validate image
        try:
            init_image = Image.open(io.BytesIO(await image.read())).convert("RGB")
        except Exception as e:
            raise InvalidInputError(f"Invalid image format: {str(e)}")
        
        # Validate mask if provided
        mask_image = None
        if mask:
            try:
                mask_image = Image.open(io.BytesIO(await mask.read())).convert("RGB")
            except Exception as e:
                raise InvalidInputError(f"Invalid mask format: {str(e)}")
        
        logger.info(f"Processing image edit request: prompt='{prompt[:50]}...', n={n}")
        
        results = []
        start_time = time.time()
        
        for i in range(n):
            try:
                out_img = pipe(
                    prompt=prompt,
                    image=init_image,
                    mask_image=mask_image,
                ).images[0]
                
                results.append({"b64_json": pil_to_b64(out_img)})
                logger.debug(f"Generated image {i+1}/{n}")
            except Exception as e:
                logger.error(f"Error generating image {i+1}: {str(e)}")
                raise APIError(f"Image generation failed: {str(e)}", "GENERATION_ERROR", 500)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Image edit completed in {elapsed_time:.2f}s, generated {n} image(s)")
        
        return JSONResponse(
            {
                "created": int(time.time()),
                "data": results,
                "usage": {
                    "processing_time_seconds": elapsed_time
                }
            }
        )
        
    except UnauthorizedError as e:
        logger.warning(f"Unauthorized request: {e.message}")
        raise HTTPException(status_code=e.status_code, detail={"error": e.code, "message": e.message})
    except ModelNotReadyError as e:
        logger.error(f"Model not ready: {e.message}")
        raise HTTPException(status_code=e.status_code, detail={"error": e.code, "message": e.message})
    except InvalidInputError as e:
        logger.warning(f"Invalid input: {e.message}")
        raise HTTPException(status_code=e.status_code, detail={"error": e.code, "message": e.message})
    except APIError as e:
        logger.error(f"API error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail={"error": e.code, "message": e.message})
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        )
