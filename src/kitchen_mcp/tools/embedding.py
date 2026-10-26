"""임베딩 검색 인덱스. 벡터 DB 없이 메모리의 numpy 행렬로 코사인 유사도를 계산한다.

모델: fastembed의 intfloat/multilingual-e5-large (1024차원, data/fastembed_cache에 캐시).
e5 모델은 질문에 "query: ", 문서에 "passage: " 접두어를 붙이는 것이 권장된다.
fastembed의 query_embed / passage_embed가 이 접두어를 붙여 준다.
문서 임베딩은 data/embeddings/<이름>.npy 에 캐시한다 (문서 내용이 같으면 재사용).
"""
import hashlib
import json
from functools import lru_cache

import numpy as np

from kitchen_mcp.tools.store import DATA_DIR, recipes, storage_notes, substitutes

MODEL_NAME = "intfloat/multilingual-e5-large"


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding  # 불러오는 데 약 0.2~0.4초 걸려서 처음 검색할 때만 불러온다
    return TextEmbedding(model_name=MODEL_NAME, cache_dir=str(DATA_DIR / "fastembed_cache"))


def embed_queries(texts):
    return np.array(list(_model().query_embed(texts)), dtype=np.float32)


def embed_passages(texts):
    return np.array(list(_model().passage_embed(texts)), dtype=np.float32)


def _normalize(m):
    return m / np.linalg.norm(m, axis=1, keepdims=True)


class Index:
    """문서 목록(id, text)을 임베딩해 두고 질문과 가까운 순으로 돌려준다."""

    def __init__(self, name, docs):
        self.docs = docs
        digest = hashlib.sha256(json.dumps([d["text"] for d in docs], ensure_ascii=False).encode()).hexdigest()[:16]
        cache = DATA_DIR / "embeddings" / f"{name}_{digest}.npy"
        if cache.exists():
            self.matrix = np.load(cache)
        else:
            cache.parent.mkdir(exist_ok=True)
            self.matrix = _normalize(embed_passages([d["text"] for d in docs]))
            np.save(cache, self.matrix)

    def search(self, query, k=3):
        q = _normalize(embed_queries([query]))[0]
        scores = self.matrix @ q
        order = np.argsort(-scores)[:k]
        return [{"id": self.docs[i]["id"], "score": round(float(scores[i]), 4), "doc": self.docs[i]} for i in order]


@lru_cache(maxsize=None)
def recipe_index():
    docs = []
    for r in recipes().values():
        ings = ", ".join(i["name"] for i in r["ingredients"])
        docs.append({"id": r["id"], "text": f"{r['name']}. 태그: {' '.join(r['tags'])}. 재료: {ings}."})
    return Index("recipes", docs)


@lru_cache(maxsize=None)
def substitute_index():
    return Index("substitutes", [{"id": s["id"], "text": s["text"]} for s in substitutes()])


@lru_cache(maxsize=None)
def storage_index():
    return Index("storage", [{"id": n["id"], "text": n["text"]} for n in storage_notes()])
