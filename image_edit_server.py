import base64
import io
import time
import logging
import secrets # <-- ADDED: For secure credential comparison
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse
# --- FIX: Changed from HTTPBearer/HTTPAuthCredentials to HTTPBasic/HTTPBasicCredentials ---
from fastapi.security import HTTPBasic, HTTPBasicCredentials 
from diffusers import QwenImageEditPipeline
from PIL import Image
import torch
import os
from dotenv import load_dotenv
from torchvision.transforms import ToPILImage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from a .env file if present
load_dotenv()

model_dir = os.getenv("QWEN_MODEL_DIR", "/mnt/models")
api_key = os.getenv("API_KEY")  # Optional: if not set, authentication is disabled
require_auth = api_key is not None
model_loaded = False
# DEVICE_MAP: supports 'balanced' or 'cuda' (defaults to 'balanced' for better multi-GPU support)
# - 'cuda': places entire model on a single GPU (can cause OOM on large models with multiple GPUs)
# - 'balanced': distributes model layers across available GPUs (recommended for multi-GPU setups)
device_map = os.getenv("DEVICE_MAP", "balanced").strip().lower()
if device_map not in ("balanced", "cuda"):
    logger.warning(f"Unsupported DEVICE_MAP='{device_map}', falling back to 'balanced'")
    device_map = "balanced"

app = FastAPI(title="Qwen Image Edit API", version="1.0.0")

