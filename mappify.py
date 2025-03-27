import os
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

Image.MAX_IMAGE_PIXELS = None

input_path = r"C:\Users\green\Downloads\final_stitched_image_cropped.png"
output_path = r"C:\Users\green\OneDrive\Documents\Code shit\cyberpunk\src\lib\levels"

print("Loading image into memory...")
img = Image.open(input_path)
img.load()
print("Image loaded :D")

width, height = img.size
x_resolution = 1600
num_levels = 6
y_resolution = (x_resolution * height // width) // 2 * 2


def process_tile(i, j, resized):
    left_index = j % (2**i)
    top_index = j // (2**i)
    left_px = left_index * x_resolution
    top_px = top_index * y_resolution
    rect = (left_px, top_px, left_px + x_resolution, top_px + y_resolution)
    print(
        f"image {i},{j}, left: {left_px}, top: {top_px}, right: {left_px + x_resolution}, bottom: {top_px + y_resolution}"
    )
    cropped = resized.crop(rect)
    file_output_path = os.path.join(output_path, str(i), f"{j}.webp")
    cropped.save(file_output_path, format="WebP", quality=70)


for i in range(num_levels):
    level_dir = os.path.join(output_path, str(i))
    os.makedirs(level_dir, exist_ok=True)
    scale = 2**i
    resized = img.resize((x_resolution * scale, y_resolution * scale))
    num_tiles = 4**i
    with ThreadPoolExecutor() as executor:
        for j in range(num_tiles):
            executor.submit(process_tile, i, j, resized)
