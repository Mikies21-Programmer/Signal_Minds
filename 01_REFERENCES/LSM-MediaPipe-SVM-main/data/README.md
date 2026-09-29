# Data folder

The extracted features file (`landmarks_dataset.csv`, 336 MB) is **not included** in this repository due to GitHub's file size limit (25 MB).

## How to regenerate it

1. Download the original dataset from Zenodo:
   https://doi.org/10.5281/zenodo.6554337

2. Extract the dataset to this folder.

3. Run the extraction script from the repository root:

python src/extract_landmarks.py --data-dir ./data --output ./data/landmarks_dataset.csv

This will generate `landmarks_dataset.csv` with 276,152 rows (21 LSM letters, 63 features each).

## Dataset details

- **Source:** Chacon Quintero, A. et al. (2022). *Dataset LSM Lenguaje de señas mexicanas*. Zenodo.
- **DOI:** [10.5281/zenodo.6554337](https://doi.org/10.5281/zenodo.6554337)
- **License:** CC BY 4.0
- **Total images:** 276,152
- **Letters:** A, B, C, D, E, F, G, H, I, L, M, N, O, P, R, S, T, U, V, W, Y
- **Excluded:** J, K, Z (require motion) and Q, X, Ñ (high visual similarity)
