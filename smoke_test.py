"""
smoke_test.py — Quick YOLOv8 Dog/Cat detection check

Usage:
  python smoke_test.py --image path/to/image.jpg [--model yolov8n.pt]

It prints all detected labels and confidence, and the final species guess
restricted to Dog/Cat if present.
"""
from __future__ import annotations
import argparse
from ultralytics import YOLO


def detect_species(image_path: str, model_path: str = "yolov8n.pt") -> str:
    model = YOLO(model_path)
    results = model(image_path)
    r = results[0]
    names = getattr(r, "names", {}) or {}

    species = "Unknown"
    if hasattr(r, "boxes") and r.boxes is not None and getattr(r.boxes, "cls", None) is not None:
        cls_list = r.boxes.cls.tolist()
        if not isinstance(cls_list, list):
            cls_list = [cls_list]
        confs = r.boxes.conf.tolist() if getattr(r.boxes, "conf", None) is not None else [None] * len(cls_list)
        pairs = []
        for ci, cf in zip(cls_list, confs):
            try:
                label = names[int(ci)]
            except Exception:
                label = str(ci)
            pairs.append((label, float(cf) if cf is not None else None))
        print("Detections:")
        for lab, cf in pairs:
            print(f"  - {lab}: conf={cf if cf is not None else 'N/A'}")
        best = None
        best_conf = -1.0
        for lab, cf in pairs:
            if lab in ("dog", "cat"):
                c = cf if cf is not None else 0.0
                if c > best_conf:
                    best = lab
                    best_conf = c
        if best is not None:
            species = "Dog" if best == "dog" else "Cat"
    return species


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="Path to test image")
    ap.add_argument("--model", default="yolov8n.pt", help="YOLOv8 detection model path")
    args = ap.parse_args()

    sp = detect_species(args.image, args.model)
    print(f"\nFinal species guess: {sp}")


if __name__ == "__main__":
    main()
