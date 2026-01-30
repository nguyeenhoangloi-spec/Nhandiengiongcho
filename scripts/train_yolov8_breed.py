"""
Train YOLOv8 (detect) to classify dog breeds using YOLO-format dataset.

Usage:
  python scripts/train_yolov8_breed.py --data D:/datasets/stanford-dogs-yolo/data.yaml --model yolov8n.pt --epochs 100 --imgsz 640 --name breeds

Result weights are saved under runs/detect/<name>/weights/best.pt
"""
from __future__ import annotations
import argparse
from ultralytics import YOLO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="Path to data.yaml")
    ap.add_argument("--model", default="yolov8n.pt", help="Base model, e.g., yolov8n.pt")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--name", default="breeds")
    args = ap.parse_args()

    model = YOLO(args.model)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, name=args.name)
    print("\nTraining finished. Check runs/detect/{} for weights.".format(args.name))


if __name__ == "__main__":
    main()
