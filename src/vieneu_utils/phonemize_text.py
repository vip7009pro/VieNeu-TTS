"""
Phonemization module for VieNeu-TTS.
Delegates all normalization and G2P logic to the sea-g2p library,
which provides a unified, tested, and maintained Vietnamese G2P pipeline.
"""
import functools
import logging
import time
from cachetools import TTLCache
from sea_g2p import SEAPipeline, G2P, Normalizer

logger = logging.getLogger("Vieneu.Phonemizer")

# ---------------------------------------------------------------------------
# Shared singletons (instantiation is lazy-safe and thread-safe via GIL)
# ---------------------------------------------------------------------------
_pipeline: SEAPipeline = None
_g2p: G2P = None
_normalizer: Normalizer = None

def _get_pipeline() -> SEAPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = SEAPipeline(lang="vi")
    return _pipeline

def _get_g2p() -> G2P:
    global _g2p
    if _g2p is None:
        _g2p = G2P(lang="vi")
    return _g2p

def _get_normalizer() -> Normalizer:
    global _normalizer
    if _normalizer is None:
        _normalizer = Normalizer()
    return _normalizer

# ---------------------------------------------------------------------------
# Public API  (same signatures as before — callers don't need to change)
# ---------------------------------------------------------------------------

_PHONEMIZE_CACHE = TTLCache(maxsize=1024, ttl=3600)
_CACHE_STATS = {"hits": 0, "misses": 0, "last_log": 0}

def _phonemize_cached(text: str) -> str:
    """Cached single-text phonemization (normalize + G2P) using TTLCache."""
    global _PHONEMIZE_CACHE

    if text in _PHONEMIZE_CACHE:
        _CACHE_STATS["hits"] += 1
        result = _PHONEMIZE_CACHE[text]
    else:
        _CACHE_STATS["misses"] += 1
        result = _get_pipeline().run(text)
        _PHONEMIZE_CACHE[text] = result

    # Log cache info periodically (every 100 calls or 5 minutes)
    current_time = time.time()
    total_calls = _CACHE_STATS["hits"] + _CACHE_STATS["misses"]
    if total_calls % 100 == 0 or (current_time - _CACHE_STATS["last_log"] > 300):
        hit_rate = (_CACHE_STATS["hits"] / total_calls) * 100 if total_calls > 0 else 0
        logger.info(
            f"Phonemizer Cache Info: Hits={_CACHE_STATS['hits']}, Misses={_CACHE_STATS['misses']}, "
            f"Hit Rate={hit_rate:.2f}%, Size={len(_PHONEMIZE_CACHE)}/1024"
        )
        _CACHE_STATS["last_log"] = current_time

    return result


def phonemize_text(text: str) -> str:
    """Normalize and phonemize a single Vietnamese/bilingual text string."""
    return _phonemize_cached(text)


def phonemize_batch(
    texts: list[str],
    skip_normalize: bool = False,
    phoneme_dict: dict = None,
    **kwargs,
) -> list[str]:
    """
    Phonemize multiple texts with bilingual support.

    Args:
        texts:          List of input strings.
        skip_normalize: If True, assume the texts are already normalized
                        (i.e. only run G2P, not the normalizer).
        phoneme_dict:   Optional custom {word: phoneme} dict that overrides
                        the built-in dictionary for specific words.
    """
    if not texts:
        return []

    g2p = _get_g2p()

    if skip_normalize:
        # Texts are pre-normalized — only run the G2P layer
        return g2p.phonemize_batch(texts, phoneme_dict=phoneme_dict)
    else:
        # Full pipeline: normalize then G2P
        normalizer = _get_normalizer()
        normalized = [normalizer.normalize(t) for t in texts]
        return g2p.phonemize_batch(normalized, phoneme_dict=phoneme_dict)


def phonemize_with_dict(
    text: str,
    phoneme_dict: dict = None,
    skip_normalize: bool = False,
) -> str:
    """
    Phonemize a single text, optionally with a custom word→phoneme mapping.

    When phoneme_dict is None and skip_normalize is False, the result is
    cached via lru_cache for performance.
    """
    if phoneme_dict is not None:
        # Custom dict supplied — skip cache to avoid cross-contamination
        return phonemize_batch(
            [text], skip_normalize=skip_normalize, phoneme_dict=phoneme_dict
        )[0]
    if skip_normalize:
        return _get_g2p().phonemize_batch([text])[0]
    return _phonemize_cached(text)


# ---------------------------------------------------------------------------
# CLI helper (python -m vieneu_utils.phonemize_text "some text")
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    test_text = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "Giá SP500 hôm nay là 4.200,5 điểm."
    )
    print(f"Output: {phonemize_text(test_text)}")