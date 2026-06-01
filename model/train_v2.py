"""
Train model v2.0.0 - RandomForestRegressor for A/B testing against v1 (GBR).

v1: GradientBoostingRegressor  - RMSE 0.087 C, R2 0.9999, ~454 trees
v2: RandomForestRegressor       - Different algorithm, compare latency + accuracy in KQL

Usage:
    python train_v2.py

Outputs:
    model_v2.0.0.pkl  - versioned v2 model artifact (joblib)
    metrics_v2.json   - metrics for comparison with v1
"""

import json
import math
import os
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RANDOM_SEED = 42
MODEL_VERSION = "2.0.0"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MODEL_PATH = os.path.join(os.path.dirname(__file__), f"model_v{MODEL_VERSION}.pkl")
METRICS_PATH = os.path.join(os.path.dirname(__file__), "metrics_v2.json")

FEATURE_COLS = [
    "temperature_c",
    "humidity",
    "wind_speed_kmh",
    "wind_bearing_sin",
    "wind_bearing_cos",
    "visibility_km",
    "pressure_mb",
    "is_rain",
    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos",
]
TARGET_COL = "apparent_temperature_c"


def load_and_preprocess(data_dir: str) -> pd.DataFrame:
    full_path = os.path.join(data_dir, "weather_full.csv")
    sample_path = os.path.join(data_dir, "sample_weather.csv")
    df = pd.read_csv(full_path if os.path.exists(full_path) else sample_path)

    col_map = {
        "Temperature (C)": "temperature_c",
        "Apparent Temperature (C)": "apparent_temperature_c",
        "Humidity": "humidity",
        "Wind Speed (km/h)": "wind_speed_kmh",
        "Wind Bearing (degrees)": "wind_bearing_deg",
        "Visibility (km)": "visibility_km",
        "Pressure (millibars)": "pressure_mb",
        "Precip Type": "precip_type",
        "Formatted Date": "date",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    df["is_rain"] = (df.get("precip_type", "null") == "rain").astype(int)
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df["hour"] = df["date"].dt.hour
    df["month"] = df["date"].dt.month
    df["hour_sin"]         = df["hour"].apply(lambda h: math.sin(2 * math.pi * h / 24))
    df["hour_cos"]         = df["hour"].apply(lambda h: math.cos(2 * math.pi * h / 24))
    df["month_sin"]        = df["month"].apply(lambda m: math.sin(2 * math.pi * m / 12))
    df["month_cos"]        = df["month"].apply(lambda m: math.cos(2 * math.pi * m / 12))
    df["wind_bearing_sin"] = df["wind_bearing_deg"].apply(lambda d: math.sin(math.radians(d)))
    df["wind_bearing_cos"] = df["wind_bearing_deg"].apply(lambda d: math.cos(math.radians(d)))

    df = df[FEATURE_COLS + [TARGET_COL]].dropna()
    return df[df["pressure_mb"] > 900].reset_index(drop=True)


def main():
    df = load_and_preprocess(DATA_DIR)
    print(f"Dataset: {df.shape}")

    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED
    )
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", RandomForestRegressor(
            n_estimators=300,
            max_depth=15,
            min_samples_leaf=5,
            max_features=0.6,
            n_jobs=-1,
            random_state=RANDOM_SEED,
        )),
    ])

    t0 = time.time()
    pipeline.fit(X_train, y_train)
    train_time = round(time.time() - t0, 2)

    y_pred = pipeline.predict(X_test)
    metrics = {
        "model_version": MODEL_VERSION,
        "algorithm": "RandomForestRegressor",
        "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4),
        "mae":  round(float(mean_absolute_error(y_test, y_pred)), 4),
        "r2":   round(float(r2_score(y_test, y_pred)), 4),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "training_time_s": train_time,
        "feature_columns": FEATURE_COLS,
        "n_estimators": 300,
    }
    print(f"RMSE : {metrics['rmse']} C")
    print(f"MAE  : {metrics['mae']} C")
    print(f"R2   : {metrics['r2']}")
    print(f"Time : {train_time}s")

    joblib.dump(pipeline, MODEL_PATH)
    print(f"Model saved -> {MODEL_PATH}")
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved -> {METRICS_PATH}")


if __name__ == "__main__":
    main()
