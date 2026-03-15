"""
Build a 21×21 JAB-style matrix from the Intigriti bug bounty coin image.

The coin has a circular grid of "bees" (company logo) in different orientations.
Each orientation is mapped to a symbol value (e.g. 0-3 for 4 colors or 0-7 for 8).
We extract the grid, classify orientations, then try rotations and mappings for decoding.

Usage:
  pip install numpy opencv-python pillow
  python jab_coin_decode.py

Then try decoding the generated images at https://jabcode.org/scan
or use the C reader from https://github.com/jabcode/jabcode
"""

from __future__ import annotations

import itertools
import os
import sys
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None
try:
    from PIL import Image
except ImportError:
    Image = None


# Default path to the coin image: pass as first argument or set JAB_COIN_IMAGE
SCRIPT_DIR = Path(__file__).resolve().parent
# Cursor may save provided images under assets (path relative to project)
ASSET_DIR = Path(__file__).resolve().parent / ".cursor" / "projects" / "Users-curuser-Documents-src-test" / "assets"
COIN_IMAGE_PATH = ASSET_DIR / "8298A22C-074B-490E-8686-AE226E0B7D00-f33742fc-0432-4150-aec8-b6ff4517914a.png"

# JAB primary symbol is 21×21 (version 1: (21-17)/4 = 1)
GRID_SIZE = 21

# 4 directions (up, right, down, left) -> often mapped to 4 JAB colors (e.g. CMYK)
NUM_DIRECTIONS_4 = 4
# 8 directions for higher capacity
NUM_DIRECTIONS_8 = 8

# JAB default palette indices: 0=black, 1=blue, 2=green, 3=cyan, 4=red, 5=magenta, 6=yellow, 7=white
# 4-color mode often uses 0,3,5,6 (K,C,M,Y) or subset
JAB_PALETTE_RGB = [
    (0, 0, 0),       # 0 black
    (0, 0, 255),     # 1 blue
    (0, 255, 0),     # 2 green
    (0, 255, 255),   # 3 cyan
    (255, 0, 0),     # 4 red
    (255, 0, 255),   # 5 magenta
    (255, 255, 0),   # 6 yellow
    (255, 255, 255), # 7 white
]


def load_image(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Coin image not found: {path}")
    if cv2 is not None:
        img = cv2.imread(str(path))
        if img is not None:
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    if Image is not None:
        img = Image.open(path)
        return np.array(img.convert("RGB"))
    raise RuntimeError("Need opencv-python or Pillow to load image")


def find_circle_region(img: np.ndarray) -> tuple[int, int, int]:
    """Estimate circle center and radius of the central pattern (dark symbols on light)."""
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img
    h, w = gray.shape
    center_x, center_y = w // 2, h // 2
    # Use inner region (avoid text ring); radius ~40% of half min dimension
    radius = int(min(w, h) * 0.38)
    return center_x, center_y, radius


def extract_square_grid(img: np.ndarray, cx: int, cy: int, radius: int, size: int) -> np.ndarray:
    """
    Extract a size×size grid from the circular region.
    We take a square crop centered at (cx,cy) with side = 2*radius, then sample size×size.
    """
    x0 = max(0, cx - radius)
    y0 = max(0, cy - radius)
    x1 = min(img.shape[1], cx + radius)
    y1 = min(img.shape[0], cy + radius)
    crop = img[y0:y1, x0:x1]
    if crop.size == 0:
        raise ValueError("Empty crop")
    # Resize to size×size so we have one pixel per module (we'll refine with blocks)
    return cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA) if cv2 is not None else _resize_pil(crop, size)


def _resize_pil(arr: np.ndarray, size: int) -> np.ndarray:
    from PIL import Image
    p = Image.fromarray(arr)
    p = p.resize((size, size), Image.Resampling.LANCZOS)
    return np.array(p)


