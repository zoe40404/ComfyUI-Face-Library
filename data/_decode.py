# -*- coding: utf-8 -*-
"""运行时数据解码器。

负责在首次使用时将固化数据还原为结构化字典，并做内存缓存。
"""
import base64
import gzip
import json

_cache = None


def _decode(blob):
    raw = base64.b64decode(blob)
    raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def load_data():
    """返回合并后的完整数据字典（惰性解码 + 缓存）。"""
    global _cache
    if _cache is not None:
        return _cache

    from ._bundle_female import _B as _bf
    from ._bundle_male import _B as _bm
    from ._bundle_menus import _B as _bs

    female = _decode(_bf)
    male = _decode(_bm)
    meta = _decode(_bs)

    entries = {}
    for e in female:
        entries[e["id"]] = e
    for e in male:
        entries[e["id"]] = e

    _cache = {
        "entries": entries,
        "female": female,
        "male": male,
        "menus": meta["menus"],
        "male_bone_base": meta["male_bone_base"],
        "negative_words": meta["negative_words"],
    }
    return _cache
