from generate_jis_characters import generate_jis_characters
from PIL import Image, ImageDraw, ImageFont
import os

def generate_jis_images(font_path, output_dir):
    font_size = 300
    font = ImageFont.truetype(font_path, font_size)
    image_size = (1024, 1024)
    jis_characters = generate_jis_characters()

    for index, char in enumerate(jis_characters):
        image = Image.new("RGB", image_size, (255, 255, 255))
        draw = ImageDraw.Draw(image)
        text_width, text_height = draw.textsize(char, font=font)
        position = ((image_size[0] - text_width) // 2, (image_size[1] - text_height) // 2)
        draw.text(position, char, fill=(0, 0, 0), font=font)

        output_image_path = f"jis_character_{str(index + 1).zfill(8)}.png"
        image.save(output_image_path)

        # 確認用に1文字のみ生成
        if index == 0:
            break

def main(font_path, output_dir):
    generate_jis_images(font_path, output_dir)

if __name__ == '__main__':
    font_path = "ipag.ttf"
    output_dir = './output'
    os.makedirs(output_dir, exist_ok=True)
    main(font_path, output_dir)
