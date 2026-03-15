# JAB 21×21 Matrix from Intigriti Bug Bounty Coin

This folder contains a pipeline to build a **21×21 JAB-style matrix** from the coin image and attempt decoding.

## Summary

- **Challenge:** The coin has a circular grid of “bees” (company logo) in different orientations. You must map each bee’s **direction** to a symbol value, build the **21×21 matrix**, then decode it as a **JAB Code** (protocol from [jabcode.org](https://jabcode.org)).
- **Tips from solvers:**
  - 21×21 matrix; each bee points in a specific direction.
  - Map each bee → direction, build the matrix, then use JAB code and **brute-force** the correct **orientation** (rotation) and **mapping** (direction → color/number) for each bee.
  - The **shape of the distortion on the back** of the coin is a clue.
  - The “dots” are the **company logo in different orientations** (right side up, upside down, etc.), not a QR code.

## 1. Build the 21×21 matrix from the image

### Dependencies

```bash
pip install -r requirements-jab.txt
# or: pip install numpy opencv-python pillow
```

### Run

- With your coin image:

  ```bash
  python jab_coin_decode.py /path/to/coin_image.png
  ```

- Or set the path via env:

  ```bash
  export JAB_COIN_IMAGE=/path/to/coin_image.png
  python jab_coin_decode.py
  ```

- Demo (synthetic grid, no image file):

  ```bash
  python jab_coin_decode.py --demo
  ```

### Outputs (in `jab_output/`)

- **matrix_4dir.csv**, **matrix_8dir.csv** – 21×21 matrices of orientation indices (4 or 8 directions per cell).
- **jab_4dir_rot{N}_perm{P}.png** – Candidate images for 4-direction mapping (4 rotations × 6 permutations = 24 images).
- **jab_8dir_rot{N}.png** – Candidate images for 8-direction mapping (4 rotations).

## 2. Decode with a JAB Code decoder

### Option A: Browser (jabcode.org)

1. Open **[https://jabcode.org/scan](https://jabcode.org/scan)**.
2. Upload one of the generated images from `jab_output/`.
3. Try different **rotations** (`rot0`–`rot3`) and **permutations** (4dir only) until one decodes.

Note: Standard JAB symbols include **finder patterns** in the corners. The script outputs **data modules only** (colored squares from bee orientations). If the web decoder does not accept these, use the C reader (Option B) or add finder patterns according to the [JAB specification](https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/Publications/TechGuidelines/TR03137/BSI-TR-03137_Part2.html).

### Option B: C reader (jabcode repo)

1. Clone and build: [https://github.com/jabcode/jabcode](https://github.com/jabcode/jabcode).
2. Build the reader (see repo README), then run it on a generated image, e.g.:

   ```bash
   jabcodeReader path/to/jab_output/jab_4dir_rot0_perm0.png
   ```

3. Try multiple rotation/permutation images until one decodes.

## 3. Possible answers

Decoded content is typically:

- A **URL** (the “hidden link” for the bug bounty).
- Possibly a **text message** or **identifier** for the challenge.

Because the correct **grid rotation** and **direction→symbol mapping** are unknown, you need to try:

- **4 rotations** of the 21×21 grid (0°, 90°, 180°, 270°).
- **4-direction mapping:** 4! = **24** permutations of which direction (up/right/down/left) corresponds to which JAB color/index.
- **8-direction mapping:** 8! permutations (many); often only a few rotations are tried first (e.g. rot0–rot3 in the script).

So **possible answers** are:

1. **One of the decoded payloads** from the candidate images that successfully decodes in the JAB scanner/reader – usually a **single hidden URL** (or short text).
2. If the challenge has ended (e.g. by 12th), the link may no longer be valid, but the **decoded string** (URL or text) is still the “answer” to the puzzle.

## 4. Quick reference

| What                | Where / How |
|---------------------|-------------|
| JAB spec            | [BSI TR-03137 Part 2](https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/Publications/TechGuidelines/TR03137/BSI-TR-03137_Part2.html), [ISO/IEC 23634](https://www.iso.org/standard/76478.html) |
| Online scan          | [jabcode.org/scan](https://jabcode.org/scan) |
| Create JAB          | [jabcode.org/create](https://jabcode.org/create) |
| C library & reader   | [github.com/jabcode/jabcode](https://github.com/jabcode/jabcode) |
| 21×21               | Primary symbol version 1: size = 17 + 4×version → 21 |

## 5. Matrix interpretation

- **4 directions:** Up / Right / Down / Left → mapped to 4 JAB colors (e.g. palette indices 0, 3, 5, 6 for K, C, M, Y).
- **8 directions:** Same idea with 8 orientations → 8 colors for higher capacity.
- **Brute force:** Try all rotations and (for 4dir) all permutations of direction→color; one combination should yield a valid JAB decode and the hidden link (or other answer).
