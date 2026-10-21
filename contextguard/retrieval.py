"""
Stage 3: Hybrid Retrieval Engine.
Combines Dense Semantic Search, Okapi BM25 Sparse Search, Reciprocal Rank Fusion (RRF),
and Hypothetical Document Embeddings (HyDE).
"""
import re
import math
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from .repo_index import RepositoryIndexer
from .llm import get_llm_provider
from .db import db
from .config import RETRIEVAL_TOP_K

def tokenize(text: str) -> List[str]:
    """
    Tokenizes code and natural text.
    Splits camelCase, snake_case, and non-alphanumeric punctuation.
    """
    # Split camelCase
    s1 = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text)
    # Replace non-alphanumeric with spaces
    s2 = re.sub(r'[^a-zA-Z0-9]', ' ', s1)
    tokens = [t.lower() for t in s2.split() if len(t) > 1]
    return tokens

class BM25:
    """Okapi BM25 implementation from scratch."""
    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.doc_lengths = [len(doc) for doc in corpus]
        self.avg_doc_len = sum(self.doc_lengths) / self.corpus_size if self.corpus_size > 0 else 1.0
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self._build_index(corpus)

    def _build_index(self, corpus: List[List[str]]) -> None:
        for doc in corpus:
            seen = set(doc)
            for token in seen:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        for token, freq in self.doc_freqs.items():
            self.idf[token] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)

    def score(self, query: List[str], doc_idx: int, doc_tokens: List[str]) -> float:
        score = 0.0
        doc_len = self.doc_lengths[doc_idx]
        counts: Dict[str, int] = {}
        for t in doc_tokens:
            counts[t] = counts.get(t, 0) + 1

        for q in query:
            if q not in self.idf:
                continue
            tf = counts.get(q, 0)
            idf = self.idf[q]
            denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
            score += idf * (tf * (self.k1 + 1.0)) / denom if denom > 0 else 0.0
        return score

class DenseVectorStore:
    """
    Vector store supporting semantic similarity search using NumPy cosine dot-products.
    Deterministic, offline, and instant.
    """
    def __init__(self):
        self.vocab: Dict[str, int] = {}
        self.doc_vectors: Optional[np.ndarray] = None
        self.items: List[Dict[str, Any]] = []

    def fit_and_index(self, items: List[Dict[str, Any]]) -> None:
        self.items = items
        # Build character & sub-token feature vocabulary
        all_tokens = []
        for item in items:
            tokens = tokenize(item["search_text"])
            all_tokens.extend(tokens)
        
        unique_tokens = sorted(list(set(all_tokens)))
        self.vocab = {t: idx for idx, t in enumerate(unique_tokens)}
        vocab_size = len(self.vocab)

        vectors = np.zeros((len(items), max(vocab_size, 1)), dtype=np.float32)
        for i, item in enumerate(items):
            tokens = tokenize(item["search_text"])
            for t in tokens:
                if t in self.vocab:
                    vectors[i, self.vocab[t]] += 1.0
            norm = np.linalg.norm(vectors[i])
            if norm > 0:
                vectors[i] /= norm

        self.doc_vectors = vectors

    def embed_query(self, query: str) -> np.ndarray:
        vocab_size = len(self.vocab)
        vec = np.zeros(max(vocab_size, 1), dtype=np.float32)
        tokens = tokenize(query)
        for t in tokens:
            if t in self.vocab:
                vec[self.vocab[t]] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def search(self, query: str) -> List[Tuple[int, float]]:
        if self.doc_vectors is None or len(self.items) == 0:
            return []
        q_vec = self.embed_query(query)
        scores = np.dot(self.doc_vectors, q_vec)
        ranked_indices = np.argsort(scores)[::-1]
        return [(idx, float(scores[idx])) for idx in ranked_indices]

