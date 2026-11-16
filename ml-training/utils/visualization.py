"""
Visualization Helpers for CrisisMap ML Fine-Tuning.

Generates publication-quality plots for:
  - Training/validation loss curves
  - Confusion matrix heatmaps
  - Per-class F1 bar charts
  - ROC curves with AUC
  - Sample prediction overlays (pre/post + pred vs ground truth)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# Use non-interactive backend for Kaggle/Colab
matplotlib.use("Agg")

# Default style
plt.rcParams.update({
    "figure.figsize": (10, 6),
    "figure.dpi": 120,
    "axes.grid": True,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "grid.alpha": 0.3,
    "font.family": "sans-serif",
})

# Damage class colors (consistent across all plots)
DAMAGE_COLORS = {
    "background": "#333333",
    "no-damage": "#2ecc71",
    "minor-damage": "#f1c40f",
    "major-damage": "#e67e22",
    "destroyed": "#e74c3c",
}

DAMAGE_CMAP_ARRAY = [
    [0.2, 0.2, 0.2, 1.0],     # background - dark gray
    [0.18, 0.80, 0.44, 1.0],  # no-damage - green
    [0.95, 0.77, 0.06, 1.0],  # minor-damage - yellow
    [0.90, 0.49, 0.13, 1.0],  # major-damage - orange
    [0.91, 0.30, 0.24, 1.0],  # destroyed - red
]


def plot_loss_curves(
    train_losses: list[float],
    val_losses: list[float],
    title: str = "Training & Validation Loss",
    save_path: Optional[str | Path] = None,
) -> plt.Figure:
    """Plot training and validation loss curves.

    Args:
        train_losses: List of training losses per epoch
        val_losses: List of validation losses per epoch
        title: Plot title
        save_path: Optional path to save the figure

    Returns:
        matplotlib Figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    epochs = range(1, len(train_losses) + 1)

    ax.plot(epochs, train_losses, "b-", linewidth=2, label="Train Loss", alpha=0.8)
    ax.plot(epochs, val_losses, "r-", linewidth=2, label="Val Loss", alpha=0.8)

    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title(title)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)

    # Mark best validation epoch
    best_epoch = np.argmin(val_losses) + 1
    best_val = min(val_losses)
    ax.axvline(x=best_epoch, color="gray", linestyle="--", alpha=0.5)
    ax.annotate(
        f"Best: {best_val:.4f} (epoch {best_epoch})",
        xy=(best_epoch, best_val),
        xytext=(best_epoch + 1, best_val + 0.01),
        fontsize=10,
        arrowprops=dict(arrowstyle="->", color="gray"),
    )

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_f1_curves(
    f1_per_epoch: dict[str, list[float]],
    title: str = "Per-Class F1 Score",
    save_path: Optional[str | Path] = None,
) -> plt.Figure:
    """Plot F1 score curves per class over epochs.

    Args:
        f1_per_epoch: Dict mapping class name to list of F1 scores per epoch
        title: Plot title
        save_path: Optional save path

    Returns:
        matplotlib Figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    for cls_name, f1s in f1_per_epoch.items():
        epochs = range(1, len(f1s) + 1)
        color = DAMAGE_COLORS.get(cls_name, None)
        ax.plot(epochs, f1s, linewidth=2, label=cls_name, color=color, alpha=0.8)

    ax.set_xlabel("Epoch")
    ax.set_ylabel("F1 Score")
    ax.set_title(title)
    ax.legend(fontsize=10, loc="lower right")
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_confusion_matrix(
    matrix: np.ndarray,
    class_names: list[str],
    title: str = "Confusion Matrix",
    normalize: bool = True,
    save_path: Optional[str | Path] = None,
) -> plt.Figure:
    """Plot a confusion matrix heatmap.

    Args:
        matrix: Confusion matrix (num_classes x num_classes)
        class_names: List of class name strings
        title: Plot title
        normalize: Whether to normalize by row (true class)
        save_path: Optional save path

    Returns:
        matplotlib Figure
    """
    import seaborn as sns

    if normalize:
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums == 0, 1, row_sums)
        norm_matrix = matrix.astype(float) / row_sums
    else:
        norm_matrix = matrix.astype(float)

    fig, ax = plt.subplots(figsize=(8, 7))

    sns.heatmap(
        norm_matrix,
        annot=True,
        fmt=".2f" if normalize else "d",
        cmap="YlOrRd",
        xticklabels=class_names,
        yticklabels=class_names,
        ax=ax,
        square=True,
        linewidths=0.5,
        cbar_kws={"label": "Proportion" if normalize else "Count"},
        vmin=0,
        vmax=1 if normalize else None,
    )

    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("True", fontsize=12)
    ax.set_title(title, fontsize=14)

    # Rotate labels
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_roc_curves(
    roc_data: dict[str, dict[str, Any]],
    title: str = "ROC Curves (One-vs-Rest)",
    save_path: Optional[str | Path] = None,
) -> plt.Figure:
    """Plot ROC curves for each class.

    Args:
        roc_data: Dict from compute_roc_data()
        title: Plot title
        save_path: Optional save path

    Returns:
        matplotlib Figure
    """
    fig, ax = plt.subplots(figsize=(8, 8))

    for cls_name, data in roc_data.items():
        color = DAMAGE_COLORS.get(cls_name, None)
        auc = data["auc"]
        ax.plot(
            data["fpr"],
            data["tpr"],
            linewidth=2,
            label=f"{cls_name} (AUC={auc:.3f})",
            color=color,
            alpha=0.8,
        )

    # Diagonal
    ax.plot([0, 1], [0, 1], "k--", alpha=0.3, linewidth=1)

    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(title)
    ax.legend(fontsize=10, loc="lower right")
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1.02])
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_sample_prediction(
    pre_img: np.ndarray,
    post_img: np.ndarray,
    pred_mask: np.ndarray,
    gt_mask: np.ndarray,
    title: str = "Sample Prediction",
    save_path: Optional[str | Path] = None,
) -> plt.Figure:
    """Plot a sample prediction with pre/post images and pred/gt masks.

    Args:
        pre_img: Pre-disaster image (H, W, 3) or (3, H, W), float [0,1]
        post_img: Post-disaster image
        pred_mask: Predicted damage mask (H, W), int 0-4
        gt_mask: Ground truth damage mask (H, W), int 0-4
        title: Plot title
        save_path: Optional save path

    Returns:
        matplotlib Figure
    """
    # Convert CHW to HWC if needed
    if pre_img.ndim == 3 and pre_img.shape[0] == 3:
        pre_img = pre_img.transpose(1, 2, 0)
    if post_img.ndim == 3 and post_img.shape[0] == 3:
        post_img = post_img.transpose(1, 2, 0)

    # Clip to valid range
    pre_img = np.clip(pre_img, 0, 1)
    post_img = np.clip(post_img, 0, 1)

    # Create colormap for damage masks
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(DAMAGE_CMAP_ARRAY)

    fig, axes = plt.subplots(1, 4, figsize=(20, 5))

    axes[0].imshow(pre_img)
    axes[0].set_title("Pre-Disaster", fontsize=12)
    axes[0].axis("off")

    axes[1].imshow(post_img)
    axes[1].set_title("Post-Disaster", fontsize=12)
    axes[1].axis("off")

    axes[2].imshow(gt_mask, cmap=cmap, vmin=0, vmax=4, interpolation="nearest")
    axes[2].set_title("Ground Truth", fontsize=12)
    axes[2].axis("off")

    im = axes[3].imshow(pred_mask, cmap=cmap, vmin=0, vmax=4, interpolation="nearest")
    axes[3].set_title("Prediction", fontsize=12)
    axes[3].axis("off")

    # Add colorbar
    cbar = fig.colorbar(im, ax=axes, fraction=0.02, pad=0.02)
    cbar.set_ticks([0, 1, 2, 3, 4])
    cbar.set_ticklabels(["BG", "No Dmg", "Minor", "Major", "Destroyed"])

    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_class_distribution(
    distribution: dict[str, float],
    title: str = "Damage Class Distribution",
    save_path: Optional[str | Path] = None,
) -> plt.Figure:
    """Plot class distribution as a bar chart.

    Args:
        distribution: Dict mapping class name to percentage
        title: Plot title
        save_path: Optional save path

    Returns:
        matplotlib Figure
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    names = list(distribution.keys())
    values = list(distribution.values())
    colors = [DAMAGE_COLORS.get(n, "#666666") for n in names]

    bars = ax.bar(names, values, color=colors, edgecolor="white", linewidth=0.5)

    # Add value labels
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{val:.1f}%",
            ha="center",
            fontsize=11,
            fontweight="bold",
        )

    ax.set_ylabel("Percentage (%)")
    ax.set_title(title, fontsize=14)
    ax.set_ylim(0, max(values) * 1.15)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_f1_comparison(
    before: dict[str, float],
    after: dict[str, float],
    title: str = "F1 Score Comparison: Before vs After Fine-Tuning",
    save_path: Optional[str | Path] = None,
) -> plt.Figure:
    """Plot before/after F1 comparison as grouped bar chart.

    Args:
        before: Dict mapping class name to F1 before fine-tuning
        after: Dict mapping class name to F1 after fine-tuning
        title: Plot title
        save_path: Optional save path

    Returns:
        matplotlib Figure
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    classes = list(after.keys())
    x = np.arange(len(classes))
    width = 0.35

    before_vals = [before.get(c, 0.0) for c in classes]
    after_vals = [after.get(c, 0.0) for c in classes]

    bars1 = ax.bar(x - width / 2, before_vals, width, label="Before (Zero-Shot)",
                   color="#95a5a6", edgecolor="white")
    bars2 = ax.bar(x + width / 2, after_vals, width, label="After (Fine-Tuned)",
                   color="#2ecc71", edgecolor="white")

    # Add value labels
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{bar.get_height():.3f}", ha="center", fontsize=9)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{bar.get_height():.3f}", ha="center", fontsize=9)

    ax.set_ylabel("F1 Score")
    ax.set_title(title, fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(classes, rotation=30, ha="right")
    ax.legend(fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.grid(True, axis="y", alpha=0.3)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig
