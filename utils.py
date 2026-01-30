# utils.py
# Các hàm tiện ích: xử lý ảnh, đặc trưng, v.v.

from typing import Tuple

import numpy as np
import cv2
from skimage.feature import hog


def load_image_bgr(path: str) -> np.ndarray | None:
	try:
		img = cv2.imread(path)
		return img
	except Exception:
		return None


def resize_keep_ratio(img: np.ndarray, target_size: Tuple[int, int] = (256, 256)) -> np.ndarray:
	h, w = img.shape[:2]
	th, tw = target_size
	scale = min(tw / w, th / h)
	nh, nw = int(h * scale), int(w * scale)
	resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
	canvas = np.zeros((th, tw, 3), dtype=resized.dtype)
	y0 = (th - nh) // 2
	x0 = (tw - nw) // 2
	canvas[y0 : y0 + nh, x0 : x0 + nw] = resized
	return canvas


def extract_hog_features(img: np.ndarray) -> np.ndarray:
	"""Trích xuất đặc trưng HOG từ ảnh BGR."""
	img256 = resize_keep_ratio(img, (256, 256))
	gray = cv2.cvtColor(img256, cv2.COLOR_BGR2GRAY)
	features = hog(
		gray,
		orientations=9,
		pixels_per_cell=(16, 16),
		cells_per_block=(2, 2),
		block_norm="L2-Hys",
		transform_sqrt=True,
		feature_vector=True,
	)
	return features.astype(np.float32)
