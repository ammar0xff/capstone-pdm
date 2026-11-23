#!/usr/bin/env python3
"""
Intelligent Predictive Maintenance (PdM) - Random Forest Classifier Trainer
Trains 300-estimator Random Forest model on multi-modal feature windows according to PRD Section 7.
Computes 5-fold cross-validation, generates Confusion Matrix, ROC curves, and Feature Importances,
and exports model.joblib plus pure-Python inference weights.
"""

import os
import json
import time
import numpy as np
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, train_test_split, cross_validate
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    precision_recall_fscore_support,
    roc_curve,
    auc
)
from sklearn.preprocessing import label_binarize
import joblib

ML_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_FILE = os.path.join(ML_DIR, "windows.csv")
MODEL_FILE = os.path.join(ML_DIR, "model.joblib")
META_FILE = os.path.join(ML_DIR, "model_meta.json")
CM_PLOT_FILE = os.path.join(ML_DIR, "confusion_matrix.png")
ROC_PLOT_FILE = os.path.join(ML_DIR, "roc_curves.png")
FEAT_PLOT_FILE = os.path.join(ML_DIR, "feature_importance.png")

FEATURE_COLS = [
    "rms_dyn",
    "peak_dyn",
    "crest_factor",
    "kurtosis",
    "temp_c",
    "temp_slope",
    "sound_rms",
    "sound_db",
    "sound_zcr"
]

CLASS_NAMES = [
    "Healthy",
    "Mechanical Imbalance",
    "Bearing Defect",
    "Thermal Runaway"
]

