"""Chinese-CLIP 文本侧批处理 Worker。

设计目标：
- 通过请求队列（Request Queue）聚合 0.1s 内的查询请求；
- 将聚合后的查询以一个 batch 送入 GPU 推理，最大化 RTX 5060 利用率；
- 对上层暴露同步接口 encode_query，便于在 FastAPI 同步路径中直接调用。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from queue import Queue, Empty
from typing import List

import numpy as np
import torch
from transformers import AutoModel, AutoProcessor


BATCH_WINDOW_SECONDS = 0.1  # 聚合窗口：0.1s 内的请求合并为一个 batch
MODEL_NAME = "OFA-Sys/chinese-clip-vit-base-patch16"


@dataclass
class _TextJob:
    text: str
    done: threading.Event = field(default_factory=threading.Event)
    result: np.ndarray | None = None
    error: Exception | None = None


class ModelWorker:
    """CLIP 文本编码批处理 Worker（线程驱动，兼容 FastAPI 同步视图）。"""

    def __init__(self) -> None:
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

        # 使用半精度运行在 RTX 上以提升吞吐
        torch_dtype = torch.float16 if self._device == "cuda" else torch.float32
        self._processor = AutoProcessor.from_pretrained(MODEL_NAME)
        self._model = AutoModel.from_pretrained(MODEL_NAME, torch_dtype=torch_dtype)
        if self._device == "cuda":
            self._model = self._model.to(self._device).eval()
        else:
            self._model = self._model.to(self._device).eval()

        self._queue: "Queue[_TextJob]" = Queue()
        self._worker_thread = threading.Thread(target=self._loop, daemon=True)
        self._worker_thread.start()

    def encode_query(self, text: str, timeout: float = 10.0) -> np.ndarray:
        """同步接口：提交单条文本并阻塞等待结果（内部自动聚合为 batch）。"""
        job = _TextJob(text=text)
        self._queue.put(job)
        ok = job.done.wait(timeout=timeout)
        if not ok:
            raise TimeoutError("ModelWorker 编码超时")
        if job.error is not None:
            raise job.error
        assert job.result is not None  # for type checker
        return job.result

    # ------------------------------------------------------------------ #
    # 内部批处理主循环
    # ------------------------------------------------------------------ #
    def _loop(self) -> None:
        while True:
            try:
                first_job = self._queue.get()
            except Exception:
                continue

            jobs: List[_TextJob] = [first_job]
            deadline = time.time() + BATCH_WINDOW_SECONDS

            # 在 0.1s 窗口内不断拉取新任务，凑成一个 batch
            while time.time() < deadline:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                try:
                    job = self._queue.get(timeout=remaining)
                    jobs.append(job)
                except Empty:
                    break

            try:
                texts = [j.text for j in jobs]
                with torch.no_grad():
                    inputs = self._processor(
                        text=texts,
                        return_tensors="pt",
                        padding=True,
                        truncation=True,
                    ).to(self._device)
                    # 与 ChineseCLIPEmbedder.encode_text 对齐的文本特征提取逻辑
                    try:
                        text_features = self._model.get_text_features(**inputs)
                    except TypeError:
                        text_features = None

                    if text_features is None:
                        text_outputs = self._model.text_model(
                            input_ids=inputs.get("input_ids"),
                            attention_mask=inputs.get("attention_mask"),
                            token_type_ids=inputs.get("token_type_ids"),
                            output_hidden_states=False,
                            return_dict=True,
                        )
                        last_hidden = text_outputs.last_hidden_state  # [B, T, H]
                        pooled = last_hidden[:, 0, :]  # CLS
                        text_features = self._model.text_projection(pooled)

                    text_features = torch.nn.functional.normalize(text_features, dim=-1)

                for idx, job in enumerate(jobs):
                    vec = text_features[idx].detach().cpu().numpy().astype(np.float32)
                    job.result = vec
                    job.done.set()
            except Exception as exc:  # noqa: BLE001
                for job in jobs:
                    job.error = exc
                    job.done.set()


_GLOBAL_WORKER: ModelWorker | None = None
_LOCK = threading.Lock()


def get_global_clip_worker() -> ModelWorker:
    """获取进程内全局唯一的 ModelWorker 实例。"""
    global _GLOBAL_WORKER
    if _GLOBAL_WORKER is None:
        with _LOCK:
            if _GLOBAL_WORKER is None:
                _GLOBAL_WORKER = ModelWorker()
    return _GLOBAL_WORKER