# Security
# --- FIX: Changed scheme to HTTPBasic ---
security = HTTPBasic(auto_error=False)  # auto_error=False to make authentication optional

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
        device_map=device_map,
    )
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
# --- FIX: Changed dependency type hint to HTTPBasicCredentials ---
async def verify_api_key(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify Basic Auth password matches API key (optional if API_KEY is not set)"""
    # If authentication is not required, skip verification
    if not require_auth:
        return None
    
    # If authentication is required but no credentials provided
    if credentials is None:
        logger.warning("Basic Auth credentials required but not provided")
        raise UnauthorizedError("Credentials are required")
    
    # We treat the API_KEY as the expected password for simplicity.
    # Use secrets.compare_digest for secure, timing-attack-resistant comparison.
    is_correct_key = secrets.compare_digest(
        credentials.password, 
        api_key
    )
    
    # Verify the API key matches
    if not is_correct_key:
        logger.warning(f"Unauthorized Basic Auth attempt by username: {credentials.username}")
        # Note: The unauthorized error will automatically prompt the client for credentials
        raise UnauthorizedError("Invalid username or password")
    
    logger.info(f"Successful Basic Auth attempt by username: {credentials.username}")
    return credentials.username

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
    images: List[UploadFile] = File(...),
    negative_prompt: str = Form(default=None),
    size: str = Form("1024x1024"),
    n: int = Form(1),
    num_inference_steps: int = Form(50),
    guidance_scale: float = Form(None),
    true_cfg_scale: float = Form(4.0),
    output_type: str = Form("pil"),
    max_sequence_length: int = Form(512),
    # --- FIX: Changed dependency type hint to HTTPBasicCredentials ---
    credentials: HTTPBasicCredentials = Depends(security), 
):
    """
    Edit image(s) using Qwen Image Edit model.
    
    Supports single or multiple input images. Pipeline will process them together
    for batch editing or generate variations for each image.
    
    Parameters:
    - prompt (str, required): The text prompt for image editing
    - images (List[file], required): One or more input image files
    - negative_prompt (str, optional): Text describing what should NOT appear
    - size (str): Image size in format "WIDTHxHEIGHT" (default: "1024x1024")
    - n (int): Number of images to generate per input (default: 1, max: 10)
    - num_inference_steps (int): Number of denoising steps (default: 50)
    - guidance_scale (float, optional): How much to follow the prompt
    - true_cfg_scale (float): Classifier-free guidance scale (default: 4.0)
    - output_type (str): Output format, "pil" or "pt" (default: "pil")
    - max_sequence_length (int): Maximum sequence length for tokenizer (default: 512)
    
    Authentication is optional (only required if API_KEY environment variable is set).
    Uses HTTP Basic Auth (Username: any, Password: API_KEY).
    
    Request example:
        curl -X POST http://localhost:8000/v1/images/edits \\
          -F "prompt=make the sky blue" \\
          -F "images=@photo1.jpg" \\
          -F "images=@photo2.jpg"
    """
    try:
        # Verify authentication (if required)
        # credentials will contain username and password if provided
        await verify_api_key(credentials)
        
        # Check model is ready
        if not model_loaded:
            raise ModelNotReadyError()
        
        # Validate inputs
        if not images or len(images) == 0:
            raise InvalidInputError("At least one image is required")
        
        if not prompt or len(prompt.strip()) == 0:
            raise InvalidInputError("Prompt cannot be empty")
        
        if n < 1 or n > 10:
            raise InvalidInputError("n must be between 1 and 10")
        
        if num_inference_steps < 1:
            raise InvalidInputError("num_inference_steps must be at least 1")
        
        if output_type not in ("pil", "pt"):
            raise InvalidInputError("output_type must be 'pil' or 'pt'")
        
        # Parse size parameter (format: "WIDTHxHEIGHT")
        try:
            size_parts = size.split("x")
            if len(size_parts) != 2:
                raise ValueError()
            width, height = int(size_parts[0]), int(size_parts[1])
            if width <= 0 or height <= 0:
                raise ValueError()
        except (ValueError, IndexError):
            raise InvalidInputError("Invalid size format. Use 'WIDTHxHEIGHT' (e.g., '1024x1024')")
        
        # Load and validate all images
        pil_images: List[Image.Image] = []
        for idx, image_file in enumerate(images):
            try:
                img = Image.open(io.BytesIO(await image_file.read())).convert("RGB")
                pil_images.append(img)
                logger.debug(f"Loaded image {idx+1}/{len(images)}: {image_file.filename}")
            except Exception as e:
                raise InvalidInputError(f"Invalid image format at index {idx}: {str(e)}")
        
        logger.info(
            f"Processing image edit request: "
            f"num_images={len(pil_images)}, prompt='{prompt[:50]}...', "
            f"size={size}, n={n}, num_inference_steps={num_inference_steps}"
        )
        
        results = []
        start_time = time.time()
        
        try:
            # Build pipeline call kwargs with all supported parameters
            # Pass multiple images as a list to the pipeline for batch processing
            pipe_kwargs = {
                "prompt": prompt,
                "image": pil_images if len(pil_images) > 1 else pil_images[0],  # Pass list if multiple, single image if one
                "height": height,
                "width": width,
                "num_inference_steps": num_inference_steps,
                "true_cfg_scale": true_cfg_scale,
                "output_type": output_type,
                "max_sequence_length": max_sequence_length,
                "num_images_per_prompt": n,  # Generate n variations per input image
            }
            
            # Add optional parameters if provided
            if negative_prompt:
                pipe_kwargs["negative_prompt"] = negative_prompt
            
            if guidance_scale is not None:
                pipe_kwargs["guidance_scale"] = guidance_scale
            
            # Single pipeline call with all images and parameters
            output = pipe(**pipe_kwargs)
            
            # Process all generated images
            # output.images is a list of generated images
            for idx, out_image in enumerate(output.images):
                try:
                    if output_type == "pil":
                        results.append({"b64_json": pil_to_b64(out_image)})
                    else:  # output_type == "pt"
                        # For tensor output, convert to PIL first for consistent API response
                        to_pil = ToPILImage()
                        if isinstance(out_image, Image.Image):
                            results.append({"b64_json": pil_to_b64(out_image)})
                        else:
                            # Handle tensor output
                            tensor = out_image
                            if tensor.dim() == 3 and tensor.shape[0] in (3, 4):  # (C, H, W)
                                out_img = to_pil(tensor)
                            else:
                                out_img = to_pil(tensor.permute(2, 0, 1) / 255.0)  # Assuming (H, W, C)
                            results.append({"b64_json": pil_to_b64(out_img)})
                    logger.debug(f"Processed generated image {idx+1}/{len(output.images)}")
                except Exception as e:
                    logger.error(f"Error processing image {idx+1}: {str(e)}")
                    raise
            
            elapsed_time = time.time() - start_time
            total_generated = len(output.images)
            logger.info(
                f"Image edit completed in {elapsed_time:.2f}s, "
                f"processed {len(pil_images)} image(s), generated {total_generated} result(s)"
            )
        except Exception as e:
            logger.error(f"Error in image editing pipeline: {str(e)}")
            raise APIError(f"Image generation failed: {str(e)}", "GENERATION_ERROR", 500)
        
        return JSONResponse(
            {
                "created": int(time.time()),
                "data": results,
                "usage": {
                    "processing_time_seconds": elapsed_time,
                    "input_images": len(pil_images),
                    "generated_images": total_generated,
                }
            }
        )
        
    except UnauthorizedError as e:
        logger.warning(f"Unauthorized request: {e.message}")
        # When raising UnauthorizedError, FastAPI will automatically add the WWW-Authenticate: Basic header
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