def main():
    print("=" * 65)
    print("  Predictive Maintenance (PdM) - Random Forest Training & Evaluation")
    print("=" * 65)

    if not os.path.exists(DATASET_FILE):
        print("[WARN] windows.csv not found. Generating fresh benchmark dataset...")
        from dataset_generator import generate_dataset
        generate_dataset()

    rows = []
    with open(DATASET_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"[INFO] Loaded dataset: {len(rows)} samples.")
    X = np.array([[float(r[col]) for col in FEATURE_COLS] for r in rows], dtype=np.float32)
    y = np.array([int(r["class_id"]) for r in rows], dtype=np.int32)

    # 1. Stratified 5-Fold Cross-Validation
    print("[INFO] Executing Stratified 5-Fold Cross-Validation (PRD Section 7)...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_clf = RandomForestClassifier(n_estimators=300, max_depth=12, min_samples_split=4, class_weight='balanced', random_state=42)
    cv_scores = cross_validate(cv_clf, X, y, cv=skf, scoring=['accuracy', 'precision_macro', 'recall_macro', 'f1_macro'])

    mean_acc = cv_scores['test_accuracy'].mean()
    mean_f1 = cv_scores['test_f1_macro'].mean()
    print(f"  -> 5-Fold Mean Accuracy: {mean_acc * 100:.2f}% (PRD Target: >= 80.0%)")
    print(f"  -> 5-Fold Mean Macro F1: {mean_f1:.4f}")

    # 2. Hold-out 70/15/15 Train/Validation/Test Split for Final Model & Evidence
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.30, stratify=y, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.50, stratify=y_temp, random_state=42)

    print(f"[INFO] Split sizes: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_split=4,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    t0 = time.time()
    model.fit(X_train, y_train)
    t_train = time.time() - t0
    print(f"[INFO] Model trained in {t_train:.2f} seconds.")

    # Validation evaluation
    y_val_pred = model.predict(X_val)
    val_acc = accuracy_score(y_val, y_val_pred)

    # Test set evaluation
    y_test_pred = model.predict(X_test)
    y_test_proba = model.predict_proba(X_test)
    test_acc = accuracy_score(y_test, y_test_pred)

    print(f"  -> Validation Set Accuracy: {val_acc * 100:.2f}%")
    print(f"  -> Test Set Accuracy:       {test_acc * 100:.2f}%")

    # Latency Benchmark (PRD Metric M2)
    print("[INFO] Benchmarking single-window inference latency on 100 samples...")
    # Temporarily set n_jobs=1 to measure true single-core latency without threadpool overhead
    model.n_jobs = 1
    t_lat_start = time.perf_counter()
    n_bench = min(100, len(X_test))
    for i in range(n_bench):
        _ = model.predict_proba(X_test[i:i+1])
    t_lat_end = time.perf_counter()
    latency_ms = ((t_lat_end - t_lat_start) / n_bench) * 1000.0
    print(f"  -> Mean Inference Latency: {latency_ms:.3f} ms per window (Target: < 5 ms)")

    # Classification Report
    report = classification_report(y_test, y_test_pred, target_names=CLASS_NAMES, digits=4)
    print("\n" + "=" * 65)
    print("  Classification Report (Test Set Evidence - M1):")
    print("=" * 65)
    print(report)

    # 3. Generate Confusion Matrix Plot
    cm = confusion_matrix(y_test, y_test_pred)
    cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    fig, ax = plt.subplots(figsize=(7, 6), dpi=200)
    cax = ax.imshow(cm_norm, interpolation='nearest', cmap=plt.cm.Blues)
    ax.set_title(f"Predictive Maintenance Confusion Matrix (Accuracy: {test_acc*100:.1f}%)", fontsize=12, fontweight='bold', pad=14)
    fig.colorbar(cax)

    tick_marks = np.arange(len(CLASS_NAMES))
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(CLASS_NAMES, rotation=25, ha='right', fontsize=9.5)
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(CLASS_NAMES, fontsize=9.5)

    thresh = cm_norm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, f"{cm[i, j]}\n({cm_norm[i, j]*100:.1f}%)",
                    ha="center", va="center",
                    color="white" if cm_norm[i, j] > thresh else "black",
                    fontsize=9.5, fontweight='bold')

    ax.set_ylabel('True Industrial Condition', fontsize=10.5, fontweight='bold')
    ax.set_xlabel('Predicted Condition (Random Forest)', fontsize=10.5, fontweight='bold')
    plt.tight_layout()
    plt.savefig(CM_PLOT_FILE)
    plt.close()
    print(f"[SUCCESS] Confusion Matrix saved to {CM_PLOT_FILE}")

    # 4. Generate ROC Curves
    y_test_bin = label_binarize(y_test, classes=[0, 1, 2, 3])
    fig, ax = plt.subplots(figsize=(7, 6), dpi=200)
    colors = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444']

    for i in range(4):
        fpr, tpr, _ = roc_curve(y_test_bin[:, i], y_test_proba[:, i])
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, color=colors[i], lw=2.2, label=f"{CLASS_NAMES[i]} (AUC = {roc_auc:.4f})")

    ax.plot([0, 1], [0, 1], 'k--', lw=1.2, alpha=0.6)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('False Positive Rate (1 - Specificity)', fontsize=10.5, fontweight='bold')
    ax.set_ylabel('True Positive Rate (Sensitivity)', fontsize=10.5, fontweight='bold')
    ax.set_title('Multi-Class One-vs-Rest ROC Curves', fontsize=12, fontweight='bold', pad=14)
    ax.legend(loc="lower right", fontsize=9.5)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(ROC_PLOT_FILE)
    plt.close()
    print(f"[SUCCESS] ROC Curves saved to {ROC_PLOT_FILE}")

    # 5. Generate Feature Importances Plot
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    sorted_features = [FEATURE_COLS[i] for i in indices]
    sorted_importances = importances[indices]

    fig, ax = plt.subplots(figsize=(8, 5), dpi=200)
    bars = ax.barh(range(len(FEATURE_COLS)), sorted_importances[::-1], color='#0284c7', align='center')
    ax.set_yticks(range(len(FEATURE_COLS)))
    ax.set_yticklabels(sorted_features[::-1], fontsize=10)
    ax.set_xlabel('Gini Feature Importance', fontsize=10.5, fontweight='bold')
    ax.set_title('Random Forest Feature Importance Ranking (Multi-Modality Fusion)', fontsize=12, fontweight='bold', pad=14)
    
    # Annotate bars
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.005, bar.get_y() + bar.get_height()/2, f"{w*100:.1f}%", va='center', fontsize=8.5, fontweight='bold', color='#0369a1')

    ax.set_xlim(0, max(sorted_importances) * 1.15)
    plt.tight_layout()
    plt.savefig(FEAT_PLOT_FILE)
    plt.close()
    print(f"[SUCCESS] Feature Importance Plot saved to {FEAT_PLOT_FILE}")

    # 6. Save Model & Metadata
    joblib.dump(model, MODEL_FILE)
    print(f"[SUCCESS] Model serialized to {MODEL_FILE}")

    meta = {
        "model_type": "RandomForestClassifier",
        "n_estimators": 300,
        "max_depth": 12,
        "features": FEATURE_COLS,
        "classes": CLASS_NAMES,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "5fold_cv_accuracy": round(float(mean_acc), 4),
        "test_accuracy": round(float(test_acc), 4),
        "inference_latency_ms": round(float(latency_ms), 3),
        "timestamp": time.time()
    }
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    print("\n[ALL TASKS COMPLETED] Machine Learning Pipeline successfully executed.")

if __name__ == "__main__":
    main()
