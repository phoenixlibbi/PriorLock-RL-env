#!/usr/bin/env bash
set -e
cat > /app/repo/src/pipeline.py << 'PYEOF'
"""Gold solution — uses tablix v1.4 semantics correctly."""
import json
import tablix


def run(data_dir, out_path):
    records = tablix.load_csv(f"{data_dir}/transactions.csv")

    # group_by includes __missing__ for empty/null category (v1.4 behaviour)
    groups = tablix.group_by(records, "category")

    categorySales = {cat: tablix.sum_field(recs, "amount")
                     for cat, recs in groups.items()}
    categoryCount = {cat: len(recs) for cat, recs in groups.items()}

    # top_n includes ALL ties at position n (v1.4 behaviour)
    top = tablix.top_n(records, 3, "amount")
    topProductIds = sorted(int(r["id"]) for r in top)

    with open(out_path, "w") as f:
        json.dump({
            "categorySales": categorySales,
            "categoryCount": categoryCount,
            "topProductIds": topProductIds,
        }, f, indent=2)
PYEOF
