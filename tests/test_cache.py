from mrt.cache import LineCache


def test_line_cache_filters_unchanged_lines():
    cache = LineCache(max_lines=3)
    lines = ["a", "b", "c"]
    first = cache.update(lines)
    assert first == lines

    second = cache.update(["a", "b", "d"])
    assert second == ["d"]
    assert len(cache) == 3

    cache.prune(ttl=0)
    assert len(cache) == 0
