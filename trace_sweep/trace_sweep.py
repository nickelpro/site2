#!/usr/bin/env python3
"""
Sweep Inkscape-compatible brightness-cutoff traces through Potrace and export PNGs.

Requires:
    Python 3.10+
    Pillow
    Potrace
    Inkscape 1.4+ (1.4 added command-line PNG compression and antialias controls)

The threshold preprocessing deliberately reproduces Inkscape's Trace Bitmap
"Brightness cutoff" implementation, including its equal-weight RGB brightness
calculation and alpha compositing over white.
"""

from __future__ import annotations

import argparse
import copy
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Sequence

try:
    from PIL import Image, ImageMath, ImageOps
except ImportError as exc:
    raise SystemExit(
        "Pillow is required. On Arch Linux: sudo pacman -S python-pillow"
    ) from exc


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


class PipelineError(RuntimeError):
    pass


def decimal_arg(text: str) -> Decimal:
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(f"not a decimal number: {text!r}") from exc
    if not value.is_finite():
        raise argparse.ArgumentTypeError(f"not a finite number: {text!r}")
    return value


def bounded_int(low: int, high: int):
    def parse(text: str) -> int:
        try:
            value = int(text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"not an integer: {text!r}") from exc
        if not low <= value <= high:
            raise argparse.ArgumentTypeError(
                f"value must be between {low} and {high}: {value}"
            )
        return value

    return parse


def positive_int(text: str) -> int:
    value = bounded_int(1, 2_147_483_647)(text)
    return value


def nonnegative_int(text: str) -> int:
    value = bounded_int(0, 2_147_483_647)(text)
    return value


def finite_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from exc
    if value != value or value in (float("inf"), float("-inf")):
        raise argparse.ArgumentTypeError(f"not a finite number: {text!r}")
    return value


def nonnegative_float(text: str) -> float:
    value = finite_float(text)
    if value < 0:
        raise argparse.ArgumentTypeError("value must be nonnegative")
    return value


