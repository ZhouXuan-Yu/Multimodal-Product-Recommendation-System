#!/usr/bin/env python3
"""
Export high-resolution figures for thesis from training outputs.
Generates:
 - t-SNE of fused product features
 - GPU usage time series
 - Model file sizes bar chart
Saved to ./figures/
"""
from pathlib import Path
import pickle
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.manifold import TSNE
import os

OUTDIR = Path("figures")
OUTDIR.mkdir(exist_ok=True)

def load_fused(path: Path):
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)

def plot_tsne(fused_features, outpath: Path, max_points=200, dpi=300):
    keys = list(fused_features.keys())
    n = min(len(keys), max_points)
    sel = keys[:n]
    X = np.array([fused_features[k] for k in sel])
    if X.shape[0] < 3:
        print("Not enough points for t-SNE (need >=3)")
        return
    # choose perplexity smaller than n_samples
    perplexity = min(30, max(2, n//3))
    if perplexity >= X.shape[0]:
        perplexity = max(2, X.shape[0] // 2)
    tsne = TSNE(n_components=2, random_state=42, perplexity=perplexity)
    X2 = tsne.fit_transform(X)
    plt.figure(figsize=(8,8))
    sc = plt.scatter(X2[:,0], X2[:,1], c=np.arange(n), cmap="viridis", s=30, alpha=0.8, edgecolors='w', linewidths=0.3)
    plt.title("Product feature distribution (t-SNE)")
    plt.xlabel("t-SNE 1")
    plt.ylabel("t-SNE 2")
    plt.colorbar(sc, label="product index")
    plt.tight_layout()
    plt.savefig(outpath.with_suffix(".png"), dpi=dpi)
    plt.savefig(outpath.with_suffix(".svg"))
    plt.close()

def plot_gpu_stats(gpu_json: Path, outpath: Path, dpi=300):
    if not gpu_json.exists():
        print("No GPU stats file:", gpu_json)
        return
    with open(gpu_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        print("GPU stats empty")
        return
    times = [i for i in range(len(data))]
    loads = [d.get("gpu_load", 0) for d in data]
    mem_used = [d.get("gpu_memory_used", 0) for d in data]
    plt.figure(figsize=(10,5))
    plt.plot(times, loads, label="GPU load (%)", color="#1f77b4")
    plt.xlabel("sample index")
    plt.ylabel("GPU load (%)")
    plt.twinx()
    plt.plot(times, mem_used, label="GPU mem used (MB)", color="#ff7f0e")
    plt.ylabel("GPU mem (MB)")
    plt.title("GPU usage during run")
    plt.tight_layout()
    plt.savefig(outpath.with_suffix(".png"), dpi=dpi)
    plt.savefig(outpath.with_suffix(".svg"))
    plt.close()

def plot_model_sizes(models_dir: Path, outpath: Path, dpi=300):
    models = list(models_dir.glob("*.pkl"))
    if not models:
        print("No models found in", models_dir)
        return
    names = [m.name for m in models]
    sizes = [m.stat().st_size/1024/1024 for m in models]  # MB
    plt.figure(figsize=(8,4))
    bars = plt.bar(names, sizes, color="#2ca02c")
    plt.ylabel("Size (MB)")
    plt.title("Trained model sizes")
    plt.xticks(rotation=45, ha="right")
    for b, s in zip(bars, sizes):
        plt.text(b.get_x()+b.get_width()/2, s + 0.01, f"{s:.2f} MB", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    plt.savefig(outpath.with_suffix(".png"), dpi=dpi)
    plt.savefig(outpath.with_suffix(".svg"))
    plt.close()

def main():
    fused_path = Path("data/embeddings/fused_features_concat.pkl")
    gpu_json = Path("data/embeddings/gpu_stats.json")
    models_dir = Path("models")

    fused = load_fused(fused_path)
    if fused:
        print("Plotting t-SNE...")
        plot_tsne(fused, OUTDIR / "tsne_products", dpi=300)
    else:
        print("No fused features found at", fused_path)

    print("Plotting GPU stats...")
    plot_gpu_stats(gpu_json, OUTDIR / "gpu_usage", dpi=300)

    print("Plotting model sizes...")
    plot_model_sizes(models_dir, OUTDIR / "model_sizes", dpi=300)

    print("Figures saved to", OUTDIR.resolve())

if __name__ == "__main__":
    main()

