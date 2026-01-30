# predict.py
# Xử lý nhận diện ảnh: phân loại chó/mèo và giống

import os
from typing import Dict, Any

import numpy as np
import cv2
from sklearn.base import BaseEstimator
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from joblib import load

from utils import load_image_bgr, extract_hog_features


class ImagePredictor:
	"""Image predictor cho pipeline cơ bản.

	- species_model: phân loại chó/mèo (Dog/Cat)
	- breed_model: phân loại giống dựa trên đặc trưng HOG
	"""

	def __init__(self, models_dir: str = "models"):
		self.models_dir = models_dir
		self.species_model: Pipeline | None = None
		self.breed_model: Pipeline | None = None
		self.breed_labels: list[str] | None = None

		self._load_models()

	def _load_models(self) -> None:
		species_path = os.path.join(self.models_dir, "species_svm.joblib")
		breed_path = os.path.join(self.models_dir, "breed_svm.joblib")
		labels_path = os.path.join(self.models_dir, "breed_labels.joblib")

		if os.path.exists(species_path):
			try:
				self.species_model = load(species_path)
			except Exception:
				self.species_model = None

		if os.path.exists(breed_path):
			try:
				self.breed_model = load(breed_path)
			except Exception:
				self.breed_model = None

		if os.path.exists(labels_path):
			try:
				self.breed_labels = load(labels_path)
			except Exception:
				self.breed_labels = None

	def predict(self, image_path: str) -> Dict[str, Any]:
		"""Dự đoán pipeline.

		Trả về dict gồm:
		- image_path: đường dẫn ảnh
		- species: 'Dog' | 'Cat' | 'Unknown'
		- breed: tên giống hoặc 'Unknown'
		- parts_info: thông tin thô về các phần (demo)
		- model_ready: bool cho biết đã có model huấn luyện chưa
		- message: hướng dẫn nếu thiếu model
		"""

		img = load_image_bgr(image_path)
		if img is None:
			return {
				"image_path": image_path,
				"species": "Unknown",
				"breed": "Unknown",
				"parts_info": {},
				"model_ready": False,
				"message": "Không thể đọc ảnh. Vui lòng thử lại với ảnh khác.",
			}

		feat = extract_hog_features(img)
		model_ready = self.species_model is not None and self.breed_model is not None and self.breed_labels is not None

		if not model_ready:
			# Fallback demo: rule-of-thumb bằng tỉ lệ cạnh và màu sắc (rất kém chính xác)
			h, w = img.shape[:2]
			aspect = w / max(h, 1)
			mean_color = img.mean(axis=(0, 1))
			species_guess = "Dog" if aspect > 0.8 and mean_color[2] > mean_color[1] else "Cat"
			return {
				"image_path": image_path,
				"species": species_guess,
				"breed": "Unknown",
				"parts_info": self._parts_demo(img),
				"model_ready": False,
				"message": (
					"Chưa có mô hình huấn luyện. Hãy chạy train.py với dữ liệu Oxford-IIIT Pet để tạo các file trong models/."
				),
			}

		# Đảm bảo model không None trước khi predict
		if self.species_model is not None and self.breed_model is not None and self.breed_labels is not None:
			species_pred = self.species_model.predict([feat])[0]
			breed_idx = int(self.breed_model.predict([feat])[0])
			breed_name = (
				self.breed_labels[breed_idx] if 0 <= breed_idx < len(self.breed_labels) else "Unknown"
			)
		else:
			species_pred = "Unknown"
			breed_name = "Unknown"

		return {
			"image_path": image_path,
			"species": species_pred,
			"breed": breed_name,
			"parts_info": self._parts_demo(img),
			"model_ready": model_ready,
			"message": "Dự đoán thành công." if model_ready else "Chưa có mô hình huấn luyện.",
		}

	def _parts_demo(self, img: np.ndarray) -> Dict[str, Any]:
		"""Demo phân tích các phần bằng Canny + contour để minh họa.
		Đây không phải segmentation chính xác, chỉ mang tính trình diễn.
		"""
		gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		edges = cv2.Canny(gray, 50, 150)
		contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
		h, w = img.shape[:2]
		total_area = h * w
		areas = [cv2.contourArea(c) for c in contours]
		large = sum(1 for a in areas if a > 0.01 * total_area)
		medium = sum(1 for a in areas if 0.005 * total_area < a <= 0.01 * total_area)
		small = sum(1 for a in areas if a <= 0.005 * total_area)
		return {
			"contours_total": len(contours),
			"large_parts": int(large),
			"medium_parts": int(medium),
			"small_parts": int(small),
		}
