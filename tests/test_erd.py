import os
from PIL import Image

def test_erd_files_exist_and_valid():
    """Verify ERD-DicoEvent-versi-1.png and .jpg exist at root and are valid images."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    png_path = os.path.join(root_dir, 'ERD-DicoEvent-versi-1.png')
    jpg_path = os.path.join(root_dir, 'ERD-DicoEvent-versi-1.jpg')

    assert os.path.exists(png_path), f"Missing {png_path}"
    assert os.path.exists(jpg_path), f"Missing {jpg_path}"

    assert os.path.getsize(png_path) > 10000, "PNG file is suspiciously small"
    assert os.path.getsize(jpg_path) > 10000, "JPG file is suspiciously small"

    # Verify Pillow can open and verify both images
    with Image.open(png_path) as img_png:
        assert img_png.size[0] >= 1920
        assert img_png.size[1] >= 1080
        assert img_png.format == 'PNG'

    with Image.open(jpg_path) as img_jpg:
        assert img_jpg.size[0] >= 1920
        assert img_jpg.size[1] >= 1080
        assert img_jpg.format == 'JPEG'
