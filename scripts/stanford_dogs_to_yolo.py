
from __future__ import annotations
import os
import shutil
import random
import argparse
from typing import List, Tuple, Optional

from PIL import Image

# Import an XML parser alias that works with Pylance typing
from typing import Any
ET_like: Any
try:
    import lxml.etree as _ET_like
    ET_like = _ET_like
except Exception:
    import xml.etree.ElementTree as _ET_like
    ET_like = _ET_like

import yaml
from tqdm import tqdm


def list_classes(images_root: str) -> List[str]:
    classes = []
    for name in sorted(os.listdir(images_root)):
        p = os.path.join(images_root, name)
        if os.path.isdir(p):
            classes.append(name)
    return classes


def parse_voc_bbox(xml_path: str) -> Optional[Tuple[int, int, int, int]]:
    """Parse first <object><bndbox> from VOC XML. Return (xmin, ymin, xmax, ymax) or None."""

    def safe_int(txt: Optional[str]) -> Optional[int]:
        if txt is None:
            return None
        try:
            return int(txt)
        except Exception:
            # Some VOCs store floats or malformed strings; try float->int
            try:
                return int(float(txt))
            except Exception:
                return None
    try:
        # Use unified alias regardless of backend
        root = ET_like.parse(xml_path).getroot()
        # Prefer first object
        for obj in root.findall("object"):
            bb = obj.find("bndbox")
            if bb is None:
                continue
            xmin = safe_int(bb.findtext("xmin"))
            ymin = safe_int(bb.findtext("ymin"))
            xmax = safe_int(bb.findtext("xmax"))
            ymax = safe_int(bb.findtext("ymax"))
            if None in (xmin, ymin, xmax, ymax):
                # Skip malformed bboxes
                continue
            # Narrow Optional[int] to int for type checker
            assert xmin is not None and ymin is not None and xmax is not None and ymax is not None
            return xmin, ymin, xmax, ymax
        return None
    except Exception:
        return None


def yolo_line(class_id: int, bbox: Tuple[int, int, int, int], w: int, h: int) -> str:
    xmin, ymin, xmax, ymax = bbox
    x_center = ((xmin + xmax) / 2.0) / w
    y_center = ((ymin + ymax) / 2.0) / h
    bw = (xmax - xmin) / w
    bh = (ymax - ymin) / h
    # Clip values into [0,1]
    x_center = min(max(x_center, 0.0), 1.0)
    y_center = min(max(y_center, 0.0), 1.0)
    bw = min(max(bw, 0.0), 1.0)
    bh = min(max(bh, 0.0), 1.0)
    return f"{class_id} {x_center:.6f} {y_center:.6f} {bw:.6f} {bh:.6f}\n"


def split_train_val(items: List[Tuple[str, str, int]], val_ratio: float) -> Tuple[List, List]:
    random.shuffle(items)
    n_val = int(len(items) * val_ratio)
    val_items = items[:n_val]
    train_items = items[n_val:]
    return train_items, val_items


def convert(images_root: str, output_root: str, annotations_root: Optional[str], val_ratio: float = 0.2) -> None:
    # Early validation for clearer errors
    if not os.path.isdir(images_root):
        raise FileNotFoundError(f"images_root not found: {images_root}")
    if annotations_root and not os.path.isdir(annotations_root):
        print(f"[warn] annotations_root not found: {annotations_root}. Falling back to full-image bbox.")
        annotations_root = None

    classes = list_classes(images_root)
    if not classes:
        raise RuntimeError(f"No class folders found in {images_root}")

    class_to_id = {c: i for i, c in enumerate(classes)}

    # Collect items: (image_path, class_name, class_id)
    items = []
    for c in classes:
        cdir = os.path.join(images_root, c)
        for fn in os.listdir(cdir):
            if not fn.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            items.append((os.path.join(cdir, fn), c, class_to_id[c]))

    train_items, val_items = split_train_val(items, val_ratio)

    # Prepare output dirs
    img_train = os.path.join(output_root, "train", "images")
    img_val = os.path.join(output_root, "val", "images")
    lab_train = os.path.join(output_root, "train", "labels")
    lab_val = os.path.join(output_root, "val", "labels")
    for p in [img_train, img_val, lab_train, lab_val]:
        os.makedirs(p, exist_ok=True)

    # Helper to write one item
    def process_item(img_path: str, class_id: int, subset: str):
        # Read size
        with Image.open(img_path) as im:
            w, h = im.size
        # Try to find VOC xml alongside (annotations_root/class/filename.xml or same dir .xml)
        base = os.path.splitext(os.path.basename(img_path))[0]
        bbox = None
        xml_candidates = []
        if annotations_root:
            xml_candidates.append(os.path.join(annotations_root, classes[class_id], base + ".xml"))
            xml_candidates.append(os.path.join(annotations_root, base + ".xml"))
        xml_candidates.append(os.path.join(os.path.dirname(img_path), base + ".xml"))
        for xp in xml_candidates:
            if os.path.exists(xp):
                bbox = parse_voc_bbox(xp)
                if bbox:
                    break
        # Fallback: full-image bbox
        if bbox is None:
            bbox = (1, 1, w - 1, h - 1)
        # Write label
        yline = yolo_line(class_id, bbox, w, h)
        if subset == "train":
            dst_img_dir, dst_lab_dir = img_train, lab_train
        else:
            dst_img_dir, dst_lab_dir = img_val, lab_val
        # Copy image
        dst_img = os.path.join(dst_img_dir, os.path.basename(img_path))
        shutil.copy2(img_path, dst_img)
        # Write label
        dst_lab = os.path.join(dst_lab_dir, os.path.splitext(os.path.basename(img_path))[0] + ".txt")
        with open(dst_lab, "w", encoding="utf-8") as f:
            f.write(yline)

    # Convert with progress bars
    for img_path, c, cid in tqdm(train_items, desc="Train convert"):
        process_item(img_path, cid, "train")
    for img_path, c, cid in tqdm(val_items, desc="Val convert"):
        process_item(img_path, cid, "val")

    # Write data.yaml
    data = {
        "train": img_train.replace("\\", "/"),
        "val": img_val.replace("\\", "/"),
        "nc": len(classes),
        "names": classes,
    }
    with open(os.path.join(output_root, "data.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True)

    print("\nDone. YOLO dataset written to:", output_root)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images-root", required=True, help="Root folder of class-based images")
    ap.add_argument("--output-root", required=True, help="Output folder for YOLO dataset")
    ap.add_argument("--annotations-root", default=None, help="Optional VOC XML annotations root")
    ap.add_argument("--val-ratio", type=float, default=0.2, help="Validation split ratio")
    args = ap.parse_args()
    convert(args.images_root, args.output_root, args.annotations_root, args.val_ratio)


if __name__ == "__main__":
    main()
