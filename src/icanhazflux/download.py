from pathlib import Path

from icoscp_core.icos import data

from .objects import DataObject


def _download_objects(
    objects: list[DataObject],
    out: str | Path,
    *,
    progress: bool = True,
) -> list[Path]:
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    total = len(objects)
    for i, obj in enumerate(objects, start=1):
        if progress:
            print(f"[{i}/{total}] {obj.filename} ({obj.size_mb:.1f} MB)")
        name = data.save_to_folder(obj.uri, str(out_dir))
        saved.append(out_dir / name)
    return saved


def _total_size_bytes(objects: list[DataObject]) -> int:
    return sum(o.size_bytes for o in objects)