def classify_orientation_4(gray_cell: np.ndarray) -> int:
    """
    Classify cell into 4 directions (0..3) using gradient direction.
    Bee "head" is the pointy part; gradient tends to align with it.
    Returns 0=up, 1=right, 2=down, 3=left (angles 0, 90, 180, 270 deg).
    """
    if gray_cell.size == 0:
        return 0
    gx = cv2.Sobel(gray_cell, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray_cell, cv2.CV_64F, 0, 1, ksize=3)
    # Dominant direction: atan2(gy, gx) -> we quantize to 4
    angle = np.arctan2(np.mean(gy), np.mean(gx))  # rad
    deg = np.degrees(angle) % 360
    # Map to 0..3: 0=up (~270/90), 1=right (~0), 2=down (~90/270), 3=left (~180)
    if deg < 45 or deg >= 315:
        return 1   # right
    if 45 <= deg < 135:
        return 2   # down
    if 135 <= deg < 225:
        return 3   # left
    return 0       # up


def classify_orientation_8(gray_cell: np.ndarray) -> int:
    """Classify into 8 directions (0..7)."""
    if gray_cell.size == 0:
        return 0
    gx = cv2.Sobel(gray_cell, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray_cell, cv2.CV_64F, 0, 1, ksize=3)
    angle = np.arctan2(np.mean(gy), np.mean(gx))
    deg = (np.degrees(angle) + 360 + 22.5) % 360
    return int(deg / 45) % 8


def build_orientation_matrix(img: np.ndarray, grid_size: int, use_8: bool = False) -> np.ndarray:
    """Build grid_size×grid_size matrix of orientation indices from full image."""
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img
    cx, cy, radius = find_circle_region(img)
    # Sample per-cell from original image for better gradient
    cell_radius = radius * 2 / grid_size
    mat = np.zeros((grid_size, grid_size), dtype=np.int32)
    for row in range(grid_size):
        for col in range(grid_size):
            # Cell center in original image
            ox = cx - radius + (col + 0.5) * (2 * radius / grid_size)
            oy = cy - radius + (row + 0.5) * (2 * radius / grid_size)
            r = int(cell_radius)
            y0 = max(0, int(oy) - r)
            y1 = min(gray.shape[0], int(oy) + r + 1)
            x0 = max(0, int(ox) - r)
            x1 = min(gray.shape[1], int(ox) + r + 1)
            cell = gray[y0:y1, x0:x1]
            if use_8:
                mat[row, col] = classify_orientation_8(cell)
            else:
                mat[row, col] = classify_orientation_4(cell)
    return mat


def rotate_matrix_90(mat: np.ndarray, k: int) -> np.ndarray:
    """Rotate matrix by k*90 degrees (k=0,1,2,3)."""
    return np.rot90(mat, k=-k % 4)


def matrix_to_color_image(mat: np.ndarray, direction_to_color: list[int], module_pixels: int = 12) -> np.ndarray:
    """
    Convert orientation matrix to RGB image using direction->color mapping.
    direction_to_color[i] = JAB palette index for direction i.
    """
    h, w = mat.shape
    out = np.zeros((h * module_pixels, w * module_pixels, 3), dtype=np.uint8)
    for r in range(h):
        for c in range(w):
            idx = mat[r, c] % len(direction_to_color)
            pal_idx = direction_to_color[idx]
            color = JAB_PALETTE_RGB[pal_idx % 8]
            out[r * module_pixels:(r + 1) * module_pixels,
                c * module_pixels:(c + 1) * module_pixels] = color
    return out


