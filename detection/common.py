"""Bits shared by train, evaluate, export and predict."""
import csv
import json
from pathlib import Path

import torch
from PIL import Image
from torchvision import models, transforms

REPO = Path(__file__).resolve().parents[1]
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def load_classes():
    return json.loads((REPO / "configs" / "classes.json").read_text())["classes"]


def load_thresholds():
    return json.loads((REPO / "configs" / "thresholds.json").read_text())


def build_model(arch, num_classes, pretrained=True):
    if arch == "large":
        w = models.MobileNet_V3_Large_Weights.IMAGENET1K_V2 if pretrained else None
        m = models.mobilenet_v3_large(weights=w)
    elif arch == "small":
        w = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        m = models.mobilenet_v3_small(weights=w)
    else:
        raise ValueError(arch)
    m.classifier[3] = torch.nn.Linear(m.classifier[3].in_features, num_classes)
    return m


def load_checkpoint(path, map_location="cpu"):
    ck = torch.load(path, map_location=map_location, weights_only=False)
    m = build_model(ck["arch"], len(ck["labels"]), pretrained=False)
    m.load_state_dict(ck["state_dict"])
    m.eval()
    return m, ck


def eval_transform(size):
    return transforms.Compose([
        transforms.Resize(round(size * 256 / 224)),
        transforms.CenterCrop(size),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


def read_manifest(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class ManifestDataset(torch.utils.data.Dataset):
    def __init__(self, rows, built_dir, transform):
        self.rows = rows
        self.built = Path(built_dir)
        self.transform = transform

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        with Image.open(self.built / r["image"]) as im:
            x = self.transform(im.convert("RGB"))
        return x, int(r["label_id"])


def crop_mask(labels_in_order, classes, crop):
    """Boolean tensor, True for classes that belong to this crop."""
    crop_of = {c["label"]: c["crop"] for c in classes}
    return torch.tensor([crop_of[lb] == crop for lb in labels_in_order])
