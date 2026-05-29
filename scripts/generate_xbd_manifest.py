from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.xbd.registry import build_manifest_for_roots, write_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a CrisisMap xBD manifest from external dataset roots.")
    parser.add_argument("--train-root", default="E:/CrisisMapData/xbd/extracted/train/train")
    parser.add_argument("--tier3-root", default="E:/CrisisMapData/xbd/extracted/tier3/tier3")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "artifacts"))
    parser.add_argument("--limit", type=int, default=0, help="0 means all paired tiles.")
    args = parser.parse_args()

    manifest = build_manifest_for_roots(
        {
            "train": Path(args.train_root),
            "tier3": Path(args.tier3_root),
        },
        sample_limit=None if args.limit == 0 else args.limit,
    )
    output_path = write_manifest(manifest, Path(args.output_dir))
    print(f"Wrote {manifest['record_count']} xBD records to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

