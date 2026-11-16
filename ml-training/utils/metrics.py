"""
Evaluation Metrics for CrisisMap ML Fine-Tuning.

POIN 5 COMPLIANCE:
  - PIXEL-LEVEL metrics: for training loss optimization
  - BUILDING-LEVEL metrics: for journal reporting (matches app pipeline)
  
  The app computes building-level damage by averaging softmax probabilities
  over the building footprint (ml_inference.py L75):
    probabilities_tensor = torch.softmax(damage_logits, dim=1).mean(dim=(0, 2, 3))
  
  EMSR452 ground truth is per-building → evaluation MUST be building-level.
"""

from __future__ import annotations

from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Pixel-Level Metrics (for training loss monitoring)
# ---------------------------------------------------------------------------

def pixel_accuracy(pred: np.ndarray, target: np.ndarray) -> float:
    """Overall pixel accuracy.

    Args:
        pred: predicted class indices (H, W) or (N, H, W)
        target: ground truth class indices, same shape

    Returns:
        Fraction of correctly classified pixels
    """
    return float((pred == target).sum() / target.size)


def pixel_iou(pred: np.ndarray, target: np.ndarray, num_classes: int = 2) -> dict[str, float]:
    """Per-class IoU (Intersection over Union) for segmentation.

    Args:
        pred: predicted class indices (H, W) or (N, H, W)
        target: ground truth class indices, same shape
        num_classes: number of classes

    Returns:
        Dict with per-class IoU and mean IoU
    """
    ious = {}
    for cls in range(num_classes):
        pred_cls = (pred == cls)
        target_cls = (target == cls)
        intersection = (pred_cls & target_cls).sum()
        union = (pred_cls | target_cls).sum()
        if union == 0:
            ious[f"class_{cls}"] = float("nan")  # class not present
        else:
            ious[f"class_{cls}"] = float(intersection / union)

    valid_ious = [v for v in ious.values() if not np.isnan(v)]
    ious["mean_iou"] = float(np.mean(valid_ious)) if valid_ious else 0.0
    return ious


def pixel_f1_per_class(
    pred: np.ndarray,
    target: np.ndarray,
    num_classes: int = 5,
    class_names: list[str] | None = None,
) -> dict[str, dict[str, float]]:
    """Per-class precision, recall, F1 at pixel level.

    Args:
        pred: predicted class indices
        target: ground truth class indices
        num_classes: number of classes
        class_names: optional list of class name strings

    Returns:
        Dict mapping class name to {precision, recall, f1, support}
    """
    if class_names is None:
        class_names = [f"class_{i}" for i in range(num_classes)]

    results = {}
    for cls in range(num_classes):
        tp = int(((pred == cls) & (target == cls)).sum())
        fp = int(((pred == cls) & (target != cls)).sum())
        fn = int(((pred != cls) & (target == cls)).sum())

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        results[class_names[cls]] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": int(((target == cls)).sum()),
        }

    # Macro F1
    f1_values = [r["f1"] for r in results.values() if r["support"] > 0]
    results["macro_f1"] = round(float(np.mean(f1_values)), 4) if f1_values else 0.0

    return results


# ---------------------------------------------------------------------------
# Building-Level Metrics (for journal reporting — POIN 5)
# ---------------------------------------------------------------------------

def building_level_prediction(
    damage_logits: np.ndarray,
    building_mask: np.ndarray,
    num_classes: int = 5,
) -> dict[str, Any]:
    """Compute building-level damage prediction by averaging softmax over building footprint.

    This matches the backend pipeline exactly (ml_inference.py L75):
      probabilities_tensor = torch.softmax(damage_logits, dim=1).mean(dim=(0, 2, 3))

    Args:
        damage_logits: model output logits (C, H, W) — NOT softmaxed
        building_mask: binary mask (H, W) where 1 = building pixels
        num_classes: number of damage classes

    Returns:
        Dict with predicted_class (int), probabilities (array), confidence (float)
    """
    # Softmax across classes
    logits = damage_logits.astype(np.float64)
    exp_logits = np.exp(logits - logits.max(axis=0, keepdims=True))
    probs = exp_logits / exp_logits.sum(axis=0, keepdims=True)  # (C, H, W)

    # Average over building pixels
    building_pixels = building_mask.astype(bool)
    if building_pixels.sum() == 0:
        # No building pixels — return background
        return {
            "predicted_class": 0,
            "probabilities": np.zeros(num_classes),
            "confidence": 0.0,
        }

    avg_probs = probs[:, building_pixels].mean(axis=1)  # (C,)
    predicted_class = int(avg_probs.argmax())

    return {
        "predicted_class": predicted_class,
        "probabilities": avg_probs,
        "confidence": float(avg_probs.max()),
    }