def main() -> None:
    if cv2 is None:
        print("Install opencv-python: pip install opencv-python", file=sys.stderr)
        sys.exit(1)

    # Allow override via env or argument
    img_path = Path(os.environ.get("JAB_COIN_IMAGE", str(COIN_IMAGE_PATH)))
    if len(sys.argv) > 1:
        img_path = Path(sys.argv[1])

    if not img_path.exists():
        print("Image not found:", img_path, file=sys.stderr)
        print("Usage: python jab_coin_decode.py [path/to/coin_image.png]", file=sys.stderr)
        print("Or set JAB_COIN_IMAGE to the coin image path.", file=sys.stderr)
        if "--demo" in sys.argv:
            print("Running in --demo mode with synthetic 21×21 grid.", file=sys.stderr)
            img = np.zeros((400, 400, 3), dtype=np.uint8)
            img[:] = (240, 240, 240)
            rng = np.random.default_rng(42)
            for i in range(GRID_SIZE):
                for j in range(GRID_SIZE):
                    cx = 80 + j * (240 // GRID_SIZE)
                    cy = 80 + i * (240 // GRID_SIZE)
                    # Synthetic "orientation" 0-3
                    o = rng.integers(0, 4)
                    if o == 0:
                        cv2.arrowedLine(img, (cx - 5, cy), (cx + 5, cy), (0, 0, 0), 1)
                    elif o == 1:
                        cv2.arrowedLine(img, (cx, cy - 5), (cx, cy + 5), (0, 0, 0), 1)
                    elif o == 2:
                        cv2.arrowedLine(img, (cx + 5, cy), (cx - 5, cy), (0, 0, 0), 1)
                    else:
                        cv2.arrowedLine(img, (cx, cy + 5), (cx, cy - 5), (0, 0, 0), 1)
        else:
            sys.exit(1)
    else:
        print("Loading image:", img_path)
        img = load_image(img_path)

    print("Building 21×21 orientation matrix (4 directions)...")
    mat4 = build_orientation_matrix(img, GRID_SIZE, use_8=False)
    print("Building 21×21 orientation matrix (8 directions)...")
    mat8 = build_orientation_matrix(img, GRID_SIZE, use_8=True)

    out_dir = SCRIPT_DIR / "jab_output"
    out_dir.mkdir(exist_ok=True)

    # Save raw matrices for inspection
    np.savetxt(out_dir / "matrix_4dir.csv", mat4, fmt="%d", delimiter=",")
    np.savetxt(out_dir / "matrix_8dir.csv", mat8, fmt="%d", delimiter=",")
    print("Saved matrix_4dir.csv and matrix_8dir.csv to", out_dir)

    # 4-color: try identity and a few permutations; 4 rotations
    # JAB 4-color palette indices for data: 0,3,5,6 (K,C,M,Y) typical
    base_map_4 = [0, 3, 5, 6]
    for rot in range(4):
        M = rotate_matrix_90(mat4, rot)
        for perm_idx, perm in enumerate(itertools.permutations(range(4))):
            direction_to_color = [base_map_4[perm[i]] for i in range(4)]
            rgb = matrix_to_color_image(M, direction_to_color, module_pixels=12)
            if Image is not None:
                out_path = out_dir / f"jab_4dir_rot{rot}_perm{perm_idx}.png"
                Image.fromarray(rgb).save(out_path)
    print("Generated 4-direction candidate images (24 files = 4 rotations × 6 permutations) in", out_dir)

    # 8-color: try identity mapping and 2 rotations to limit count
    base_map_8 = list(range(8))
    for rot in range(4):
        M = rotate_matrix_90(mat8, rot)
        direction_to_color = base_map_8
        rgb = matrix_to_color_image(M, direction_to_color, module_pixels=12)
        if Image is not None:
            out_path = out_dir / f"jab_8dir_rot{rot}.png"
            Image.fromarray(rgb).save(out_path)
    print("Generated 8-direction candidate images (4 rotations) in", out_dir)

    print("\n--- Next steps ---")
    print("1. Open https://jabcode.org/scan and try uploading images from jab_output/")
    print("2. JAB codes have finder patterns in the corners; this script outputs data modules only.")
    print("   If the scanner does not accept these, use the C reader and feed a bitmap, or add finder patterns.")
    print("3. Try different rotations (rot0..rot3) and permutations (4dir) to brute-force the correct orientation.")
    print("4. Possible answers: the decoded payload is typically a URL (hidden link) for the bug bounty challenge.")


if __name__ == "__main__":
    main()
