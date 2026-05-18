from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from backend.ml_predictor import (  # noqa: E402
    METADATA_PATH,
    METRICS_PATH,
    train_and_save_models,
)


def main():
    metadata = train_and_save_models()
    print("Predictive ML models trained successfully.")
    print(metadata)
    print(f"Metadata saved to: {METADATA_PATH}")
    print(f"Metrics saved to: {METRICS_PATH}")


if __name__ == "__main__":
    main()
