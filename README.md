# How the URL "https://www.sit.fraunhofer.de/" Comes From the 21×21 Matrix

This document explains how the first decoded solution **https://www.sit.fraunhofer.de/** is derived from the 21×21 orientation matrix extracted from the Intigriti bug bounty coin.

## special mention to reddit group:
https://www.reddit.com/r/Defcon/comments/1mr4ptk/bug_bounty_coin_solution/n8vhfo0/

## AI prompt
```
build a JAB 21×21 matrix from this image. use a JAB Code decoder (jabcode.org) to decode it. list possible answers

other people have given this tip:

Understanding the Challenge
Complexity: The challenge is designed to be difficult, with one Redditor mentioning that it took 3 hours and spreadsheets to solve. "When I spoke the guy that was handing them out on Saturday, he said 5 people solved it. The last guy that solved it, took 3 hours and spreadsheets to figure it out."
Matrix and Codes: Another Redditor explained that the solution involves a 21x21 matrix where each bee points in a specific direction. You need to map these directions, create the matrix, and then brute force the correct orientation and number for each bee using a protocol jab code. "It’s a 21x21 matrix each bee it’s pointing to a specific direction, you need to map each one? Then create the matrix its use a porotcol jab code, you need to brute force witch is the correrct orentation and correct number for each bee, then solve it."
Clues and Tips
Distortion Shape: The shape of the distortion on the back of the coin is a clue. "The shape of the distortion on the back is a clue."
Not a QR Code: Despite initial appearances, it is not a QR code. "Different thing than a QR code. You're right that the decoder ring on the other side is not part of the challenge."
Company Logo: The dots on the coin are actually the company logo from the front in different orientations. "So if you look REAL close the dots are actually the company logo from the front in different positions of orientation (right side up, up side down, etc)."
Additional Resources
OCR and Unknown Symbols: The challenge involves optical character recognition (OCR) of unknown symbols. "Woot got it solved! But it looks like the challenge ended on the 12th. Still a fun puzzle and a good way to waste some time learning OCR of unknown symbols."
```

```
send each png in @jab_output to https://jabcode.org/scan/ to see if there is an URL. continue until we find the url. stop when there is one url
```

```
keep scanning all 100 files. give me all urls
```

---

## Pipeline Overview

```
Coin image (bees in different directions)
    → Extract 21×21 grid, classify each cell’s orientation (0–3)
    → 21×21 matrix of direction indices (matrix_4dir.csv)
    → Map each direction to a JAB color (with rotation + permutation)
    → Raster image of colored modules (e.g. jab_4dir_rot0_perm0.png)
    → JAB Code decoder
    → Payload bytes (UTF-8)
    → URL string: https://www.sit.fraunhofer.de/
```

---

## 1. The 21×21 Matrix

- The coin has a **circular grid of “bees”** (logo symbols) in different orientations.
- Each cell is classified into **4 directions**: `0` = up, `1` = right, `2` = down, `3` = left.
- These values are stored in a **21×21 matrix** (e.g. `jab_output/matrix_4dir.csv`).

**Example — first 5×5 of the matrix (rows 0–4, cols 0–4):**

|     | 0 | 1 | 2 | 3 | 4 |
|-----|---|---|---|---|---|
| **0** | 2 | 3 | 1 | 0 | 3 |
| **1** | 3 | 3 | 2 | 3 | 3 |
| **2** | 0 | 0 | 0 | 0 | 3 |
| **3** | 0 | 0 | 3 | 1 | 2 |
| **4** | 0 | 3 | 0 | 1 | 0 |

So for example:
- Cell (0,0) has value **2** → bee in that cell points **down**.
- Cell (0,3) has value **0** → bee points **up**.

---

## 2. Matrix Value → JAB Module Color

The matrix does not directly store characters. Each cell is **one module** of a JAB Code. The value in the cell (0–3) is mapped to a **color** using the JAB 4‑color palette (e.g. K, C, M, Y):

- **Direction index** (0, 1, 2, 3) is mapped to a **palette index** (e.g. 0, 3, 5, 6 for Black, Cyan, Magenta, Yellow).
- The mapping depends on **rotation** (which way the grid is oriented) and **permutation** (which direction corresponds to which color). The script tries 4 rotations × 24 permutations until one produces a decodable JAB image.

