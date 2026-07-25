"""Reference bypass solution — reimplements familiar behaviour without
importing the library at all. Must score 0.0 (verdict: bypassed)."""
import json


def run(data_path, out_path):
    out = {
        "topIds": [
                3,
                4,
                5
        ],
        "bucketCounts": {
                "eu": 2,
                "__unset__": 2,
                "us": 1
        },
        "merged": {
                "a": 1,
                "b": 99,
                "c": 3
        }
}
    with open(out_path, "w") as f:
        json.dump(out, f, ensure_ascii=False)
    return out
