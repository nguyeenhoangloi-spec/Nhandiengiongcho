pip install -r requirements.txt

import zipfile
with zipfile.ZipFile('runs.zip', 'r') as zip_ref:
zip_ref.extractall()
with zipfile.ZipFile('stanford-dogs-yolo.zip', 'r') as zip_ref:
zip_ref.extractall()

conda activate faceenv
D:
cd

conda activate yolo

python scripts/stanford_dogs_to_yolo.py --images-root static/images --output-root stanford-dogs-yolo --val-ratio 0.2

set KMP_DUPLICATE_LIB_OK=TRUE

yolo detect train model=yolov8n.pt data=stanford-dogs-yolo/data.yaml epochs=50 imgsz=640 batch=16 project=runs/detect/breeds name=yolov8n_breeds

yolo detect train model=yolov8n.pt data=stanford-dogs-yolo/data.yaml epochs=10 imgsz=640 batch=2 project=runs/detect/breeds name=yolov8n_breeds_cpu

.\ngrok http 5000

from google.colab import files
files.download('runs/detect/breeds_from_scratch/weights/best.pt')
files.download('runs/detect/breeds_from_scratch/weights/last.pt')

# Hệ thống nhận diện giống chó mèo

Giải pháp Flask cho nhận diện chó/mèo và suy đoán giống từ ảnh. Pipeline gồm: phân loại loài (Dog/Cat), phân loại giống (breed) bằng đặc trưng HOG + SVM, và phần minh họa phân tích bộ phận (demo contour).

## Tính năng

- Nhận ảnh tải lên và hiển thị kết quả phân loại Dog/Cat.
- Suy đoán giống nếu đã huấn luyện mô hình SVM từ dataset.
- Trang kết quả hiển thị thống kê contour như một demo phân tích bộ phận.

## Cài đặt

```bash
pip install -r requirements.txt
```

Lưu ý trên Windows: nếu cài đặt gói nặng gặp lỗi, hãy cập nhật `pip` và `setuptools`.

```bash
python -m pip install --upgrade pip setuptools wheel
```

## Huấn luyện mô hình (tùy chọn, để có phân loại giống)

Chuẩn bị dataset theo cấu trúc thư mục:

```
dataset_root/
	Dog/
		husky/
			*.jpg
		corgi/
			*.jpg
	Cat/
		bengal/
			*.jpg
		siamese/
			*.jpg
```

Chạy lệnh huấn luyện (tạo mô hình trong thư mục `models/`):

```bash
python train.py path/to/dataset_root --models-dir models
```

Sau khi huấn luyện, ứng dụng sẽ tự động dùng các file:

- `models/species_svm.joblib`
- `models/breed_svm.joblib`
- `models/breed_labels.joblib`

## Chạy ứng dụng

```bash
python app.py
```

Truy cập: http://localhost:5000

## Sử dụng

- Tại trang chủ, chọn ảnh và bấm "Phân tích ảnh".
- Kết quả hiển thị ở trang "Kết quả dự đoán" gồm Loài, Giống (nếu có mô hình) và thống kê contour demo.
- Các trang đăng nhập/đăng ký là demo, chưa kết nối CSDL.

## Cấu trúc thư mục

```
├── app.py              # Ứng dụng Flask + routes upload/predict
├── predict.py          # ImagePredictor: HOG + SVM, fallback demo
├── train.py            # Huấn luyện mô hình từ dataset thư mục
├── utils.py            # Hỗ trợ đọc ảnh, resize, HOG
├── models/             # Lưu file mô hình (.joblib)
├── requirements.txt    # Thư viện cần thiết
├── static/
│   ├── css/style.css
│   ├── js/script.js
│   ├── images/
│   └── uploads/        # Ảnh người dùng tải lên
├── templates/
│   ├── home.html       # Trang chủ + form upload
│   ├── predict.html    # Trang kết quả
│   ├── dashboard.html
│   ├── login.html
│   └── register.html
└── README.md
```

## Lưu ý chuyên môn

- Pipeline HOG+SVM là baseline nhẹ. Để đạt độ chính xác cao, có thể thay bằng CNN (EfficientNet/ResNet) hoặc YOLOv8-cls và fine-tune trên Oxford-IIIT Pet/Stanford Dogs.
- Phân tích bộ phận (chân/lông/đuôi/thân) nên dùng segmentation (Mask R-CNN/U-Net). Trong phạm vi đồ án này, trang kết quả minh họa contour như demo trực quan.

## Tham khảo

- Oxford-IIIT Pet Dataset: https://www.robots.ox.ac.uk/~vgg/data/pets/
- Stanford Dogs Dataset: http://vision.stanford.edu/aditya86/ImageNetDogs/

## Huấn luyện YOLOv8 cho giống chó (Stanford Dogs)

1. Chuẩn bị dữ liệu Stanford Dogs (thư mục ảnh theo từng giống). Nếu có XML VOC, trỏ thêm `--annotations-root`.

```bash
python scripts/stanford_dogs_to_yolo.py --images-root D:/datasets/stanford-dogs/images \
	--output-root D:/datasets/stanford-dogs-yolo --val-ratio 0.2 \
	--annotations-root D:/datasets/stanford-dogs/annotations
```

Sau khi chạy, YOLO dataset nằm tại `D:/datasets/stanford-dogs-yolo` gồm `train/`, `val/`, và `data.yaml`.

2. Cài đặt thư viện và train YOLOv8n detect:

```bash
pip install -r requirements.txt
python scripts/train_yolov8_breed.py --data D:/datasets/stanford-dogs-yolo/data.yaml --model yolov8n.pt --epochs 100 --imgsz 640 --name breeds
```

Kết quả trọng số: `runs/detect/breeds/weights/best.pt`.

3. Tích hợp vào ứng dụng: đặt file trọng số vào một trong các vị trí sau để app tự nhận:

- `runs/detect/breeds/weights/best.pt` (mặc định của Ultralytics)
- `weights/yolov8_breed_best.pt`
- `models/yolov8_breed_best.pt`

Khi có trọng số, trang kết quả sẽ hiển thị giống (breed) theo mô hình YOLOv8 nếu có.
