"""
Train a Gradient Boosting Regressor to predict apparent temperature (°C)
from the Szeged Weather 2006-2016 dataset.

Usage:
    # First download the dataset:
    python data/download_data.py

    # Then train:
    python train.py

Outputs:
    model_v1.0.0.pkl  - versioned model artifact (joblib)
    metrics.json      - RMSE, MAE, R² on the 20% hold-out test set
"""

import json
import os
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RANDOM_SEED = 42
MODEL_VERSION = "1.0.0"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MODEL_PATH = os.path.join(os.path.dirname(__file__), f"model_v{MODEL_VERSION}.pkl")
METRICS_PATH = os.path.join(os.path.dirname(__file__), "metrics.json")

FEATURE_COLS = [
    "humidity",
    "wind_speed_kmh",
    "wind_bearing_deg",
    "visibility_km",
    "pressure_mb",
    "is_rain",
]
TARGET_COL = "apparent_temperature_c"


def load_data(data_dir: str) -> pd.DataFrame:
    full_path = os.path.join(data_dir, "weather_full.csv")
    sample_path = os.path.join(data_dir, "sample_weather.csv")

    if os.path.exists(full_path):
        print(f"Loading full dataset from {full_path}")
        df = pd.read_csv(full_path)
    else:
        print(f"Full dataset not found. Using sample ({sample_path}).")
        print("Run `python data/download_data.py` to get the full dataset.")
        df = pd.read_csv(sample_path)

    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {
        "Humidity": "humidity",
        "Wind Speed (km/h)": "wind_speed_kmh",
        "Wind Bearing (degrees)": "wind_bearing_deg",
        "Visibility (km)": "visibility_km",
        "Pressure (millibars)": "pressure_mb",
        "Apparent Temperature (C)": "apparent_temperature_c",
        "Precip Type": "precip_type",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    df["is_rain"] = (df.get("precip_type", "null") == "rain").astype(int)

    required = FEATURE_COLS + [TARGET_COL]
    df = df[required].dropna()

    # Remove physically impossible pressure readings
    df = df[df["pressure_mb"] > 900]

    return df.reset_index(drop=True)


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("model", GradientBoostingRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            random_state=RANDOM_SEED,
        )),
    ])


def evaluate(model, X_test, y_test) -> dict:
    y_pred = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mae = float(mean_absolute_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))
    return {"rmse": round(rmse, 4), "mae": round(mae, 4), "r2": round(r2, 4)}


def main():
    df = load_data(DATA_DIR)
    df = preprocess(df)
    print(f"Dataset shape after preprocessing: {df.shape}")

    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED
    )
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")

    pipeline = build_pipeline()
    t0 = time.time()
    pipeline.fit(X_train, y_train)
    train_time = round(time.time() - t0, 2)
    print(f"Training complete in {train_time}s")

    metrics = evaluate(pipeline, X_test, y_test)
    metrics["model_version"] = MODEL_VERSION
    metrics["train_samples"] = len(X_train)
    metrics["test_samples"] = len(X_test)
    metrics["training_time_s"] = train_time
    metrics["feature_columns"] = FEATURE_COLS
    metrics["target_column"] = TARGET_COL

    print(f"RMSE : {metrics['rmse']} °C")
    print(f"MAE  : {metrics['mae']} °C")
    print(f"R²   : {metrics['r2']}")

    joblib.dump(pipeline, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to {METRICS_PATH}")


if __name__ == "__main__":
    main()
