from PIL import Image, ImageDraw, ImageFont
import os

cover_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'covers')
os.makedirs(cover_dir, exist_ok=True)
target_path = os.path.join(cover_dir, 'default_cover.png')

# Create an image with a flat background color (#6366f1)
img = Image.new('RGB', (300, 450), color='#6366f1')

# Draw text
d = ImageDraw.Draw(img)

# Fallback basic text without custom font
# Try drawing multiple lines to center "Book Cover"
text = "Book Cover"
# Basic sizing heuristics
text_width = len(text) * 6
text_height = 10
x = (300 - text_width) // 2
y = (450 - text_height) // 2

d.text((x, y), text, fill=(255, 255, 255))
d.text((x-5, y+20), "(Placeholder)", fill=(255, 255, 255))

img.save(target_path)
print(f"Generated default cover at {target_path}")
