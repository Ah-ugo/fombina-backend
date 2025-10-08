import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)


async def upload_image(file_data: bytes, folder: str = "fombina-tower", public_id: str = None):
    """
    Upload image to Cloudinary

    Args:
        file_data: Image file bytes
        folder: Cloudinary folder name
        public_id: Optional custom public ID

    Returns:
        dict: Upload result with secure_url
    """
    try:
        upload_options = {
            "folder": folder,
            "resource_type": "image",
            "quality": "auto:good",
            "fetch_format": "auto",
        }

        if public_id:
            upload_options["public_id"] = public_id

        result = cloudinary.uploader.upload(file_data, **upload_options)
        return {
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "width": result["width"],
            "height": result["height"],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def delete_image(public_id: str):
    """
    Delete image from Cloudinary

    Args:
        public_id: Cloudinary public ID

    Returns:
        dict: Deletion result
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_image_url(public_id: str, transformation: dict = None):
    """
    Get optimized image URL with optional transformations

    Args:
        public_id: Cloudinary public ID
        transformation: Optional transformation parameters

    Returns:
        str: Image URL
    """
    if transformation:
        return cloudinary.CloudinaryImage(public_id).build_url(**transformation)
    return cloudinary.CloudinaryImage(public_id).build_url()