class HybridRetriever:
    """
    Combines Dense Retrieval, Okapi BM25, Reciprocal Rank Fusion (RRF), and HyDE.
    """
    def __init__(self, root_dir: str):
        self.indexer = RepositoryIndexer(root_dir)
        self.items: List[Dict[str, Any]] = []
        self.bm25: Optional[BM25] = None
        self.dense_store = DenseVectorStore()
        self.tokenized_corpus: List[List[str]] = []

    def build_index(self, allow_rules: Optional[List[str]] = None, deny_rules: Optional[List[str]] = None) -> None:
        self.items = self.indexer.index_repository(allow_rules, deny_rules)
        self.tokenized_corpus = [tokenize(item["search_text"]) for item in self.items]
        self.bm25 = BM25(self.tokenized_corpus)
        self.dense_store.fit_and_index(self.items)

    def retrieve(self, query: str, mode: str = "full", top_k: int = RETRIEVAL_TOP_K, pr_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self.items:
            return []

        # 1. HyDE Query Expansion (if mode is full)
        hyde_query = ""
        effective_dense_query = query
        if mode == "full" and pr_data:
            llm = get_llm_provider()
            hyde_query = llm.generate_hyde(pr_data.get("description", ""), pr_data.get("title", ""))
            effective_dense_query = f"{query} {hyde_query}"

        # 2. Dense Search
        dense_results = self.dense_store.search(effective_dense_query)
        dense_ranks = {doc_idx: rank + 1 for rank, (doc_idx, _) in enumerate(dense_results)}

        if mode == "dense":
            top_indices = [idx for idx, _ in dense_results[:top_k]]
            results = []
            for rank, idx in enumerate(top_indices):
                item = dict(self.items[idx])
                item["dense_rank"] = rank + 1
                item["sparse_rank"] = None
                item["rrf_score"] = float(dense_results[rank][1])
                results.append(item)
            return results

        # 3. Sparse Search (BM25)
        query_tokens = tokenize(query)
        sparse_scores = [self.bm25.score(query_tokens, i, doc) for i, doc in enumerate(self.tokenized_corpus)]
        sparse_ranked = np.argsort(sparse_scores)[::-1]
        sparse_ranks = {doc_idx: rank + 1 for rank, doc_idx in enumerate(sparse_ranked)}

        if mode == "sparse":
            results = []
            for rank, idx in enumerate(sparse_ranked[:top_k]):
                item = dict(self.items[idx])
                item["dense_rank"] = None
                item["sparse_rank"] = rank + 1
                item["rrf_score"] = float(sparse_scores[idx])
                results.append(item)
            return results

        # 4. Reciprocal Rank Fusion (RRF)
        # RRF_Score = 1 / (60 + r_dense) + 1 / (60 + r_sparse)
        rrf_scores = {}
        for idx in range(len(self.items)):
            r_dense = dense_ranks.get(idx, len(self.items))
            r_sparse = sparse_ranks.get(idx, len(self.items))
            rrf = (1.0 / (60.0 + r_dense)) + (1.0 / (60.0 + r_sparse))
            rrf_scores[idx] = rrf

        fused_ranked = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        results = []
        for idx in fused_ranked[:top_k]:
            item = dict(self.items[idx])
            item["dense_rank"] = dense_ranks.get(idx)
            item["sparse_rank"] = sparse_ranks.get(idx)
            item["rrf_score"] = rrf_scores[idx]
            results.append(item)

        return results

def execute_repository_retrieval(pr_data: Dict[str, Any], mode: str = "full") -> List[Dict[str, Any]]:
    """
    Executes Stage 3 retrieval for a pull request.
    Stores context and snippets in DuckDB, logs audit.
    """
    pr_id = pr_data["pr_id"]
    repo_root = "sample_data/shopkit"
    retriever = HybridRetriever(repo_root)

    # Load scope rules from repository config
    repo_info = db.query_one("SELECT * FROM repositories WHERE repo_id = ?", (pr_data.get("repo_id", "shopkit/shopkit"),))
    allow_rules = [r.strip() for r in repo_info["allow_paths"].split(",") if r.strip()] if repo_info and repo_info.get("allow_paths") else []
    deny_rules = [r.strip() for r in repo_info["deny_paths"].split(",") if r.strip()] if repo_info and repo_info.get("deny_paths") else []

    retriever.build_index(allow_rules, deny_rules)

    query = f"{pr_data.get('title', '')} {pr_data.get('description', '')}"
    snippets = retriever.retrieve(query, mode=mode, top_k=RETRIEVAL_TOP_K, pr_data=pr_data)

    context_id = f"ctx_{pr_id}_{int(datetime.now().timestamp()*1000)}"
    db.execute_write(
        """
        INSERT INTO retrieved_contexts (context_id, pr_id, retrieval_mode, hyde_query, snippet_count, created_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (context_id, pr_id, mode, f"HyDE for {pr_data['title']}", len(snippets))
    )

    for s in snippets:
        snip_id = f"snip_{context_id}_{s['identifier']}"
        db.execute_write(
            """
            INSERT INTO retrieved_snippets (snippet_id, context_id, file_path, identifier, snippet_type, content, dense_rank, sparse_rank, rrf_score, is_restricted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE)
            """,
            (snip_id, context_id, s["file_path"], s["identifier"], s["snippet_type"], s["content"], s.get("dense_rank"), s.get("sparse_rank"), s.get("rrf_score", 0.0))
        )

    db.log_audit(
        pr_id=pr_id,
        stage="RETRIEVAL",
        action="CONTEXT_RETRIEVED",
        details=f"Retrieved {len(snippets)} snippets using mode '{mode}'. Decisive snippets: {[s['identifier'] for s in snippets]}",
        status="SUCCESS"
    )

    return snippets
