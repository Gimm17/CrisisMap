"""
Data Transforms & Normalization for CrisisMap ML Fine-Tuning.

PREPROCESSING PARITY RULE:
  Training normalization MUST produce tensors compatible with backend inference.
  
  Backend (ml_inference.py):
    data = src.read(indexes=[1,2,3])      # RGB
    data = data.astype("float32")
    scale = max(float(np.percentile(data, 99)), 255.0)
    data = np.clip(data / scale, 0.0, 1.0)
    
  Training (xBD PNG, 8-bit):
    img = img.astype("float32") / 255.0   # equivalent since p99 ≈ 255 for 8-bit
    
  The small difference (p99 vs fixed 255) is part of the domain shift
  that Stage B calibration addresses.
"""

from __future__ import annotations

import numpy as np
import torch


def normalize_xbd_png(img: np.ndarray) -> np.ndarray:
    """Normalize an xBD 8-bit PNG image to [0, 1] float32.

    This is the CANONICAL normalization for training.
    Matches backend ml_inference.py behavior on 8-bit data.

    Args:
        img: numpy array of shape (H, W, 3) or (3, H, W), uint8 or float

    Returns:
        float32 array in [0, 1] range, same shape as input
    """
    img = img.astype(np.float32)
    if img.max() > 1.0:
        img = img / 255.0
    return np.clip(img, 0.0, 1.0)


def normalize_geotiff(img: np.ndarray) -> np.ndarray:
    """Normalize a GeoTIFF image using percentile scaling.

    Matches backend ml_inference.py exactly:
      scale = max(p99, 255.0)
      data = clip(data / scale, 0, 1)

    Used for Stage B (Beirut Maxar GeoTIFF).

    Args:
        img: numpy array, any bit depth

    Returns:
        float32 array in [0, 1] range
    """
    img = img.astype(np.float32)
    scale = max(float(np.percentile(img, 99)), 255.0)
    return np.clip(img / scale, 0.0, 1.0)


def to_tensor(img: np.ndarray) -> torch.Tensor:
    """Convert numpy HWC image to CHW float32 tensor.

    Args:
        img: (H, W, C) numpy array, assumed already normalized

    Returns:
        (C, H, W) float32 tensor
    """
    if img.ndim == 3 and img.shape[2] in (1, 3):
        img = img.transpose(2, 0, 1)  # HWC → CHW
    return torch.from_numpy(img.astype(np.float32))


def mask_to_tensor(mask: np.ndarray) -> torch.Tensor:
    """Convert label mask to int64 tensor.

    Args:
        mask: (H, W) numpy array with integer class labels

    Returns:
        (H, W) int64 tensor
    """
    return torch.from_numpy(mask.astype(np.int64))


class PairedRandomCrop:
    """Random crop that applies the SAME crop to pre, post, and all masks."""

    def __init__(self, crop_size: int = 256):
        self.crop_size = crop_size

    def __call__(
        self,
        pre: np.ndarray,
        post: np.ndarray,
        *masks: np.ndarray,
    ) -> tuple:
        h, w = pre.shape[:2] if pre.ndim == 3 else pre.shape[1:]
        if h < self.crop_size or w < self.crop_size:
            raise ValueError(
                f"Image size ({h}, {w}) smaller than crop_size ({self.crop_size})"
            )

        top = np.random.randint(0, h - self.crop_size + 1)
        left = np.random.randint(0, w - self.crop_size + 1)

        if pre.ndim == 3:  # HWC
            pre_crop = pre[top:top + self.crop_size, left:left + self.crop_size]
            post_crop = post[top:top + self.crop_size, left:left + self.crop_size]
        else:  # CHW
            pre_crop = pre[:, top:top + self.crop_size, left:left + self.crop_size]
            post_crop = post[:, top:top + self.crop_size, left:left + self.crop_size]

        mask_crops = []
        for m in masks:
            mask_crops.append(m[top:top + self.crop_size, left:left + self.crop_size])

        return (pre_crop, post_crop, *mask_crops)


class PairedFlip:
    """Random horizontal and vertical flip for paired images + masks."""

    def __init__(self, p_horizontal: float = 0.5, p_vertical: float = 0.5):
        self.p_h = p_horizontal
        self.p_v = p_vertical

    def __call__(
        self,
        pre: np.ndarray,
        post: np.ndarray,
        *masks: np.ndarray,
    ) -> tuple:
        # Horizontal flip
        if np.random.random() < self.p_h:
            axis_img = -1 if pre.ndim == 2 else (2 if pre.ndim == 3 and pre.shape[0] in (1, 3) else 1)
            pre = np.flip(pre, axis=axis_img).copy()
            post = np.flip(post, axis=axis_img).copy()
            masks = tuple(np.flip(m, axis=-1).copy() for m in masks)

        # Vertical flip
        if np.random.random() < self.p_v:
            axis_img = -2 if pre.ndim == 3 else 0
            if pre.ndim == 3 and pre.shape[0] in (1, 3):
                axis_img = 1
            pre = np.flip(pre, axis=axis_img).copy()
            post = np.flip(post, axis=axis_img).copy()
            masks = tuple(np.flip(m, axis=0).copy() for m in masks)

        return (pre, post, *masks)


class ColorJitter:
    """Slight color jitter for images (NOT masks).

    Applied identically to both pre and post to maintain relative differences.
    """

    def __init__(
        self,
        brightness: float = 0.1,
        contrast: float = 0.1,
        saturation: float = 0.05,
    ):
        self.brightness = brightness
        self.contrast = contrast
        self.saturation = saturation

    def __call__(self, img: np.ndarray) -> np.ndarray:
        """Apply color jitter to a single normalized image (CHW or HWC, float32)."""
        # Brightness
        b = 1.0 + np.random.uniform(-self.brightness, self.brightness)
        img = img * b

        # Contrast
        c = 1.0 + np.random.uniform(-self.contrast, self.contrast)
        mean = img.mean()
        img = (img - mean) * c + mean

        return np.clip(img, 0.0, 1.0)