def confusion_matrix(
    y_true: list[int] | np.ndarray,
    y_pred: list[int] | np.ndarray,
    num_classes: int = 5,
    class_names: list[str] | None = None,
) -> dict[str, Any]:
    """Compute confusion matrix and derived metrics.

    Args:
        y_true: ground truth class labels (building-level)
        y_pred: predicted class labels (building-level)
        num_classes: number of classes
        class_names: optional class name strings

    Returns:
        Dict with matrix, per_class metrics, macro_f1, accuracy
    """
    if class_names is None:
        class_names = [f"class_{i}" for i in range(num_classes)]

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    # Build matrix
    matrix = np.zeros((num_classes, num_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            matrix[t, p] += 1

    # Per-class metrics
    per_class = {}
    f1_values = []
    for cls in range(num_classes):
        tp = int(matrix[cls, cls])
        fp = int(matrix[:, cls].sum() - tp)
        fn = int(matrix[cls, :].sum() - tp)
        support = int(matrix[cls, :].sum())

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_class[class_names[cls]] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }

        if support > 0:
            f1_values.append(f1)

    total = len(y_true)
    correct = int(np.diag(matrix).sum())

    return {
        "matrix": matrix,
        "class_names": class_names,
        "per_class": per_class,
        "accuracy": round(correct / total, 4) if total > 0 else 0.0,
        "macro_f1": round(float(np.mean(f1_values)), 4) if f1_values else 0.0,
        "total_samples": total,
    }


def compute_roc_data(
    y_true: np.ndarray,
    y_probs: np.ndarray,
    num_classes: int = 5,
    class_names: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Compute ROC curve data (one-vs-rest) for each class.

    Args:
        y_true: ground truth labels, shape (N,)
        y_probs: predicted probabilities, shape (N, num_classes)
        num_classes: number of classes
        class_names: optional class name strings

    Returns:
        Dict mapping class name to {fpr, tpr, auc}
    """
    if class_names is None:
        class_names = [f"class_{i}" for i in range(num_classes)]

    roc_data = {}
    for cls in range(num_classes):
        binary_true = (np.asarray(y_true) == cls).astype(int)
        scores = np.asarray(y_probs)[:, cls]

        # Sort by descending score
        sorted_idx = np.argsort(-scores)
        binary_true_sorted = binary_true[sorted_idx]
        scores_sorted = scores[sorted_idx]

        # Compute TPR and FPR at each threshold
        tps = np.cumsum(binary_true_sorted)
        fps = np.cumsum(1 - binary_true_sorted)
        total_pos = binary_true.sum()
        total_neg = len(binary_true) - total_pos

        if total_pos == 0 or total_neg == 0:
            roc_data[class_names[cls]] = {
                "fpr": [0.0, 1.0],
                "tpr": [0.0, 1.0],
                "auc": 0.5,
            }
            continue

        tpr = np.concatenate([[0], tps / total_pos])
        fpr = np.concatenate([[0], fps / total_neg])

        # AUC via trapezoidal rule
        auc = float(np.trapz(tpr, fpr))

        roc_data[class_names[cls]] = {
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
            "auc": round(auc, 4),
        }

    return roc_data


# ---------------------------------------------------------------------------
# Checkpoint Compatibility Check (POIN 4)
# ---------------------------------------------------------------------------

def verify_checkpoint_compatibility(
    checkpoint_path: str,
    model_class: type,
    expected_output_shapes: dict[str, tuple] | None = None,
) -> dict[str, Any]:
    """Verify that a checkpoint can be loaded by the backend.

    Checks:
      1. File loads with map_location="cpu"
      2. Contains 'state_dict' key
      3. No missing keys when loaded into model
      4. Forward pass produces expected output shapes

    Args:
        checkpoint_path: Path to .pth.tar file
        model_class: Model class (e.g. SiamUnet)
        expected_output_shapes: Optional dict of expected shapes

    Returns:
        Dict with verification results
    """
    import torch

    results: dict[str, Any] = {"passed": True, "checks": []}

    # Check 1: Load checkpoint
    try:
        try:
            ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        except (TypeError, Exception):
            ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        results["checks"].append({"name": "load_checkpoint", "passed": True})
    except Exception as e:
        results["checks"].append({"name": "load_checkpoint", "passed": False, "error": str(e)})
        results["passed"] = False
        return results

    # Check 2: Has 'state_dict' key
    if isinstance(ckpt, dict) and "state_dict" in ckpt:
        state_dict = ckpt["state_dict"]
        results["checks"].append({"name": "has_state_dict_key", "passed": True})
        results["epoch"] = ckpt.get("epoch")
        results["best_f1"] = ckpt.get("best_f1")
    else:
        results["checks"].append({"name": "has_state_dict_key", "passed": False})
        results["passed"] = False
        return results

    # Check 3: No prefix (module., model.)
    has_prefix = any(k.startswith(("module.", "model.")) for k in state_dict)
    results["checks"].append({
        "name": "no_prefix",
        "passed": not has_prefix,
        "note": "Keys should NOT have module. or model. prefix",
    })
    if has_prefix:
        results["passed"] = False

    # Check 4: Load into model
    try:
        model = model_class()
        load_result = model.load_state_dict(state_dict, strict=True)
        results["checks"].append({
            "name": "strict_load",
            "passed": True,
            "missing_keys": list(load_result.missing_keys),
            "unexpected_keys": list(load_result.unexpected_keys),
        })
    except Exception as e:
        results["checks"].append({"name": "strict_load", "passed": False, "error": str(e)})
        results["passed"] = False
        return results

    # Check 5: Forward pass
    try:
        model.eval()
        dummy_pre = torch.randn(1, 3, 256, 256)
        dummy_post = torch.randn(1, 3, 256, 256)
        with torch.no_grad():
            outputs = model(dummy_pre, dummy_post)

        shapes = {
            "seg_pre": tuple(outputs[0].shape),
            "seg_post": tuple(outputs[1].shape),
            "damage": tuple(outputs[2].shape),
        }
        results["output_shapes"] = shapes
        results["checks"].append({"name": "forward_pass", "passed": True, "shapes": shapes})

        if expected_output_shapes:
            for key, expected in expected_output_shapes.items():
                if shapes.get(key) != expected:
                    results["checks"].append({
                        "name": f"shape_{key}",
                        "passed": False,
                        "expected": expected,
                        "got": shapes.get(key),
                    })
                    results["passed"] = False
    except Exception as e:
        results["checks"].append({"name": "forward_pass", "passed": False, "error": str(e)})
        results["passed"] = False

    return results