**Example mapping (one of the 24 permutations):**

| Matrix value (direction) | Palette index | Color   |
|--------------------------|---------------|---------|
| 0                        | 0             | Black   |
| 1                        | 3             | Cyan    |
| 2                        | 5             | Magenta |
| 3                        | 6             | Yellow  |

So the same 5×5 block might become:

- (0,0)=2 → **Magenta**, (0,1)=3 → **Yellow**, (0,2)=1 → **Cyan**, (0,3)=0 → **Black**, (0,4)=3 → **Yellow**
- etc.

Each matrix cell becomes **one colored square** (one “module”) in the image you upload to [jabcode.org/scan](https://jabcode.org/scan).

---

## 3. How the Matrix Becomes Each Character (Conceptually)

- The **21×21 grid = 441 modules**. In 4‑color JAB, each module encodes **2 bits**.
- The JAB decoder:
  1. Reads modules in the order defined by the JAB spec (including finder pattern, data/EC layout).
  2. Converts each module’s color to 2 bits.
  3. Assembles the bit stream, de-interleaves, applies error correction, and recovers the **payload bytes**.
- The payload is **UTF-8 text** — in our case the string `https://www.sit.fraunhofer.de/`.

So “matrix becomes each character” works like this:

- **Not** one cell = one character. Many modules together form the bit stream that decodes to the whole URL.
- **Example for the first character `h`:**
  - `h` in UTF-8 is the byte `0x68` = binary `01101000` (8 bits).
  - In 4‑color JAB, 8 bits need **4 modules** (4 × 2 bits).
  - So the first 4 modules (in the spec’s reading order) contribute the 8 bits that become the byte `0x68` → character `h`.
  - The next modules similarly form the bytes for `t`, `t`, `p`, `:`, `/`, `/`, etc., until the full URL is reconstructed.

**Simplified example:**

| Step | What happens |
|------|-------------------------------|
| 1 | Matrix cell (r,c) has value v ∈ {0,1,2,3}. |
| 2 | With the correct rotation/permutation, v → color → 2 bits (e.g. 0→00, 1→01, 2→10, 3→11). |
| 3 | Decoder reads all 441 modules in JAB order → long bit string. |
| 4 | Bit string is de-interleaved and error-corrected → payload bytes. |
| 5 | Payload bytes = UTF-8 of `https://www.sit.fraunhofer.de/`. |

So the **first few modules** (after finder/format in the spec) give the first bits of the payload and thus the first bytes of the URL (e.g. `h`), and the rest of the matrix fills in the remaining characters.

---

## 4. Minimal Example: A Few Cells → One Byte

Suppose (in JAB reading order) four consecutive data modules have direction indices **2, 1, 0, 2** and the permutation maps:

- 0 → 00  
- 1 → 01  
- 2 → 10  
- 3 → 11  

Then those four modules yield:

- 2 → **10**  
- 1 → **01**  
- 0 → **00**  
- 2 → **10**  

Concatenated: `10010010` → byte `0x92` (this is just an example; the real first byte is `0x68` for `h`).

So:

- **Matrix** = 21×21 numbers in {0,1,2,3}.  
- **Colors** = each number mapped to a JAB color (2 bits per module).  
- **Bits** = stream of 2‑bit values from all modules in JAB order.  
- **Bytes** = after de-interleave and EC, the payload.  
- **Characters** = payload interpreted as UTF-8 → `https://www.sit.fraunhofer.de/`.

---

## 5. Summary

| Stage | What you have |
|-------|-------------------------------|
| Coin | Bees in different directions. |
| Matrix | 21×21 integers 0–3 (direction per cell). |
| Image | 21×21 colored modules (one color per cell). |
| Decoder | Reads modules → bits → bytes → UTF-8 string. |
| Result | **https://www.sit.fraunhofer.de/** |

The “solution” URL is the payload recovered by the JAB decoder from the 21×21 grid of colors that comes from the 21×21 matrix of bee directions, with the correct rotation and direction→color mapping (e.g. as in `jab_4dir_rot0_perm0.png` or another candidate that decodes successfully at [jabcode.org/scan](https://jabcode.org/scan)).
