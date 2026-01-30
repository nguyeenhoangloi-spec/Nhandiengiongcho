# train.py
# Huấn luyện mô hình SVM cho phân loại chó/mèo và giống

import os
import argparse
from typing import List, Tuple

import numpy as np
import cv2
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.metrics import classification_report
from joblib import dump

from utils import load_image_bgr, extract_hog_features


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png"}


def is_image_file(name: str) -> bool:
    ext = os.path.splitext(name)[1].lower()
    return ext in SUPPORTED_EXTS


def load_dataset(root: str) -> Tuple[np.ndarray, List[str], List[str]]:
    """
    Kỳ vọng cấu trúc thư mục:
    root/
      Dog/
        breed1/
          *.jpg
        breed2/
          *.jpg
      Cat/
        breed3/
          *.jpg
        ...
    Trả về: features, species_labels, breed_labels
    """
    feats: List[np.ndarray] = []
    species_labels: List[str] = []
    breed_labels: List[str] = []

    for species in ("Dog", "Cat"):
        species_dir = os.path.join(root, species)
        if not os.path.isdir(species_dir):
            print(f"[WARN] Không tìm thấy thư mục: {species_dir}")
            continue
        for breed in os.listdir(species_dir):
            breed_dir = os.path.join(species_dir, breed)
            if not os.path.isdir(breed_dir):
                continue
            for fname in os.listdir(breed_dir):
                if not is_image_file(fname):
                    continue
                fpath = os.path.join(breed_dir, fname)
                img = load_image_bgr(fpath)
                if img is None:
                    continue
                feat = extract_hog_features(img)
                feats.append(feat)
                species_labels.append(species)
                breed_labels.append(breed)

    if not feats:
        raise RuntimeError("Không có dữ liệu ảnh hợp lệ. Hãy kiểm tra cấu trúc thư mục và định dạng ảnh.")

    return np.array(feats), species_labels, breed_labels


def main():
    parser = argparse.ArgumentParser(description="Train SVM models for species and breed classification")
    parser.add_argument("dataset", help="Đường dẫn tới thư mục dataset")
    parser.add_argument("--models-dir", default="models", help="Thư mục lưu mô hình")
    args = parser.parse_args()

    os.makedirs(args.models_dir, exist_ok=True)

    print("[INFO] Đang tải dữ liệu...")
    X, y_species, y_breed = load_dataset(args.dataset)

    # Map breed labels to indices for classifier
    unique_breeds = sorted(set(y_breed))
    breed_to_idx = {b: i for i, b in enumerate(unique_breeds)}
    y_breed_idx = np.array([breed_to_idx[b] for b in y_breed])

    # Species model
    print("[INFO] Huấn luyện mô hình species (Dog/Cat)...")
    X_train, X_val, ys_train, ys_val = train_test_split(X, y_species, test_size=0.2, random_state=42, stratify=y_species)
    species_clf = Pipeline([
        ("scaler", StandardScaler()),
        ("svc", SVC(kernel="rbf", C=10, gamma="scale")),
    ])
    species_clf.fit(X_train, ys_train)
    ys_pred = species_clf.predict(X_val)
    print("[REPORT] Species classification:")
    print(classification_report(ys_val, ys_pred))

    # Breed model
    print("[INFO] Huấn luyện mô hình breed...")
    X_train_b, X_val_b, yb_train, yb_val = train_test_split(X, y_breed_idx, test_size=0.2, random_state=42, stratify=y_breed_idx)
    breed_clf = Pipeline([
        ("scaler", StandardScaler()),
        ("svc", SVC(kernel="rbf", C=10, gamma="scale")),
    ])
    breed_clf.fit(X_train_b, yb_train)
    yb_pred = breed_clf.predict(X_val_b)
    print("[REPORT] Breed classification:")
    print(classification_report(yb_val, yb_pred))

    # Save models
    species_path = os.path.join(args.models_dir, "species_svm.joblib")
    breed_path = os.path.join(args.models_dir, "breed_svm.joblib")
    labels_path = os.path.join(args.models_dir, "breed_labels.joblib")

    dump(species_clf, species_path)
    dump(breed_clf, breed_path)
    dump(unique_breeds, labels_path)

    print(f"[DONE] Đã lưu mô hình tại: {args.models_dir}")


if __name__ == "__main__":
    main()
