"""Train the MobileNetV3 leaf classifier.

    python -I detection/train.py --root <data_root> --arch large --out <data_root>/models/mnv3l

Stage 1 trains only the new head with the ImageNet backbone frozen. Stage 2
fine-tunes everything for a few epochs at a lower learning rate. After each
epoch we score the validation set and keep the checkpoint with the best macro
F1. At the end a temperature is fitted on the validation logits so the
confidence numbers mean something.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import f1_score
from torch import nn
from torchvision import transforms

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MEAN, STD, ManifestDataset, build_model, eval_transform, load_classes, read_manifest  # noqa: E402


def train_transform(size):
    # Field-style augmentation: framing, angle, light, focus and things in the way.
    return transforms.Compose([
        transforms.RandomResizedCrop(size, scale=(0.45, 1.0), ratio=(0.75, 1.33)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomApply([transforms.RandomRotation(25)], p=0.5),
        transforms.ColorJitter(brightness=0.35, contrast=0.35, saturation=0.3, hue=0.03),
        transforms.RandomApply([transforms.GaussianBlur(5, sigma=(0.1, 2.0))], p=0.3),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
        transforms.RandomErasing(p=0.3, scale=(0.02, 0.15), value="random"),
    ])


def make_sampler(rows, field_weight):
    """Each class drawn about equally often. Inside a class, a field photo is
    field_weight times as likely to be drawn as a lab photo."""
    raw = np.array([field_weight if r["domain"] == "field" else 1.0 for r in rows])
    labels = np.array([int(r["label_id"]) for r in rows])
    w = np.zeros(len(rows))
    for c in np.unique(labels):
        idx = labels == c
        w[idx] = raw[idx] / raw[idx].sum()
    return torch.utils.data.WeightedRandomSampler(torch.tensor(w, dtype=torch.double), len(rows), replacement=True)


@torch.no_grad()
def predict_logits(model, loader, device, amp):
    model.eval()
    out, ys = [], []
    for x, y in loader:
        with torch.autocast(device.type, enabled=amp):
            out.append(model(x.to(device, non_blocking=True)).float().cpu())
        ys.append(y)
    return torch.cat(out), torch.cat(ys)


def fit_temperature(logits, labels):
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)
    nll = nn.CrossEntropyLoss()

    def closure():
        opt.zero_grad()
        loss = nll(logits / log_t.exp(), labels)
        loss.backward()
        return loss

    opt.step(closure)
    return float(log_t.exp())


def set_backbone_trainable(model, trainable):
    for p in model.features.parameters():
        p.requires_grad = trainable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="data folder with built/manifest.csv")
    ap.add_argument("--out", required=True, help="where to write the checkpoint and logs")
    ap.add_argument("--arch", choices=["large", "small"], default="large")
    ap.add_argument("--size", type=int, default=224)
    ap.add_argument("--batch-size", "--batch", dest="batch", type=int, default=32)
    ap.add_argument("--num-workers", "--workers", dest="workers", type=int, default=2)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--device", default="auto", help="auto, cpu or cuda")
    ap.add_argument("--no-amp", action="store_true", help="turn off mixed precision on cuda")
    ap.add_argument("--frozen-epochs", type=int, default=3)
    ap.add_argument("--full-epochs", type=int, default=4)
    ap.add_argument("--epochs", type=int, default=0,
                    help="total epochs; the first --frozen-epochs of them are stage 1, the rest stage 2")
    ap.add_argument("--limit", type=int, default=0, help="use only this many train and val images (smoke test)")
    ap.add_argument("--head-lr", type=float, default=2e-3)
    ap.add_argument("--full-lr", type=float, default=4e-4)
    ap.add_argument("--field-weight", type=float, default=2.0)
    ap.add_argument("--max-steps", type=int, default=0, help="cut each epoch short, for quick tests")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--resume", help="best.pt to start from; skips stage 1 and runs only stage 2")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    amp = device.type == "cuda" and not args.no_amp
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log_file = open(out / "train_log.txt", "a", encoding="utf-8")

    def log(msg):
        print(msg, flush=True)
        log_file.write(msg + "\n")
        log_file.flush()

    classes = load_classes()
    labels = [c["label"] for c in classes]
    built = Path(args.root) / "built"
    rows = read_manifest(built / "manifest.csv")
    train_rows = [r for r in rows if r["split"] == "train"]
    val_rows = [r for r in rows if r["split"] == "val"]
    if args.limit:
        rng = random.Random(args.seed)
        train_rows = rng.sample(train_rows, min(args.limit, len(train_rows)))
        val_rows = rng.sample(val_rows, min(args.limit, len(val_rows)))
    resume_ck = None
    if args.resume:
        resume_ck = torch.load(args.resume, map_location="cpu", weights_only=False)
        if resume_ck["labels"] != labels:
            raise SystemExit("--resume checkpoint has different labels from configs/classes.json")
        args.arch, args.size = resume_ck["arch"], resume_ck["size"]
        args.frozen_epochs = 0  # the head is already trained, go straight to stage 2
    if args.epochs:
        args.frozen_epochs = min(args.frozen_epochs, args.epochs)
        args.full_epochs = args.epochs - args.frozen_epochs
    val_field = np.array([r["domain"] == "field" for r in val_rows])
    log(f"args: {vars(args)}")
    log(f"device {device}, amp {amp}, train {len(train_rows)}, val {len(val_rows)}")

    pin = device.type == "cuda"
    train_dl = torch.utils.data.DataLoader(
        ManifestDataset(train_rows, built, train_transform(args.size)), batch_size=args.batch,
        sampler=make_sampler(train_rows, args.field_weight), num_workers=args.workers,
        pin_memory=pin, persistent_workers=args.workers > 0, drop_last=True)
    val_dl = torch.utils.data.DataLoader(
        ManifestDataset(val_rows, built, eval_transform(args.size)), batch_size=args.batch * 2,
        num_workers=args.workers, pin_memory=pin, persistent_workers=args.workers > 0)

    model = build_model(args.arch, len(labels), pretrained=resume_ck is None)
    if resume_ck is not None:
        model.load_state_dict(resume_ck["state_dict"])
        log(f"resumed from {args.resume} (epoch {resume_ck.get('epoch')}, "
            f"val macro F1 {resume_ck.get('val_macro_f1')})")
    model = model.to(device)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)
    scaler = torch.amp.GradScaler(enabled=amp)

    best_f1, history = -1.0, []
    t_start = time.time()
    total_epochs = args.frozen_epochs + args.full_epochs
    steps_per_epoch = len(train_dl) if not args.max_steps else min(args.max_steps, len(train_dl))

    for epoch in range(total_epochs):
        frozen = epoch < args.frozen_epochs
        if epoch == 0 or epoch == args.frozen_epochs:
            set_backbone_trainable(model, not frozen)
            params = [p for p in model.parameters() if p.requires_grad]
            lr = args.head_lr if frozen else args.full_lr
            n_ep = args.frozen_epochs if frozen else args.full_epochs
            opt = torch.optim.AdamW(params, lr=lr, weight_decay=1e-4)
            sched = torch.optim.lr_scheduler.OneCycleLR(
                opt, max_lr=lr, total_steps=n_ep * steps_per_epoch, pct_start=0.15)
            log(f"stage {'1 (frozen backbone)' if frozen else '2 (full fine-tune)'}, lr {lr}")

        model.train()
        if frozen:
            model.features.eval()  # keep ImageNet batch norm stats while the backbone is frozen
        t0 = time.time()
        run_loss, n = 0.0, 0
        for step, (x, y) in enumerate(train_dl):
            if step >= steps_per_epoch:
                break
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            with torch.autocast(device.type, enabled=amp):
                loss = loss_fn(model(x), y)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
            run_loss += loss.item() * len(y)
            n += len(y)
            if step % 50 == 0:
                log(f"  epoch {epoch + 1} step {step}/{steps_per_epoch} loss {loss.item():.3f} "
                    f"{(time.time() - t0) / (step + 1):.2f} s/step")
        train_s = time.time() - t0

        logits, ys = predict_logits(model, val_dl, device, amp)
        pred = logits.argmax(1).numpy()
        y = ys.numpy()
        f1 = f1_score(y, pred, average="macro", labels=range(len(labels)), zero_division=0)
        f1_field = f1_score(y[val_field], pred[val_field], average="macro",
                            labels=sorted(set(y[val_field])), zero_division=0)
        acc = float((pred == y).mean())
        epoch_s = time.time() - t0
        rec = dict(epoch=epoch + 1, stage=1 if frozen else 2, train_loss=run_loss / max(n, 1),
                   val_acc=acc, val_macro_f1=f1, val_field_macro_f1=f1_field,
                   train_seconds=round(train_s, 1), epoch_seconds=round(epoch_s, 1))
        history.append(rec)
        log(f"epoch {epoch + 1}/{total_epochs}: loss {rec['train_loss']:.3f} val acc {acc:.4f} "
            f"val macro F1 {f1:.4f} val field macro F1 {f1_field:.4f} ({epoch_s:.0f} s)")
        if f1 > best_f1:
            best_f1 = f1
            torch.save({"arch": args.arch, "size": args.size, "labels": labels,
                        "state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
                        "epoch": epoch + 1, "val_macro_f1": f1}, out / "best.pt")
            log(f"  saved best.pt (val macro F1 {f1:.4f})")

    total_s = time.time() - t_start

    # temperature on the best checkpoint
    ck = torch.load(out / "best.pt", map_location=device, weights_only=False)
    model.load_state_dict(ck["state_dict"])
    logits, ys = predict_logits(model, val_dl, device, amp)
    t = fit_temperature(logits, ys)
    nll = nn.CrossEntropyLoss()
    before, after = float(nll(logits, ys)), float(nll(logits / t, ys))
    (out / "temperature.json").write_text(json.dumps(
        {"temperature": t, "val_nll_before": before, "val_nll_after": after}, indent=1))
    log(f"temperature {t:.3f} (val NLL {before:.4f} -> {after:.4f})")

    summary = dict(args=vars(args), device=str(device), train_images=len(train_rows),
                   val_images=len(val_rows), best_epoch=ck["epoch"], best_val_macro_f1=best_f1,
                   temperature=t, total_train_seconds=round(total_s, 1),
                   mean_epoch_seconds=round(sum(h["epoch_seconds"] for h in history) / len(history), 1),
                   history=history)
    (out / "train_summary.json").write_text(json.dumps(summary, indent=1))
    log(f"done in {total_s / 60:.1f} min, best epoch {ck['epoch']}, val macro F1 {best_f1:.4f}")


if __name__ == "__main__":
    main()
