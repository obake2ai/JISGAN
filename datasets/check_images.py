import os
import shutil
from PIL import Image
import hashlib

def calculate_image_hash(image_path):
    """Calculate the hash of the image content for comparison."""
    with Image.open(image_path) as img:
        img = img.convert('RGB')
        hash_value = hashlib.md5(img.tobytes()).hexdigest()
    return hash_value

def move_matching_images(source_folder, target_image_path, destination_folder):
    """Explore the source folder and move all images that match the target image."""
    # Calculate the hash of the target image
    target_hash = calculate_image_hash(target_image_path)

    # Create the destination folder if it doesn't exist
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
        print(f"Created directory: {destination_folder}")

    # Explore the source folder and compare images
    for root, _, files in os.walk(source_folder):
        for file in files:
            if file.lower().endswith('.png'):
                file_path = os.path.join(root, file)
                if calculate_image_hash(file_path) == target_hash:
                    # Move the matching file to the destination folder
                    shutil.move(file_path, os.path.join(destination_folder, file))
                    print(f"Moved: {file_path} to {destination_folder}")

if __name__ == '__main__':
    source_folder = './output'  # 画像がたくさんあるフォルダのパス
    target_image_path = './trashbox/jis_character_miss.png'  # 対象画像のパス
    destination_folder = './trashbox'  # 移動先フォルダのパス

    move_matching_images(source_folder, target_image_path, destination_folder)
