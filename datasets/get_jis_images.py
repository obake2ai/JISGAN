from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
import os

from get_jis_characters import generate_jis_characters

def generate_jis_images(font_path, output_dir, skipped_file_path):
    font_size = 900
    font = ImageFont.truetype(font_path, font_size)
    image_size = (1024, 1024)
    jis_characters = generate_jis_characters()

    # Skipped characters will be appended to the file during the loop
    with open(skipped_file_path, 'a', encoding='utf-8') as skipped_file:
        for index, char in enumerate(jis_characters):
            image = Image.new("RGB", image_size, (255, 255, 255))
            draw = ImageDraw.Draw(image)

            try:
                # textbboxを使用して文字のバウンディングボックスを取得
                bbox = draw.textbbox((0, 0), char, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # バウンディングボックスを使用して中央に配置
                position = ((image_size[0] - text_width) // 2 - bbox[0],
                            (image_size[1] - text_height) // 2 - bbox[1])

                draw.text(position, char, fill=(0, 0, 0), font=font)

                output_image_path = os.path.join(output_dir, f"jis_character_{str(index + 1).zfill(8)}.png")
                image.save(output_image_path)
            except Exception as e:
                # 欠損文字の場合はスキップし、JISコード（Unicodeコードポイント）をメモする
                skipped_character = f"{char} (U+{ord(char):04X})"
                skipped_file.write(skipped_character + '\n')

def main(font_path, output_dir):
    skipped_file_path = './skipped_jis.txt'
    # Clear the previous skipped file
    if os.path.exists(skipped_file_path):
        os.remove(skipped_file_path)
    generate_jis_images(font_path, output_dir, skipped_file_path)

if __name__ == '__main__':
    font_path = "./fonts/NotoSansCJKjp-Regular.otf"
    output_dir = './output'
    os.makedirs(output_dir, exist_ok=True)
    main(font_path, output_dir)
