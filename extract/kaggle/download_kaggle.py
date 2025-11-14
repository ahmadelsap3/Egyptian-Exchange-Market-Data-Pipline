#!/usr/bin/env python3
"""Download Kaggle dataset files into a local folder.

Usage:
    python extract/kaggle/download_kaggle.py --dataset saurabhshahane/egyptian-stock-exchange --outdir extract/kaggle/raw

This script is a small wrapper around the kaggle API (python package). It expects the
`KAGGLE_USERNAME` and `KAGGLE_KEY` to be available in the environment or via the
~/.kaggle/kaggle.json configuration.
"""
import argparse
import os
from kaggle.api.kaggle_api_extended import KaggleApi


def download_dataset(dataset: str, outdir: str):
    api = KaggleApi()
    api.authenticate()
    os.makedirs(outdir, exist_ok=True)
    print(f"Downloading {dataset} into {outdir} ...")
    api.dataset_download_files(dataset, path=outdir, unzip=True, quiet=False)
    print("Download complete.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Kaggle dataset (owner/dataset-name)")
    parser.add_argument("--outdir", required=True, help="Output directory")
    args = parser.parse_args()
    download_dataset(args.dataset, args.outdir)


if __name__ == "__main__":
    main()