def quote_command(command: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run(command: Sequence[str], *, verbose: bool) -> subprocess.CompletedProcess[str]:
    if verbose:
        print(f"+ {quote_command(command)}", file=sys.stderr)
    try:
        return subprocess.run(
            list(command),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise PipelineError(f"program not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        message = f"command failed ({exc.returncode}): {quote_command(command)}"
        if detail:
            message += f"\n{detail}"
        raise PipelineError(message) from exc


def resolve_program(program: str) -> str:
    resolved = shutil.which(program)
    if resolved is None:
        raise PipelineError(f"program not found: {program}")
    return resolved


def check_inkscape(program: str, *, verbose: bool) -> None:
    result = run([program, "--version"], verbose=verbose)
    text = f"{result.stdout}\n{result.stderr}"
    match = re.search(r"\bInkscape\s+(\d+)\.(\d+)", text)
    if match and (int(match.group(1)), int(match.group(2))) < (1, 4):
        raise PipelineError(
            "Inkscape 1.4 or newer is required for command-line PNG "
            "compression and antialias controls"
        )


def check_potrace(program: str, *, verbose: bool) -> None:
    run([program, "--version"], verbose=verbose)


def generate_thresholds(start: Decimal, stop: Decimal, step: Decimal) -> list[Decimal]:
    if not (Decimal(0) <= start <= Decimal(1)):
        raise PipelineError("--threshold-start must be in [0, 1]")
    if not (Decimal(0) <= stop <= Decimal(1)):
        raise PipelineError("--threshold-stop must be in [0, 1]")
    if stop < start:
        raise PipelineError("--threshold-stop must not be below --threshold-start")
    if step <= 0:
        raise PipelineError("--threshold-step must be positive")

    result: list[Decimal] = []
    value = start
    while value <= stop:
        result.append(value)
        if len(result) > 10_000:
            raise PipelineError("threshold range would produce more than 10,000 scans")
        value += step
    return result


def decimal_places(values: Iterable[Decimal]) -> int:
    return max(0, max((-value.as_tuple().exponent for value in values), default=0))


def threshold_label(value: Decimal, places: int) -> str:
    return f"{value:.{places}f}".replace("-", "m").replace(".", "p")


def load_rgba(path: Path) -> Image.Image:
    try:
        with Image.open(path) as source:
            source.seek(0)
            source = ImageOps.exif_transpose(source)
            return source.convert("RGBA")
    except OSError as exc:
        raise PipelineError(f"cannot read input image {path}: {exc}") from exc


def build_inkscape_brightness(rgba: Image.Image) -> Image.Image:
    """
    Reproduce Inkscape 1.4's gdkPixbufToGrayMap():

        alpha  = A
        white  = 3 * (255 - alpha)
        sample = R + G + B
        bright = sample * alpha / 256 + white

    The result is an integer image with values in approximately [0, 765].
    ImageMath performs integer division for mode-I operands.
    """
    r, g, b, a = (channel.convert("I") for channel in rgba.split())
    if hasattr(ImageMath, "lambda_eval"):
        return ImageMath.lambda_eval(
            lambda p: ((p["r"] + p["g"] + p["b"]) * p["a"]) / 256
            + 3 * (255 - p["a"]),
            r=r,
            g=g,
            b=b,
            a=a,
        )

    # Compatibility with older Pillow versions.
    expression = "((r + g + b) * a) / 256 + 3 * (255 - a)"
    if hasattr(ImageMath, "unsafe_eval"):
        return ImageMath.unsafe_eval(expression, r=r, g=g, b=b, a=a)
    return ImageMath.eval(expression, r=r, g=g, b=b, a=a)


def threshold_bitmap(
    brightness: Image.Image, threshold: Decimal, *, invert: bool
) -> Image.Image:
    """
    Inkscape marks a pixel black when:

        brightness < 3 * threshold * 256

    Use an exact rational comparison rather than a floating-point cutoff.
    Pillow mode "1" stores black as 0 and white as 255.
    """
    ratio = Fraction(threshold)
    denominator = ratio.denominator
    cutoff_numerator = ratio.numerator * 768

    if hasattr(ImageMath, "lambda_eval"):
        if invert:
            mask = ImageMath.lambda_eval(
                lambda p: (p["brightness"] * denominator < cutoff_numerator) * 255,
                brightness=brightness,
            )
        else:
            mask = ImageMath.lambda_eval(
                lambda p: (p["brightness"] * denominator >= cutoff_numerator) * 255,
                brightness=brightness,
            )
    else:
        operator = "<" if invert else ">="
        expression = (
            f"(brightness * {denominator} {operator} {cutoff_numerator}) * 255"
        )
        if hasattr(ImageMath, "unsafe_eval"):
            mask = ImageMath.unsafe_eval(expression, brightness=brightness)
        else:
            mask = ImageMath.eval(expression, brightness=brightness)

    return mask.convert("1", dither=Image.Dither.NONE)


def write_pbm(
    brightness: Image.Image, threshold: Decimal, destination: Path, *, invert: bool
) -> None:
    bitmap = threshold_bitmap(brightness, threshold, invert=invert)
    destination.parent.mkdir(parents=True, exist_ok=True)
    bitmap.save(destination, format="PPM")


def potrace_svg(
    potrace: str,
    pbm: Path,
    svg: Path,
    *,
    speckles: int,
    smooth_corners: float,
    optimize: bool,
    optimize_tolerance: float,
    turn_policy: str,
    coordinate_unit: int,
    verbose: bool,
) -> None:
    command = [
        potrace,
        "--svg",
        "--flat",
        "--resolution",
        "96",
        "--turnpolicy",
        turn_policy,
        "--turdsize",
        str(speckles),
        "--alphamax",
        f"{smooth_corners:.17g}",
        "--unit",
        str(coordinate_unit),
    ]
    if optimize:
        command += ["--opttolerance", f"{optimize_tolerance:.17g}"]
    else:
        command.append("--longcurve")
    command += ["--output", str(svg), str(pbm)]
    run(command, verbose=verbose)


def export_png(
    inkscape: str,
    svg: Path,
    png: Path,
    *,
    width: int | None,
    height: int | None,
    dpi: float | None,
    color_mode: str,
    compression: int,
    antialias: int,
    dithering: bool,
    background: str | None,
    background_opacity: float,
    verbose: bool,
) -> None:
    command = [
        inkscape,
        str(svg),
        "--export-type=png",
        f"--export-filename={png}",
        "--export-area-page",
        "--export-overwrite",
        f"--export-png-color-mode={color_mode}",
        f"--export-png-compression={compression}",
        f"--export-png-antialias={antialias}",
        f"--export-png-use-dithering={'true' if dithering else 'false'}",
        f"--export-background-opacity={background_opacity:.17g}",
    ]
    if width is not None:
        command.append(f"--export-width={width}")
    if height is not None:
        command.append(f"--export-height={height}")
    if dpi is not None:
        command.append(f"--export-dpi={dpi:.17g}")
    if background is not None:
        command.append(f"--export-background={background}")
    run(command, verbose=verbose)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def remove_paint_properties(element: ET.Element) -> None:
    element.attrib.pop("fill", None)
    element.attrib.pop("stroke", None)
    style = element.attrib.get("style")
    if style is None:
        return
    kept: list[str] = []
    for declaration in style.split(";"):
        declaration = declaration.strip()
        if not declaration:
            continue
        name = declaration.split(":", 1)[0].strip().lower()
        if name not in {"fill", "stroke"}:
            kept.append(declaration)
    if kept:
        element.set("style", ";".join(kept))
    else:
        element.attrib.pop("style", None)


def traced_drawing(svg: Path) -> tuple[dict[str, str], ET.Element]:
    try:
        root = ET.parse(svg).getroot()
    except (OSError, ET.ParseError) as exc:
        raise PipelineError(f"cannot parse Potrace SVG {svg}: {exc}") from exc

    drawing = next(
        (child for child in root if local_name(child.tag) == "g"),
        None,
    )
    if drawing is None:
        drawing = ET.Element(f"{{{SVG_NS}}}g")
        for child in root:
            if local_name(child.tag) in {"path", "polygon", "rect"}:
                drawing.append(copy.deepcopy(child))
    else:
        drawing = copy.deepcopy(drawing)

    for element in drawing.iter():
        remove_paint_properties(element)

    attributes = {
        key: value
        for key, value in root.attrib.items()
        if key in {"version", "width", "height", "viewBox", "preserveAspectRatio"}
    }
    return attributes, drawing


def combine_brightness_steps(
    traced: Sequence[tuple[Decimal, Path]], destination: Path
) -> None:
    if not traced:
        raise PipelineError("no traces were produced")

    root_attributes, _ = traced_drawing(traced[0][1])
    root_attributes.setdefault("version", "1.1")
    root = ET.Element(f"{{{SVG_NS}}}svg", root_attributes)

    # SVG paints later elements on top. The highest/lightest threshold goes
    # first; progressively darker thresholds are then painted over it.
    for threshold, svg in reversed(traced):
        _, drawing = traced_drawing(svg)
        gray = min(255, max(0, int(threshold * Decimal(256))))
        layer = ET.SubElement(
            root,
            f"{{{SVG_NS}}}g",
            {
                "fill": f"#{gray:02x}{gray:02x}{gray:02x}",
                "stroke": "none",
                "data-threshold": format(threshold, "f"),
            },
        )
        layer.append(drawing)

    destination.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(
        destination, encoding="utf-8", xml_declaration=True
    )


def png_ihdr(path: Path) -> tuple[int, int, int, int]:
    try:
        with path.open("rb") as stream:
            if stream.read(8) != b"\x89PNG\r\n\x1a\n":
                raise PipelineError(f"not a PNG file: {path}")
            length = struct.unpack(">I", stream.read(4))[0]
            chunk_type = stream.read(4)
            data = stream.read(length)
    except OSError as exc:
        raise PipelineError(f"cannot read output PNG {path}: {exc}") from exc

    if chunk_type != b"IHDR" or len(data) != 13:
        raise PipelineError(f"malformed PNG IHDR: {path}")
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[:10])
    return width, height, bit_depth, color_type


def verify_png(
    path: Path,
    *,
    expected_width: int | None,
    expected_height: int | None,
    color_mode: str,
) -> None:
    width, height, bit_depth, color_type = png_ihdr(path)
    if expected_width is not None and width != expected_width:
        raise PipelineError(
            f"{path} has width {width}, expected {expected_width}"
        )
    if expected_height is not None and height != expected_height:
        raise PipelineError(
            f"{path} has height {height}, expected {expected_height}"
        )
    if color_mode == "GrayAlpha_8" and (bit_depth, color_type) != (8, 4):
        raise PipelineError(
            f"{path} is PNG bit-depth/color-type {(bit_depth, color_type)}, "
            "expected 8-bit grayscale+alpha (8, 4)"
        )


def copy_if_requested(source: Path, destination: Path, keep: bool) -> Path:
    if keep:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination
    return source


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Run an Inkscape-compatible brightness-cutoff threshold sweep "
            "through Potrace and export controlled PNGs."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    result.add_argument("input", type=Path, help="source raster image")
    result.add_argument(
        "-o", "--output-dir", type=Path, default=Path("."), help="output directory"
    )
    result.add_argument("--name", help="output basename; defaults to input stem")
    result.add_argument(
        "--mode",
        choices=("separate", "brightness-steps"),
        default="separate",
        help=(
            "separate: one PNG per threshold; brightness-steps: one layered "
            "grayscale PNG matching Inkscape's multi-scan brightness styling"
        ),
    )

    thresholds = result.add_argument_group("threshold sweep")
    thresholds.add_argument(
        "--threshold-start", type=decimal_arg, default=Decimal("0.20")
    )
    thresholds.add_argument(
        "--threshold-stop", type=decimal_arg, default=Decimal("0.80")
    )
    thresholds.add_argument(
        "--threshold-step", type=decimal_arg, default=Decimal("0.05")
    )
    thresholds.add_argument(
        "--invert",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="invert the threshold bitmap after cutoff",
    )

    tracing = result.add_argument_group("Potrace / Trace Bitmap controls")
    tracing.add_argument(
        "--speckles",
        type=nonnegative_int,
        default=2,
        help="suppress components up to this many source pixels; 0 disables",
    )
    tracing.add_argument(
        "--smooth-corners",
        type=nonnegative_float,
        default=1.0,
        metavar="ALPHAMAX",
        help="corner smoothing; 0 gives polygonal output",
    )
    tracing.add_argument(
        "--optimize",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="join adjacent Bézier segments",
    )
    tracing.add_argument(
        "--optimize-tolerance",
        type=nonnegative_float,
        default=0.2,
        help="maximum curve-optimization error",
    )
    tracing.add_argument(
        "--turn-policy",
        choices=("black", "white", "right", "left", "minority", "majority", "random"),
        default="minority",
    )
    tracing.add_argument(
        "--coordinate-unit",
        type=positive_int,
        default=10,
        help="Potrace SVG coordinate quantization",
    )

    export = result.add_argument_group("PNG export")
    export.add_argument("--width", type=positive_int, help="output width in pixels")
    export.add_argument("--height", type=positive_int, help="output height in pixels")
    export.add_argument(
        "--dpi",
        type=nonnegative_float,
        help="output DPI; cannot be combined with width or height",
    )
    export.add_argument(
        "--color-mode",
        choices=(
            "Gray_1",
            "Gray_2",
            "Gray_4",
            "Gray_8",
            "Gray_16",
            "RGB_8",
            "RGB_16",
            "GrayAlpha_8",
            "GrayAlpha_16",
            "RGBA_8",
            "RGBA_16",
        ),
        default="GrayAlpha_8",
    )
    export.add_argument("--compression", type=bounded_int(0, 9), default=6)
    export.add_argument("--antialias", type=bounded_int(0, 3), default=2)
    export.add_argument(
        "--dithering", action=argparse.BooleanOptionalAction, default=False
    )
    export.add_argument("--background", help="SVG/CSS background color")
    export.add_argument(
        "--background-opacity",
        type=finite_float,
        default=0.0,
        help="0..1 or 0..255, as accepted by Inkscape",
    )

    files = result.add_argument_group("intermediates and programs")
    files.add_argument(
        "--keep-svg",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="retain traced SVG output",
    )
    files.add_argument(
        "--keep-pbm",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="retain thresholded PBM input to Potrace",
    )
    files.add_argument("--potrace", default="potrace", help="Potrace executable")
    files.add_argument("--inkscape", default="inkscape", help="Inkscape executable")
    files.add_argument(
        "-v", "--verbose", action="store_true", help="print subprocess commands"
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)

    if args.dpi is not None and (args.width is not None or args.height is not None):
        raise PipelineError("--dpi cannot be combined with --width or --height")
    if args.dpi is not None and args.dpi <= 0:
        raise PipelineError("--dpi must be positive")
    if not (
        0.0 <= args.background_opacity <= 1.0
        or 1.0 < args.background_opacity <= 255.0
    ):
        raise PipelineError("--background-opacity must be in [0,1] or (1,255]")

    input_path = args.input.expanduser().resolve()
    if not input_path.is_file():
        raise PipelineError(f"input is not a regular file: {input_path}")

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    base = args.name or input_path.stem

    thresholds = generate_thresholds(
        args.threshold_start, args.threshold_stop, args.threshold_step
    )
    places = decimal_places(
        (args.threshold_start, args.threshold_stop, args.threshold_step)
    )

    potrace = resolve_program(args.potrace)
    inkscape = resolve_program(args.inkscape)
    check_potrace(potrace, verbose=args.verbose)
    check_inkscape(inkscape, verbose=args.verbose)

    rgba = load_rgba(input_path)
    source_width, source_height = rgba.size
    brightness = build_inkscape_brightness(rgba)

    expected_width = args.width
    expected_height = args.height
    if args.width is None and args.height is None and args.dpi is None:
        expected_width = source_width
        expected_height = source_height

    produced: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="trace-sweep-") as temp_name:
        temp_dir = Path(temp_name)
        traced: list[tuple[Decimal, Path]] = []

        for threshold in thresholds:
            label = threshold_label(threshold, places)
            temporary_pbm = temp_dir / f"{base}-t{label}.pbm"
            temporary_svg = temp_dir / f"{base}-t{label}.svg"

            write_pbm(
                brightness, threshold, temporary_pbm, invert=args.invert
            )
            potrace_svg(
                potrace,
                temporary_pbm,
                temporary_svg,
                speckles=args.speckles,
                smooth_corners=args.smooth_corners,
                optimize=args.optimize,
                optimize_tolerance=args.optimize_tolerance,
                turn_policy=args.turn_policy,
                coordinate_unit=args.coordinate_unit,
                verbose=args.verbose,
            )

            if args.keep_pbm:
                shutil.copy2(
                    temporary_pbm, output_dir / f"{base}-t{label}.pbm"
                )

            if args.mode == "separate":
                svg_for_export = copy_if_requested(
                    temporary_svg,
                    output_dir / f"{base}-t{label}.svg",
                    args.keep_svg,
                )
                png = output_dir / f"{base}-t{label}.png"
                export_png(
                    inkscape,
                    svg_for_export,
                    png,
                    width=args.width,
                    height=args.height,
                    dpi=args.dpi,
                    color_mode=args.color_mode,
                    compression=args.compression,
                    antialias=args.antialias,
                    dithering=args.dithering,
                    background=args.background,
                    background_opacity=args.background_opacity,
                    verbose=args.verbose,
                )
                verify_png(
                    png,
                    expected_width=expected_width,
                    expected_height=expected_height,
                    color_mode=args.color_mode,
                )
                produced.append(png)
            else:
                traced.append((threshold, temporary_svg))

        if args.mode == "brightness-steps":
            temporary_composite = temp_dir / f"{base}-brightness-steps.svg"
            combine_brightness_steps(traced, temporary_composite)
            svg_for_export = copy_if_requested(
                temporary_composite,
                output_dir / f"{base}-brightness-steps.svg",
                args.keep_svg,
            )
            png = output_dir / f"{base}-brightness-steps.png"
            export_png(
                inkscape,
                svg_for_export,
                png,
                width=args.width,
                height=args.height,
                dpi=args.dpi,
                color_mode=args.color_mode,
                compression=args.compression,
                antialias=args.antialias,
                dithering=args.dithering,
                background=args.background,
                background_opacity=args.background_opacity,
                verbose=args.verbose,
            )
            verify_png(
                png,
                expected_width=expected_width,
                expected_height=expected_height,
                color_mode=args.color_mode,
            )
            produced.append(png)

    for path in produced:
        print(path)
    return 0


def cli() -> int:
    """Console-script entry point with user-facing error handling."""
    try:
        return main()
    except PipelineError as exc:
        print(f"trace-sweep: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(cli())
