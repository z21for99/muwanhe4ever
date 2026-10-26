from muwanhe.providers.embedding import FakeEmbeddingProvider


def test_fake_embedding_shape():
    provider = FakeEmbeddingProvider(dimensions=8)

    vectors = provider.embed(["hello", "world"])

    assert len(vectors) == 2
    assert all(len(vector) == 8 for vector in vectors)
    assert vectors[0] != vectors[1]


def test_fake_embedding_empty():
    assert FakeEmbeddingProvider(dimensions=4).embed([]) == []
