import os
from PIL import Image, ImageDraw, ImageFont

def convert_txt_to_image(input_txt, output_img, font_size=13, line_spacing=1.3):
    # Prevent PIL limits from tripping on massive vertical dimensions
    Image.MAX_IMAGE_PIXELS = None

    if not os.path.exists(input_txt):
        print(f"Error: Source file '{input_txt}' not found.")
        return

    with open(input_txt, 'r', encoding='utf-8') as f:
        lines = [line.rstrip('\r\n') for line in f.readlines()]

    # Load standard system monospaced font (Fallback chain)
    font = None
    font_names = ["consolas.ttf", "cour.ttf", "Courier", "DejaVuSansMono.ttf"]
    for f_name in font_names:
        try:
            font = ImageFont.truetype(f_name, font_size)
            break
        except IOError:
            continue
            
    if not font:
        font = ImageFont.load_default()
        print("Warning: Standard fonts not found. Falling back to default canvas font.")

    # Calculate exact canvas dimensions
    if hasattr(font, 'getbbox'):
        max_w = max(font.getbbox(line)[2] for line in lines) if lines else 100
        char_h = font.getbbox("M")[3]
    else:
        max_w = max(font.getsize(line)[0] for line in lines) if lines else 100
        char_h = font.getsize("M")[1]

    line_height = int(char_h * line_spacing)
    padding = 24
    
    img_width = max_w + (padding * 2)
    img_height = (len(lines) * line_height) + (padding * 2)

    # Render initially in Grayscale ('L') to support drawing passes
    img = Image.new('L', (img_width, img_height), color=255)
    draw = ImageDraw.Draw(img)

    # Render source strings
    y = padding
    for line in lines:
        draw.text((padding, y), line, fill=0, font=font)
        y += line_height

    # CRUCIAL: Convert to 1-bit monochrome ('1') for aggressive lossless compression
    img = img.convert('1')

    # Save format execution (Supports PNG, TIF, etc.)
    img.save("output.tif", compression="tiff_lzw")
    
    file_size_mb = os.path.getsize(output_img) / (1024 * 1024)
    print(f"Execution successful.")
    print(f"Output Path: {output_img}")
    print(f"Dimensions:  {img_width}x{img_height} px")
    print(f"File Size:   {file_size_mb:.2f} MB")

if __name__ == "__main__":
    # Configure your paths here
    convert_txt_to_image("your_code.txt", "codex_ready_output.png")