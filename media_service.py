import os
import subprocess
import vision
import database_ops
import pillow_heif
from PIL import Image
from sqlalchemy.orm import Session

pillow_heif.register_heif_opener()

def _convert_heic(heic_path: str, base_name: str, upload_folder: str) -> str:
    """Convert HEIC to JPG (still) or MP4 (video). Returns the converted filename."""
    try:
        heif_file = pillow_heif.open_heif(heic_path)
        is_video = len(heif_file) > 1
    except Exception:
        is_video = True  # pillow can't open it as a still — treat as video

    if is_video:
        output_filename = base_name + ".mp4"
        output_path = os.path.join(upload_folder, output_filename)
        subprocess.run(
            ["ffmpeg", "-y", "-i", heic_path, "-c:v", "libx264",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", output_path],
            check=True, capture_output=True
        )
    else:
        output_filename = base_name + ".jpg"
        output_path = os.path.join(upload_folder, output_filename)
        img = Image.open(heic_path)
        img.save(output_path, "JPEG", quality=95)

    return output_filename


def _compress_video(video_path: str, base_name: str, upload_folder: str) -> str:
    """Compress a raw MOV/MP4 into a smaller preview MP4. Returns the preview filename."""
    output_filename = base_name + "_preview.mp4"
    output_path = os.path.join(upload_folder, output_filename)
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-c:v", "libx264", "-crf", "32",
         "-preset", "veryfast", "-vf", "scale='min(1280,iw)':-2",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", output_path],
        check=True, capture_output=True
    )
    return output_filename


def handle_upload_process(
    db: Session,
    file,
    category_name: str,
    asset_title: str,
    copyright_option_id: int = None,
    use_purpose_option_id: int = None,
):
    """Handles saving, AI analysis, and DB registration."""
    upload_folder = "static/uploads"

    with open(os.path.join(upload_folder, file.filename), "wb+") as f:
        f.write(file.file.read())

    original_file_path = None
    display_filename = file.filename

    if file.filename.lower().endswith(".heic"):
        heic_path = os.path.join(upload_folder, file.filename)
        base_name = os.path.splitext(file.filename)[0]
        try:
            converted_filename = _convert_heic(heic_path, base_name, upload_folder)
            original_file_path = file.filename
            display_filename = converted_filename
        except Exception as e:
            print(f"DEBUG: HEIC Conversion Error - {e}")

    elif file.filename.lower().endswith((".mov", ".mp4")):
        video_path = os.path.join(upload_folder, file.filename)
        base_name = os.path.splitext(file.filename)[0]
        try:
            preview_filename = _compress_video(video_path, base_name, upload_folder)
            original_file_path = file.filename
            display_filename = preview_filename
        except Exception as e:
            print(f"DEBUG: Video Compression Error - {e}")

    ai_path = os.path.join(upload_folder, display_filename)
    try:
        ai_description = vision.analyze_media(ai_path)
    except Exception as e:
        print(f"DEBUG: AI Routing Error - {e}")
        ai_description = "AI-Analysis-Unavailable"

    cat_id = database_ops.get_or_create_category(db, category_name)
    database_ops.create_asset(
        db=db,
        name=asset_title,
        file_path=display_filename,
        ai_tags=ai_description,
        category_id=cat_id,
        original_file_path=original_file_path,
        copyright_option_id=copyright_option_id,
        use_purpose_option_id=use_purpose_option_id,
    )
    return True
