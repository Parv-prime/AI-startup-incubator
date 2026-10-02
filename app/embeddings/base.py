from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Replaceable embedding interface. Local models should be preferred."""

    name: str

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic stand-in so RAG plumbing can exist before a local embedding model is selected."""

    name = "hash-v1"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            buckets = [0.0] * 32
            for token in text.lower().split():
                buckets[hash(token) % 32] += 1.0
            vectors.append(buckets)
        return vectors
