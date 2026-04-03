from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from body_metric_module import analyze_body_from_image

router = APIRouter()

@router.post("/{user_id}/scan")
async def scan_body(
    user_id: str, 
    file: UploadFile = File(...)
):
    print(f"Received scan request for user: {user_id}")
    print(f"File: {file.filename}, type: {file.content_type}")

    if not file.content_type or \
       not file.content_type.startswith('image/'):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid file",
                "message": "Please upload an image file (JPG or PNG)"
            }
        )

    image_bytes = await file.read()
    print(f"Received {len(image_bytes)} bytes")

    if len(image_bytes) == 0:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Empty file",
                "message": "The uploaded file is empty."
            }
        )

    result = analyze_body_from_image(image_bytes)

    if "error" in result and "success" not in result:
        return JSONResponse(
            status_code=422,
            content=result
        )

    return JSONResponse(
        status_code=200,
        content=result
    )

@router.get("/{user_id}")
async def get_body_profile(user_id: str):
    return JSONResponse(content={"profile": None})
