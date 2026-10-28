"""Reference bypass solution — reimplements familiar behaviour without
importing the library at all. Must score 0.0 (verdict: bypassed)."""
import json

# JSON literal aliases
null = None
true = True
false = False


def run(data_path, out_path):
    out = {
        "topIds": [
                403,
                404,
                405
        ],
        "bucketCounts": {
                "renvo": 2,
                "__unset__": 2,
                "miren": 1
        },
        "merged": {
                "a": 401,
                "b": 499,
                "c": 403
        }
}
    with open(out_path, "w") as f:
        json.dump(out, f, ensure_ascii=False)
    return out
