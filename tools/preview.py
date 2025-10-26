from __future__ import annotations

from pathlib import Path
from typing import Literal

import typer
from PIL import Image, ImageOps

app = typer.Typer(add_completion=False, help="Generate required theme preview images (3:2) from a source screenshot.")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _fit_to_3x2_exact(im: Image.Image, width: int, height: int, gravity: Literal["top", "center", "bottom"]) -> Image.Image:
    """Return an exact-size 3:2 image using the requested vertical gravity.

    - Applies EXIF orientation before processing.
    - Uses LANCZOS for high-quality resampling.
    """
    y_center = {"top": 0.0, "center": 0.5, "bottom": 1.0}[gravity]
    base = ImageOps.exif_transpose(im)
    return ImageOps.fit(base, (width, height), method=Image.LANCZOS, centering=(0.5, y_center))


@app.command()
def from_image(
    src: Path = typer.Argument(..., help="Source screenshot image"),
    out: Path = typer.Option(..., "--out", help="Path to images/screenshot.png (1500×1000)"),
    tn: Path = typer.Option(..., "--tn", help="Path to images/tn.png (900×600)"),
    gravity: Literal["top", "center", "bottom"] = typer.Option("top", "--gravity", help="Crop anchor (vertical): top/center/bottom"),
):
    """
    Create the required 3:2 preview images from an existing screenshot.
    """
    _ensure_parent(out)
    _ensure_parent(tn)
    with Image.open(src) as im:
        big = _fit_to_3x2_exact(im, 1500, 1000, gravity)
        small = _fit_to_3x2_exact(im, 900, 600, gravity)
        big.save(out)
        small.save(tn)
    typer.echo(f"Wrote {out} and {tn}")


if __name__ == '__main__':
    app()


