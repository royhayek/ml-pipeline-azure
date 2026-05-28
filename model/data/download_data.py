"""
Download the Szeged weather dataset from Kaggle.

Requires a valid ~/.kaggle/kaggle.json API token.
See: https://www.kaggle.com/docs/api#authentication

Usage:
    pip install kaggle
    python download_data.py
"""
import subprocess
import os

DATASET = "budincsevity/szeged-weather"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    print(f"Downloading '{DATASET}' via Kaggle CLI ...")
    subprocess.run(
        ["kaggle", "datasets", "download", "-d", DATASET, "-p", OUT_DIR, "--unzip"],
        check=True,
    )
    # The downloaded file is 'weatherHistory.csv'
    src = os.path.join(OUT_DIR, "weatherHistory.csv")
    dst = os.path.join(OUT_DIR, "weather_full.csv")
    if os.path.exists(src):
        os.rename(src, dst)
        print(f"Saved to {dst}")
    else:
        print("Download complete. Check the output directory for the CSV file.")


if __name__ == "__main__":
    main()
