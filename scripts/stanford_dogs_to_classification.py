import os
import shutil
from glob import glob

# Đường dẫn gốc ảnh Stanford Dogs

# Đường dẫn gốc ảnh Stanford Dogs
images_root = r'D:/datasets/stanford-dogs/images'
# Đường dẫn output cho dữ liệu classification (ngay trong thư mục đề tài)
output_root = r'd:/KhoaLuanTotNghiep/stanford-dogs-classification'

os.makedirs(output_root, exist_ok=True)

for breed_folder in os.listdir(images_root):
    breed_path = os.path.join(images_root, breed_folder)
    if os.path.isdir(breed_path):
        out_breed = os.path.join(output_root, breed_folder)
        os.makedirs(out_breed, exist_ok=True)
        for img_file in glob(os.path.join(breed_path, '*.jpg')):
            shutil.copy(img_file, out_breed)

print('Đã chuyển dữ liệu về dạng classification theo folder class.')
