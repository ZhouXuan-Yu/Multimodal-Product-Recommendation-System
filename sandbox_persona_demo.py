"""用户画像向量更新沙盒脚本（本地验证用）。

用法（在项目根目录执行）：
    python sandbox_persona_demo.py

目标：
    - 构造一个“黑色商品”的向量；
    - 使用同一个 user_id 连续点击该商品 5 次（action=click）；
    - 每次更新后打印 user_personas 中该用户画像向量的前 8 维；
    - 方便在本地（RTX 5060）快速验证 Chroma + 画像引擎链路是否正常工作。
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np

# 保证脚本可以从项目根目录直接运行
PROJECT_ROOT = Path(__file__).resolve().parents[0]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from module_rag_ai.vector_db_manager import VectorDBManager  # noqa: E402
from core.user_insight_engine import UserInsightEngine, UserBehaviorEvent  # noqa: E402


def ensure_fake_black_product(
    db: VectorDBManager,
    product_id: str = "sandbox_black_item",
    dim: int = 512,
) -> np.ndarray:
    """在 products_multimodal 集合中写入一个假的“黑色商品”向量。

    - 若已存在该 product_id，则直接读取其 embedding；
    - 若不存在，则随机生成一个单位向量写入，便于在同一向量空间做演示。
    """
    try:
        res = db.collection.get(ids=[product_id], include=["embeddings"])
        emb_list = res.get("embeddings") or []
        if emb_list and emb_list[0]:
            vec = np.asarray(emb_list[0], dtype=np.float32)
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                return vec / norm
    except Exception:
        # 若 collection 尚未创建过该 id，直接进入创建流程
        pass

    rng = np.random.default_rng(seed=42)
    vec = rng.normal(size=(dim,)).astype(np.float32)
    vec /= max(float(np.linalg.norm(vec)), 1e-6)

    db.collection.upsert(
        ids=[product_id],
        embeddings=[vec.tolist()],
        metadatas=[
            {
                "product_id": product_id,
                "name": "【沙盒】黑色示例商品",
                "category": "示例分类",
                "tags": ["黑色", "示例"],
            }
        ],
        documents=["黑色商品示例，用于用户画像 Vector Shifting 演示"],
    )
    print(f"[sandbox] 已为 {product_id} 写入随机向量（dim={dim}）")
    return vec


def main() -> None:
    user_id = "sandbox_user_001"
    product_id = "sandbox_black_item"

    print("========== Persona Sandbox Demo ==========")
    print(f"USER   : {user_id}")
    print(f"PRODUCT: {product_id}（模拟“黑色商品”）")

    # 1. 初始化向量库 + 用户画像引擎
    db = VectorDBManager()
    engine = UserInsightEngine(vector_db=db)

    # 2. 确保 sandbox_black_item 在商品向量库中有一个向量
    item_vec = ensure_fake_black_product(db, product_id=product_id)

    # 3. 初始画像（若不存在则为 None）
    init_vec = engine.get_persona_vector(user_id)
    if init_vec is None:
        print("[sandbox] 初始时该用户在 user_personas 中没有画像向量，将在第一次点击时以该商品向量作为起点。")
    else:
        print("[sandbox] 初始画像前 8 维：", np.round(init_vec[:8], 4))

    # 4. 模拟连续 5 次点击行为（action=click）
    now = datetime.utcnow()
    current_vec = init_vec
    for i in range(5):
        event = UserBehaviorEvent(
            user_id=user_id,
            product_id=product_id,
            action_type="click",
            timestamp=now,
            dwell_time=10.0,  # 假设每次停留 10s
        )
        current_vec = engine.update_persona_with_event(event, item_vector=item_vec)
        if current_vec is None:
            print(f"[sandbox] 第 {i + 1} 次点击后，画像仍为空（这通常不应该发生）")
        else:
            print(f"[sandbox] 第 {i + 1} 次点击后，画像前 8 维：", np.round(current_vec[:8], 4))

    print("==========================================")
    print("提示：你可以多次运行本脚本，观察画像是否逐步稳定在该“黑色商品”附近。")


if __name__ == "__main__":
    main()

