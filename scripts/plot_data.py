#!/usr/bin/env python3
"""Turn the researcher's own CSV/XLSX data into journal-ready characterization panels.

Every curve, bar and number comes from the supplied file. The script never
invents, interpolates beyond the data, or "fills in" values: if a column is
missing it stops with a clear message. Computed quantities (T5%, Tmax(DTG),
Segal CrI, modulus, mean +/- SD ...) are printed with their definition so they
can be checked, and optionally written to CSV.

Outputs (same base name): .svg (editable text, svg.fonttype=none), .png
(600 dpi default), .pdf (TrueType fonts), and .caption.txt (caption draft
stating what was plotted, n, error type and data provenance).

Style: Okabe-Ito colour-blind-safe palette, line style + marker also differ per
series (grayscale-safe), Arial/Helvetica 7 pt, journal widths
(single 85 mm, onehalf 114 mm, double 170 mm, or any number in mm),
bold panel letters (a)(b)(c) top-left in panel mode. SciencePlots is used
when installed (--style auto/science) but is optional.

Plot kinds
  ftir     wavenumber axis reversed (4000 -> 400), stacked with offset
  xrd      2-theta increasing, stacked; optional Segal crystallinity index
  tga      mass % vs temperature; optional DTG (twin axis or separate panel);
           T5%, T10%, Tmax(DTG), residue table
  dtg      -dm/dT computed from TGA mass data (for its own panel)
  dsc      heat flow vs temperature, exo up/down marker
  tensile  stress-strain curves; strength, elongation, modulus table
  bar      mean +/- SD/SEM/CI95 from replicates (points overlaid) or from
           mean/sd columns; optional significance letters supplied by the user
  xy       generic line/scatter
  panel    multi-panel figure from a JSON layout file

Data layouts
  wide   first column = x, other numeric columns = one series each (default)
  long   --sample-col NAME : one x column, one y column, a column naming the sample
  pairs  --pairs : columns alternate x1,y1,x2,y2,... (e.g. tensile specimens)
  Lines starting with '#' are comments. Delimiter (, ; tab) is auto-detected.
  The x and y columns actually used are always printed.

Examples
  python plot_data.py --demo-data ./plot-test            (ILLUSTRATIVE test CSVs)
  python plot_data.py ftir spectra.csv --peaks "1650:amide I;1560:amide II" -o fig_ftir
  python plot_data.py ftir spectra.csv --extrema 1700-1600,1100-1000 --xlim 1800,800
  python plot_data.py ftir abs.csv --mode absorbance --offset 0.3 --legend legend
  python plot_data.py xrd xrd.csv --segal 22.6:18.0 --report-csv crI.csv
  python plot_data.py tga tga.csv --dtg panel --dtg-smooth 11 --report-csv tga_table.csv
  python plot_data.py dsc dsc.csv --exo up --ylabel "Heat flow (W g$^{-1}$)"
  python plot_data.py tensile tensile.csv --pairs --modulus-range 0,1
  python plot_data.py bar strength.csv --error sd --sig-letters "a,b,b" --ylabel "Tensile strength (MPa)"
  python plot_data.py bar summary.csv --mean mean --sd sd --n-col n
  python plot_data.py panel layout.json -o figure2

Panel layout JSON (paths relative to the JSON file):
  {"width": "double", "height_mm": 60, "ncols": 3, "output": "figure2",
   "panels": [
     {"kind": "ftir", "file": "ftir.csv", "options": {"peaks": "1650:amide I;1560:amide II"}},
     {"kind": "tga",  "file": "tga.csv",  "options": {"report_csv": "tga_table.csv"}},
     {"kind": "dtg",  "file": "tga.csv",  "options": {"dtg_smooth": 11}}]}
  Any CLI option can be given in "options" (dashes -> underscores); "x", "y",
  "labels", "sample_col" may also sit directly in the panel entry.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.transforms import blended_transform_factory  # noqa: E402

try:  # optional
    import scienceplots  # noqa: F401
    HAVE_SCIENCEPLOTS = True
except Exception:  # pragma: no cover
    HAVE_SCIENCEPLOTS = False

# ----------------------------------------------------------------------------- constants
OKABE_ITO = ["#000000", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#F0E442"]
BAR_COLORS = OKABE_ITO[1:] + OKABE_ITO[:1]          # bars: avoid black (hides error bars)
LINESTYLES = ["-", "--", "-.", ":", (0, (5, 1, 1, 1)), (0, (1, 1)), (0, (8, 2)), (0, (3, 1, 1, 1, 1, 1))]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
HATCHES = ["", "//", "..", "xx", "\\\\", "--", "++", "oo"]
WIDTHS_MM = {"single": 85.0, "onehalf": 114.0, "one-half": 114.0, "1.5": 114.0, "double": 170.0}
MM = 1 / 25.4
KINDS = ["ftir", "xrd", "tga", "dtg", "dsc", "tensile", "bar", "xy"]

DEFAULT_LABELS = {
    "ftir": ("Wavenumber (cm$^{-1}$)", None),
    "xrd": ("2θ (°)", "Intensity (a.u.)"),
    "tga": ("Temperature (°C)", "Mass (%)"),
    "dtg": ("Temperature (°C)", "DTG, −dm/dT (% °C$^{-1}$)"),
    "dsc": ("Temperature (°C)", "Heat flow (a.u.)"),
    "tensile": ("Strain (%)", "Stress (MPa)"),
    "bar": (None, None),
    "xy": (None, None),
}
KIND_NAMES = {"ftir": "FTIR spectra", "xrd": "XRD patterns", "tga": "TGA curves",
              "dtg": "DTG curves", "dsc": "DSC curves", "tensile": "Stress–strain curves",
              "bar": "Bar chart", "xy": "Plot"}


class DataError(Exception):
    """Problem with the user's data or options: reported cleanly, exit code 2."""


@dataclass
class Series:
    label: str
    x: np.ndarray
    y: np.ndarray
    source_cols: str = ""


@dataclass
class Dataset:
    path: Path
    series: list
    xname: str
    ynames: list
    illustrative: bool = False
    notes: list = field(default_factory=list)


# ----------------------------------------------------------------------------- reading
def _sniff_sep(lines):
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#"):
            counts = {sep: s.count(sep) for sep in ("\t", ";", ",")}
            best = max(counts, key=counts.get)
            return best if counts[best] > 0 else r"\s+"
    raise DataError("file contains no data lines")


def read_table(path, sheet=None, decimal="."):
    p = Path(path)
    if not p.exists():
        raise DataError(f"file not found: {p}")
    ext = p.suffix.lower()
    illustrative = p.name.upper().startswith("ILLUSTRATIVE")
    if ext in (".xlsx", ".xlsm", ".xls"):
        try:
            df = pd.read_excel(p, sheet_name=sheet if sheet is not None else 0, comment="#")
        except ImportError as e:
            raise DataError(f"reading Excel needs the 'openpyxl' package ({e}). Install it in your "
                            "environment or save the sheet as CSV.")
    else:
        with open(p, "r", encoding="utf-8-sig", errors="replace") as fh:
            lines = fh.readlines()
        illustrative |= any(l.lstrip().startswith("#") and "ILLUSTRATIVE" in l.upper() for l in lines[:20])
        sep = _sniff_sep(lines)
        if decimal == "," and sep == ",":
            raise DataError("decimal ',' with ',' delimiter is ambiguous; use ';' or tab as delimiter")
        df = pd.read_csv(p, comment="#", sep=sep, decimal=decimal, engine="python",
                         skipinitialspace=True, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if df.empty:
        raise DataError(f"no data rows in {p}")
    return df, illustrative


def find_col(df, name, path):
    name = str(name).strip()
    if name in df.columns:
        return name
    low = {c.lower(): c for c in df.columns}
    if name.lower() in low:
        return low[name.lower()]
    if name.isdigit() and int(name) < len(df.columns):   # allow 0-based index
        return df.columns[int(name)]
    raise DataError(f"column '{name}' not found in {Path(path).name}. Available columns: "
                    + ", ".join(repr(c) for c in df.columns))


def as_list(v):
    if v is None or v == "":
        return None
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v]
    sep = ";" if ";" in str(v) else ","
    return [s.strip() for s in str(v).split(sep) if s.strip()]


def numeric(s):
    return pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)


def load_dataset(path, opt):
    df, illustrative = read_table(path, opt.sheet, opt.decimal)
    notes = []
    series = []
    ylist = as_list(opt.y)
    if opt.pairs:
        cols = list(df.columns)
        if len(cols) % 2:
            raise DataError(f"--pairs needs an even number of columns; {Path(path).name} has {len(cols)}")
        for i in range(0, len(cols), 2):
            series.append(Series(cols[i + 1], numeric(df[cols[i]]), numeric(df[cols[i + 1]]),
                                 f"{cols[i]} / {cols[i + 1]}"))
        xname = cols[0]
    else:
        xname = find_col(df, opt.x, path) if opt.x else df.columns[0]
        if opt.sample_col:
            sc = find_col(df, opt.sample_col, path)
            if ylist:
                if len(ylist) != 1:
                    raise DataError("long format (--sample-col) takes exactly one --y column")
                ycol = find_col(df, ylist[0], path)
            else:
                cand = [c for c in df.columns if c not in (xname, sc) and np.isfinite(numeric(df[c])).any()]
                if not cand:
                    raise DataError("no numeric y column found besides x and sample columns")
                ycol = cand[0]
            for name, g in df.groupby(sc, sort=False):
                series.append(Series(str(name), numeric(g[xname]), numeric(g[ycol]), f"{xname} / {ycol}"))
        else:
            if ylist:
                ycols = [find_col(df, c, path) for c in ylist]
            else:
                ycols = []
                for c in df.columns:
                    if c == xname:
                        continue
                    if np.isfinite(numeric(df[c])).any():
                        ycols.append(c)
                    else:
                        notes.append(f"skipped non-numeric column '{c}'")
            if not ycols:
                raise DataError(f"no numeric y columns found in {Path(path).name}")
            xv = numeric(df[xname])
            for c in ycols:
                series.append(Series(c, xv, numeric(df[c]), f"{xname} / {c}"))
    # drop non-finite points per series (never filled)
    clean = []
    for s in series:
        ok = np.isfinite(s.x) & np.isfinite(s.y)
        if (~ok).sum():
            notes.append(f"'{s.label}': {int((~ok).sum())} empty/non-numeric rows ignored")
        if ok.sum() == 0:
            raise DataError(f"series '{s.label}' has no numeric data")
        clean.append(Series(s.label, s.x[ok], s.y[ok], s.source_cols))
    labels = as_list(opt.labels)
    if labels:
        if len(labels) != len(clean):
            raise DataError(f"--labels gives {len(labels)} names but {len(clean)} series were found: "
                            + ", ".join(s.label for s in clean))
        for s, l in zip(clean, labels):
            s.label = l
    ds = Dataset(Path(path), clean, xname, [s.source_cols for s in clean], illustrative, notes)
    print(f"[{Path(path).name}] x = '{xname}'; series: "
          + "; ".join(f"{s.label} <- {s.source_cols} (n={len(s.x)})" for s in clean))
    for n in notes:
        print(f"  note: {n}")
    if illustrative:
        print("  WARNING: this file is ILLUSTRATIVE synthetic data, not measurements.")
    return ds


# ----------------------------------------------------------------------------- helpers
def parse_pairs(spec, what):
    """'a:b' -> (a, b) floats."""
    try:
        a, b = str(spec).split(":")
        return float(a), float(b)
    except Exception:
        raise DataError(f"{what} must look like 22.6:18.0, got {spec!r}")


def parse_range(spec, what):
    if isinstance(spec, (list, tuple)) and len(spec) == 2:
        return float(spec[0]), float(spec[1])
    s = str(spec).strip()
    for sep in (",", ":", "-"):
        parts = s.split(sep) if sep != "-" else s.lstrip("-").split("-", 1)
        if len(parts) == 2:
            try:
                a = float(parts[0]) * (-1 if (sep == "-" and s.startswith("-")) else 1)
                return a, float(parts[1])
            except ValueError:
                continue
    raise DataError(f"{what}: cannot read range {spec!r} (use e.g. 1700-1600 or 0,2)")


def parse_ranges(spec, what):
    """'1700-1600,1100-1000' (or JSON list of pairs) -> [(a, b), ...]."""
    if spec is None or spec == "":
        return []
    items = spec if isinstance(spec, (list, tuple)) else [i for i in str(spec).replace(";", ",").split(",") if i.strip()]
    return [parse_range(i, what) for i in items]


def parse_peaks(spec):
    """'1650:amide I;1560:amide II' or '1650,1560' or JSON list/dict -> [(pos, label)]."""
    if not spec:
        return []
    out = []
    if isinstance(spec, dict):
        items = list(spec.items())
    elif isinstance(spec, (list, tuple)):
        items = [tuple(i) if isinstance(i, (list, tuple)) else (i, None) for i in spec]
    else:
        s = str(spec)
        sep = ";" if ";" in s else ","
        items = []
        for part in s.split(sep):
            if not part.strip():
                continue
            pos, _, lab = part.partition(":")
            items.append((pos, lab.strip().strip('"').strip("'") or None))
    for pos, lab in items:
        try:
            p = float(pos)
        except ValueError:
            raise DataError(f"--peaks: '{pos}' is not a number")
        out.append((p, lab if lab else f"{p:g}"))
    return out


def parse_width(w):
    if w is None:
        return None
    if isinstance(w, (int, float)):
        return float(w)
    s = str(w).strip().lower().replace("mm", "")
    if s in WIDTHS_MM:
        return WIDTHS_MM[s]
    try:
        return float(s)
    except ValueError:
        raise DataError(f"width must be single, onehalf, double or a number in mm, got {w!r}")


def style_kw(i, n_points, opt, n_series=1):
    kw = dict(color=OKABE_ITO[i % 8], ls=LINESTYLES[i % 8], lw=opt.linewidth)
    if not opt.no_markers and n_points > 1:
        step = max(n_points // 7, 1)
        start = int(step * (i + 0.5) / max(n_series, 1)) % step
        kw.update(marker=MARKERS[i % 8], markevery=(start, step), ms=2.6, mew=0.5,
                  mfc=OKABE_ITO[i % 8] if i % 2 == 0 else "white")
    return kw


def normalize(y, how):
    if how in (None, "none"):
        return y
    if how == "max":
        return y / np.nanmax(np.abs(y))
    if how == "minmax":
        rng = np.nanmax(y) - np.nanmin(y)
        return (y - np.nanmin(y)) / rng if rng else y * 0
    raise DataError(f"unknown --normalize {how!r}")


def set_limits(ax, opt, reverse_x=False, xdata=None):
    if opt.xlim:
        a, b = parse_range(opt.xlim, "--xlim")
        lo, hi = min(a, b), max(a, b)
    elif xdata is not None:
        lo, hi = float(np.min(xdata)), float(np.max(xdata))
    else:
        lo = hi = None
    if lo is not None:
        ax.set_xlim((hi, lo) if reverse_x else (lo, hi))
    if opt.ylim:
        ax.set_ylim(*parse_range(opt.ylim, "--ylim"))


def finish_labels(ax, opt, kind, ydefault=None, xdefault=None):
    dx, dy = DEFAULT_LABELS.get(kind, (None, None))
    ax.set_xlabel(opt.xlabel or xdefault or dx or "x")
    ax.set_ylabel(opt.ylabel or ydefault or dy or "y")


# Labels whose placement depends on the final axes size are placed after the
# layout is frozen (constrained layout first, then these hooks).
POST_LAYOUT = []


def run_post_layout():
    while POST_LAYOUT:
        POST_LAYOUT.pop(0)()


def _spread(vals, minsep, lo=None, hi=None, iters=200):
    """Push 1-D positions apart so neighbours are >= minsep (keeps order)."""
    v = np.array(vals, float)
    order = np.argsort(v)
    w = v[order].copy()
    for _ in range(iters):
        moved = False
        for k in range(len(w) - 1):
            gap = w[k + 1] - w[k]
            if gap < minsep - 1e-9:
                d = (minsep - gap) / 2
                w[k] -= d
                w[k + 1] += d
                moved = True
        if lo is not None and len(w) and w[0] < lo:
            w += lo - w[0]
        if hi is not None and len(w) and w[-1] > hi:
            w -= w[-1] - hi
        if not moved:
            break
    out = np.empty_like(w)
    out[order] = w
    return out


def _axes_pts(ax):
    bb = ax.get_window_extent()
    k = 72 / ax.figure.dpi
    return bb.width * k, bb.height * k


def place_peak_labels(ax, peaks, fs):
    """Rotated labels at the top of user-given peak guides; nudged apart if crowded."""
    def hook():
        trans = blended_transform_factory(ax.transData, ax.transAxes)
        k = 72 / ax.figure.dpi
        xd = np.array([ax.transData.transform((p, 0))[0] for p, _ in peaks]) * k
        bb = ax.get_window_extent()
        new = _spread(xd, (fs - 1) * 1.3, bb.x0 * k + fs, bb.x1 * k - fs)
        for (pos, lab), a, b in zip(peaks, xd, new):
            ax.annotate(lab, xy=(pos, 0.985), xycoords=trans, xytext=(b - a, 0), textcoords="offset points",
                        rotation=90, ha="center", va="top", fontsize=fs - 1, color="0.25",
                        bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.9))
    POST_LAYOUT.append(hook)


def place_inline_labels(ax, labels, xs, ys, colors, fs, avoid_x=(), top_bound=None):
    """Label stacked curves directly: for each curve pick the left-most window where
    the text fits above it without touching the curve above (curves listed top first)."""
    def hook():
        wpt, hpt = _axes_pts(ax)
        xl, yl = ax.get_xlim(), ax.get_ylim()
        lo, hi = sorted(xl)
        rev = xl[0] > xl[1]
        yr = yl[1] - yl[0]
        tfs = fs - 0.5
        th = tfs * 1.25 / hpt * yr
        pad = 1.2 / hpt * yr
        for i, (lab, x, y) in enumerate(zip(labels, xs, ys)):
            tw = (len(lab) * tfs * 0.56 + 2) / wpt * (hi - lo)
            above = (xs[i - 1], ys[i - 1]) if i > 0 else None
            bound = top_bound if (i == 0 and top_bound is not None) else yl[1]
            best = None
            for st in np.linspace(0, max((hi - lo) - tw, 0), 80):
                a, b = (hi - st - tw, hi - st) if rev else (lo + st, lo + st + tw)
                m = (x >= a) & (x <= b)
                if not m.any():
                    continue
                if any(a - 0.01 * (hi - lo) <= p <= b + 0.01 * (hi - lo) for p in avoid_x):
                    continue
                base = np.max(y[m]) + pad
                ceil = bound
                if above is not None:
                    ma = (above[0] >= a) & (above[0] <= b)
                    if ma.any():
                        ceil = min(ceil, np.min(above[1][ma]))
                clear = ceil - (base + th)
                if clear >= 0.4 * th:
                    best = (a, b, base, clear)
                    break
                if best is None or clear > best[3]:
                    best = (a, b, base, clear)
            if best is None:
                continue
            a, b, base, _ = best
            ax.text(b if rev else a, base, lab, ha="left", va="bottom", color=colors[i], fontsize=tfs)
    POST_LAYOUT.append(hook)


def place_peak_values(ax, xs, ys, texts, colors, fs):
    """Numbers for curve maxima (e.g. Tmax), set to the right of the right-most peak,
    spread vertically, each with a thin leader to its own peak."""
    def hook():
        k = 72 / ax.figure.dpi
        disp = np.array([ax.transData.transform((x, y)) for x, y in zip(xs, ys)]) * k
        xr = disp[:, 0].max() + 9
        ny = _spread(disp[:, 1], (fs - 1.5) * 1.3)
        for (x, y), d, yy, t, c in zip(zip(xs, ys), disp, ny, texts, colors):
            ax.annotate(t, (x, y), xytext=(xr - d[0], yy - d[1]), textcoords="offset points", ha="left",
                        va="center", fontsize=fs - 1.5, color=c,
                        arrowprops=dict(arrowstyle="-", lw=0.4, color=c, shrinkA=0.5, shrinkB=0.5))
    POST_LAYOUT.append(hook)


def add_legend(ax, opt, stacked, series_artists, ys_plot=None, xs=None, loc="best", avoid_x=(), top_bound=None):
    mode = opt.legend
    if mode == "auto":
        mode = "inline" if stacked else "legend"
    if mode == "none" or not series_artists:
        return
    if mode == "legend":
        ax.legend(loc=opt.legend_loc or loc, frameon=False, handlelength=2.6, borderaxespad=0.3)
        return
    place_inline_labels(ax, [l for _, l in series_artists], xs, ys_plot,
                        [a.get_color() for a, _ in series_artists], opt.font_size, avoid_x, top_bound)


# ----------------------------------------------------------------------------- plotters
def plot_stacked(ax, ds, opt, kind):
    """FTIR / XRD / DSC / generic stacked line plots."""
    n = len(ds.series)
    if kind == "dsc" and opt.invert:
        for s in ds.series:
            s.y = -s.y
    ys = [normalize(s.y, opt.normalize) for s in ds.series]
    if opt.offset in (None, "auto"):
        if kind in ("ftir", "xrd") and n > 1:
            off = 0.9 * max(np.ptp(y) for y in ys)
        else:
            off = 0.0
    else:
        off = float(opt.offset)
    plotted, artists, info = [], [], {"tables": [], "caption": ""}
    for i, (s, y) in enumerate(zip(ds.series, ys)):
        yp = y + (n - 1 - i) * off
        order = np.argsort(s.x)
        line, = ax.plot(s.x[order], yp[order], label=s.label, **style_kw(i, len(s.x), opt, n))
        artists.append((line, s.label))
        plotted.append(yp[order])
    allx = np.concatenate([s.x for s in ds.series])
    if kind == "ftir":
        if opt.xlim:
            set_limits(ax, opt, reverse_x=True)
        else:
            ax.set_xlim(min(4000, allx.max()), max(400, allx.min()))
            if opt.ylim:
                ax.set_ylim(*parse_range(opt.ylim, "--ylim"))
    else:
        set_limits(ax, opt, xdata=allx)

    # --- y label
    if kind == "ftir":
        base = "Transmittance" if opt.mode == "transmittance" else "Absorbance"
        unit = "(%)" if (opt.mode == "transmittance" and off == 0 and opt.normalize in (None, "none")) else "(a.u.)"
        ydef = f"{base} {unit}"
    else:
        ydef = None
    finish_labels(ax, opt, kind, ydefault=ydef)
    if off and not opt.ylabel_keep_ticks:
        ax.set_yticks([])

    # --- user peaks: vertical guides labelled only at user-given positions
    peaks = parse_peaks(opt.peaks)
    top_bound = None
    if peaks:
        lo, hi = ax.get_ylim()
        top_bound = hi
        ax.set_ylim(lo, hi + opt.peak_headroom * (hi - lo))
        for pos, _ in peaks:
            ax.axvline(pos, color="0.55", lw=0.45, ls=(0, (2, 2)), zorder=0)
        place_peak_labels(ax, peaks, opt.font_size)

    # --- auto extrema inside user windows: labelled with measured position only
    windows = parse_ranges(opt.extrema, "--extrema")
    if windows:
        etype = opt.extrema_type
        if etype == "auto":
            etype = "min" if (kind == "ftir" and opt.mode == "transmittance") else "max"
        dec = opt.extrema_decimals if opt.extrema_decimals is not None else (0 if kind == "ftir" else 2)
        rows = []
        for i, (s, y) in enumerate(zip(ds.series, ys)):
            for a, b in windows:
                lo, hi = min(a, b), max(a, b)
                m = (s.x >= lo) & (s.x <= hi)
                if not m.any():
                    print(f"  note: no data of '{s.label}' in window {lo:g}-{hi:g}")
                    continue
                idx = np.where(m)[0]
                j = idx[np.argmin(y[idx])] if etype == "min" else idx[np.argmax(y[idx])]
                xv, yv = s.x[j], y[j] + (n - 1 - i) * off
                ax.plot([xv], [yv], marker="^" if etype == "min" else "v", ms=2.4,
                        color=OKABE_ITO[i % 8], ls="none", zorder=4)
                ax.annotate(f"{xv:.{dec}f}", (xv, yv), xytext=(0, -3.5 if etype == "min" else 3.5),
                            textcoords="offset points", ha="center",
                            va="top" if etype == "min" else "bottom",
                            fontsize=opt.font_size - 1.5, color=OKABE_ITO[i % 8])
                rows.append({"sample": s.label, "window": f"{lo:g}-{hi:g}", "position": xv,
                             "value": s.y[j], "type": etype})
        tab = pd.DataFrame(rows)
        print(f"  local {etype}ima found in user windows (position = data point with the extreme value):")
        print(tab.to_string(index=False))
        info["tables"].append(("Local extrema in user-specified windows", tab))

    # --- Segal crystallinity index (XRD)
    if kind == "xrd" and opt.segal:
        p200, pam = parse_pairs(opt.segal, "--segal")
        w = opt.segal_window
        rows = []
        for s in ds.series:
            m1 = np.abs(s.x - p200) <= w
            m2 = np.abs(s.x - pam) <= w
            if not m1.any() or not m2.any():
                raise DataError(f"Segal: '{s.label}' has no data within ±{w}° of {p200}° or {pam}°")
            i1 = np.where(m1)[0][np.argmax(s.y[m1])]
            i2 = np.where(m2)[0][np.argmin(s.y[m2])]
            I200, Iam = s.y[i1], s.y[i2]
            rows.append({"sample": s.label, "2theta_I200": s.x[i1], "I200": I200,
                         "2theta_Iam": s.x[i2], "Iam": Iam, "CrI_percent": (I200 - Iam) / I200 * 100})
        tab = pd.DataFrame(rows)
        print(f"  Segal CrI = (I200 − Iam) / I200 × 100; I200 = max within ±{w}° of {p200}°, "
              f"Iam = min within ±{w}° of {pam}° (raw intensities, no background subtraction)")
        print(tab.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
        info["tables"].append((f"Segal crystallinity index, CrI = (I200 − Iam)/I200 × 100 "
                               f"(I200: max within ±{w}° of {p200}°; Iam: min within ±{w}° of {pam}°; "
                               "raw intensities)", tab))

    if kind == "dsc":
        _exo_marker(ax, opt)

    stacked = off != 0
    add_legend(ax, opt, stacked, artists, plotted, [np.sort(s.x) for s in ds.series],
               avoid_x=[p for p, _ in peaks], top_bound=top_bound)

    names = ", ".join(s.label for s in ds.series)
    cap = f"{KIND_NAMES[kind]} of {names}"
    if kind == "ftir":
        cap += f" ({opt.mode})"
    if opt.normalize not in (None, "none"):
        cap += f", each normalized ({opt.normalize})"
    if stacked:
        cap += f"; curves offset vertically by {off:.3g} for clarity"
    if kind == "dsc":
        cap += f"; exothermic {opt.exo}" + (" (sign inverted from the file)" if opt.invert else "")
    if peaks:
        cap += "; dashed lines mark " + ", ".join(f"{l} ({p:g})" for p, l in peaks)
    if windows:
        cap += "; marked positions are the measured local extrema within the stated windows"
    info["caption"] = cap
    return info


def _exo_marker(ax, opt):
    up = opt.exo == "up"
    ax.annotate("", xy=(0.06, 0.95 if up else 0.78), xytext=(0.06, 0.78 if up else 0.95),
                xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", lw=0.6, color="black", mutation_scale=6))
    ax.text(0.085, 0.865, "Exo", transform=ax.transAxes, va="center", ha="left", fontsize=opt.font_size - 0.5)


def _tga_arrays(s, opt):
    order = np.argsort(s.x)
    T, m = s.x[order], s.y[order]
    if len(np.unique(T)) < len(T):   # collapse duplicate temperatures by averaging
        d = pd.DataFrame({"T": T, "m": m}).groupby("T", sort=True)["m"].mean()
        T, m = d.index.to_numpy(float), d.to_numpy(float)
    if opt.tga_normalize:
        m = m / m[0] * 100
    return T, m


def compute_dtg(T, m, smooth):
    ms = m
    if smooth and smooth > 2:
        from scipy.signal import savgol_filter
        w = int(smooth) | 1
        if w >= len(m):
            raise DataError(f"--dtg-smooth {smooth} is larger than the number of points ({len(m)})")
        ms = savgol_filter(m, w, 2)
    return -np.gradient(ms, T)


def _t_at_loss(T, m, loss, ref):
    target = ref * (1 - loss / 100.0)
    below = np.where(m <= target)[0]
    if not len(below):
        return np.nan
    j = below[0]
    if j == 0:
        return T[0]
    # linear interpolation between the two bracketing measured points
    return T[j - 1] + (target - m[j - 1]) * (T[j] - T[j - 1]) / (m[j] - m[j - 1])


def tga_metrics(ds, opt):
    rows = []
    windows = parse_ranges(opt.tmax_windows, "--tmax-windows")
    for s in ds.series:
        T, m = _tga_arrays(s, opt)
        if opt.tga_ref_temp is not None:
            if opt.tga_ref_temp < T[0] or opt.tga_ref_temp > T[-1]:
                raise DataError(f"--tga-ref-temp {opt.tga_ref_temp} outside data range of '{s.label}'")
            ref = float(np.interp(opt.tga_ref_temp, T, m))
        else:
            ref = m[0]
        dtg = compute_dtg(T, m, opt.dtg_smooth)
        row = {"sample": s.label, "T5_C": _t_at_loss(T, m, 5, ref), "T10_C": _t_at_loss(T, m, 10, ref)}
        if windows:
            for a, b in windows:
                lo, hi = min(a, b), max(a, b)
                msk = (T >= lo) & (T <= hi)
                row[f"Tmax_DTG_{lo:g}-{hi:g}_C"] = T[msk][np.argmax(dtg[msk])] if msk.any() else np.nan
        else:
            row["Tmax_DTG_C"] = T[np.argmax(dtg)]
        row["DTGmax_pct_per_C"] = float(np.max(dtg))
        row["residue_pct"] = m[-1]
        row["residue_at_C"] = T[-1]
        rows.append(row)
    tab = pd.DataFrame(rows)
    ref_txt = f"mass at {opt.tga_ref_temp:g} °C" if opt.tga_ref_temp is not None else "first data point"
    defs = (f"T5%/T10%: temperature at 5/10 % mass loss relative to the {ref_txt} (linear interpolation "
            f"between bracketing data points); Tmax(DTG): temperature of maximum −dm/dT"
            + (f" (Savitzky–Golay smoothing, {int(opt.dtg_smooth) | 1}-point window, order 2)" if opt.dtg_smooth else "")
            + "; residue: mass at the highest measured temperature")
    print("  TGA values computed from the data:")
    print("  " + defs)
    print(tab.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    return tab, defs


def plot_tga(ax, ds, opt, kind="tga"):
    info = {"tables": [], "caption": ""}
    artists, n = [], len(ds.series)
    allT = []
    for i, s in enumerate(ds.series):
        T, m = _tga_arrays(s, opt)
        allT.append(T)
        line, = ax.plot(T, m, label=s.label, **style_kw(i, len(T), opt, n))
        artists.append((line, s.label))
    set_limits(ax, opt, xdata=np.concatenate(allT))
    finish_labels(ax, opt, "tga")
    if opt.dtg == "twin":
        ax2 = ax.twinx()
        for i, s in enumerate(ds.series):
            T, m = _tga_arrays(s, opt)
            ax2.plot(T, compute_dtg(T, m, opt.dtg_smooth), color=OKABE_ITO[i % 8], ls=LINESTYLES[i % 8],
                     lw=opt.linewidth * 0.7, alpha=0.75)
        ax2.set_ylabel(DEFAULT_LABELS["dtg"][1])
        ax2.set_ylim(bottom=min(0, ax2.get_ylim()[0]))
    add_legend(ax, opt, False, artists, loc="lower left")
    tab, defs = tga_metrics(ds, opt)
    info["tables"].append(("TGA values: " + defs, tab))
    cap = f"TGA curves (mass vs temperature) of {', '.join(s.label for s in ds.series)}"
    if opt.tga_normalize:
        cap += ", mass normalized to the first data point (100 %)"
    if opt.dtg == "twin":
        cap += "; thin lines (right axis): DTG computed as −dm/dT from the same data"
    info["caption"] = cap
    return info


def plot_dtg(ax, ds, opt, kind="dtg"):
    info = {"tables": [], "caption": ""}
    artists, allT, n, peaks_xy = [], [], len(ds.series), []
    for i, s in enumerate(ds.series):
        T, m = _tga_arrays(s, opt)
        d = compute_dtg(T, m, opt.dtg_smooth)
        allT.append(T)
        line, = ax.plot(T, d, label=s.label, **style_kw(i, len(T), opt, n))
        artists.append((line, s.label))
        j = int(np.argmax(d))
        peaks_xy.append((T[j], d[j], f"{T[j]:.0f}", OKABE_ITO[i % 8]))
    set_limits(ax, opt, xdata=np.concatenate(allT))
    finish_labels(ax, opt, "dtg")
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + 0.08 * (hi - lo))
    add_legend(ax, opt, False, artists, loc="best")  # "best" also avoids the Tmax labels
    if not opt.no_tmax_marks and peaks_xy:
        place_peak_values(ax, *zip(*peaks_xy), opt.font_size)
    smooth = (f" after Savitzky–Golay smoothing ({int(opt.dtg_smooth) | 1}-point window, order 2)"
              if opt.dtg_smooth else "")
    info["caption"] = (f"DTG curves (−dm/dT, computed by numerical differentiation of the TGA mass data{smooth}) "
                       f"of {', '.join(s.label for s in ds.series)}"
                       + ("" if opt.no_tmax_marks else "; numbers give the temperature of maximum rate (°C)"))
    return info


def plot_tensile(ax, ds, opt, kind="tensile"):
    info = {"tables": [], "caption": ""}
    artists, n, rows = [], len(ds.series), []
    factor = {"percent": 100.0, "fraction": 1.0}[opt.strain_unit]
    mr = parse_range(opt.modulus_range, "--modulus-range") if opt.modulus_range else None
    for i, s in enumerate(ds.series):
        line, = ax.plot(s.x, s.y, label=s.label, **style_kw(i, len(s.x), opt, n))
        artists.append((line, s.label))
        jmax = int(np.argmax(s.y))
        keep = np.where(s.y >= opt.break_frac * s.y[jmax])[0]
        jb = keep[-1]
        row = {"sample": s.label, "strength_MPa": s.y[jmax], "strain_at_max": s.x[jmax],
               "strain_at_break": s.x[jb]}
        if mr:
            lo, hi = sorted(mr)
            msk = (s.x >= lo) & (s.x <= hi)
            if msk.sum() < 3:
                raise DataError(f"modulus range {lo:g}-{hi:g} holds <3 points for '{s.label}'")
            slope, icpt = np.polyfit(s.x[msk], s.y[msk], 1)
            row["E_MPa"] = slope * factor
            row["fit_points"] = int(msk.sum())
        rows.append(row)
    set_limits(ax, opt)
    finish_labels(ax, opt, "tensile", xdefault="Strain (%)" if opt.strain_unit == "percent" else "Strain (–)")
    if not opt.ylim:
        ax.set_ylim(bottom=0)
    if not opt.xlim:
        ax.set_xlim(left=0)
    add_legend(ax, opt, False, artists, loc="upper left")
    tab = pd.DataFrame(rows)
    defs = ("strength = maximum stress; strain at break = last point with stress ≥ "
            f"{opt.break_frac:g} × max" + (f"; E = slope of a linear least-squares fit for strain "
                                           f"{mr[0]:g}–{mr[1]:g} (stress assumed in MPa, strain in {opt.strain_unit})"
                                           if mr else ""))
    print("  Tensile values computed from the data: " + defs)
    print(tab.to_string(index=False, float_format=lambda v: f"{v:.3g}"))
    info["tables"].append(("Tensile values: " + defs, tab))
    info["caption"] = f"Representative stress–strain curves of {', '.join(s.label for s in ds.series)}"
    return info


def plot_xy(ax, ds, opt, kind="xy"):
    info = {"tables": [], "caption": ""}
    artists, n = [], len(ds.series)
    for i, s in enumerate(ds.series):
        kw = style_kw(i, len(s.x), opt, n)
        if opt.scatter:
            kw.update(ls="none", marker=MARKERS[i % 8], markevery=None, ms=3)
            line, = ax.plot(s.x, s.y, label=s.label, **kw)
        else:
            o = np.argsort(s.x)
            line, = ax.plot(s.x[o], s.y[o], label=s.label, **kw)
        artists.append((line, s.label))
    if opt.logx:
        ax.set_xscale("log")
    if opt.logy:
        ax.set_yscale("log")
    set_limits(ax, opt)
    finish_labels(ax, opt, "xy", xdefault=ds.xname,
                  ydefault=ds.series[0].label if n == 1 else None)
    if n > 1 or opt.legend == "legend":
        add_legend(ax, opt, False, artists)
    info["caption"] = f"{', '.join(s.label for s in ds.series)} versus {ds.xname}"
    return info


# --- bar
def load_bar(path, opt):
    df, illustrative = read_table(path, opt.sheet, opt.decimal)
    groups = []
    if opt.mean:
        gcol = find_col(df, opt.x, path) if opt.x else df.columns[0]
        mcol = find_col(df, opt.mean, path)
        if not opt.sd:
            raise DataError("--mean needs --sd (the error column) as well")
        scol = find_col(df, opt.sd, path)
        ncol = find_col(df, opt.n_col, path) if opt.n_col else None
        for _, r in df.iterrows():
            groups.append({"name": str(r[gcol]), "values": None, "mean": float(r[mcol]), "err": float(r[scol]),
                           "n": int(r[ncol]) if ncol else None})
        layout = f"group = '{gcol}', mean = '{mcol}', error = '{scol}'" + (f", n = '{ncol}'" if ncol else "")
    elif opt.sample_col:
        sc = find_col(df, opt.sample_col, path)
        yl = as_list(opt.y)
        ycol = find_col(df, yl[0], path) if yl else \
            [c for c in df.columns if c != sc and np.isfinite(numeric(df[c])).any()][0]
        for name, g in df.groupby(sc, sort=False):
            groups.append({"name": str(name), "values": numeric(g[ycol])})
        layout = f"long format: group = '{sc}', values = '{ycol}'"
    else:
        first = df.columns[0]
        first_numeric = np.isfinite(numeric(df[first])).mean() > 0.5
        if not first_numeric and opt.orient != "columns":
            yl = as_list(opt.y)
            vcols = [find_col(df, c, path) for c in yl] if yl else \
                [c for c in df.columns[1:] if np.isfinite(numeric(df[c])).any()]
            for _, r in df.iterrows():
                groups.append({"name": str(r[first]), "values": numeric(r[vcols])})
            layout = f"rows = groups (names from '{first}'), replicate columns = {vcols}"
        else:
            yl = as_list(opt.y)
            vcols = [find_col(df, c, path) for c in yl] if yl else list(df.columns)
            for c in vcols:
                groups.append({"name": c, "values": numeric(df[c])})
            layout = f"columns = groups ({vcols}), rows = replicates"
    from scipy import stats
    for g in groups:
        if g["values"] is not None:
            v = g["values"][np.isfinite(g["values"])]
            g["values"] = v
            g["n"] = len(v)
            if len(v) == 0:
                raise DataError(f"group '{g['name']}' has no numeric values")
            g["mean"] = float(np.mean(v))
            sd = float(np.std(v, ddof=1)) if len(v) > 1 else np.nan
            g["sd"] = sd
            g["err"] = {"sd": sd, "sem": sd / math.sqrt(len(v)),
                        "ci95": (stats.t.ppf(0.975, len(v) - 1) * sd / math.sqrt(len(v))) if len(v) > 1 else np.nan
                        }[opt.error]
            if len(v) < 2:
                print(f"  WARNING: group '{g['name']}' has n = {len(v)}; no error bar can be computed")
    labels = as_list(opt.labels)
    if labels:
        if len(labels) != len(groups):
            raise DataError(f"--labels gives {len(labels)} names for {len(groups)} groups")
        for g, l in zip(groups, labels):
            g["name"] = l
    print(f"[{Path(path).name}] bar data: {layout}")
    if illustrative:
        print("  WARNING: this file is ILLUSTRATIVE synthetic data, not measurements.")
    return groups, illustrative


def plot_bar(ax, groups, opt, kind="bar"):
    info = {"tables": [], "caption": ""}
    xpos = np.arange(len(groups))
    rng = np.random.default_rng(1)
    tops = []
    for i, g in enumerate(groups):
        ax.bar(xpos[i], g["mean"], width=0.62, color=BAR_COLORS[i % 8], alpha=0.85, edgecolor="black",
               lw=0.6, hatch=HATCHES[i % 8] if opt.hatch else None, zorder=1)
        err = g["err"] if np.isfinite(g.get("err", np.nan)) else 0
        if err:
            ax.errorbar(xpos[i], g["mean"], yerr=err, color="black", lw=0.7, capsize=2.2, capthick=0.7, zorder=3)
        top = g["mean"] + err
        if g["values"] is not None and not opt.no_points:
            jit = rng.uniform(-0.13, 0.13, len(g["values"]))
            ax.plot(xpos[i] + jit, g["values"], ls="none", marker="o", ms=2.6, mfc="white", mec="black",
                    mew=0.6, zorder=4)
            top = max(top, float(np.max(g["values"])))
        tops.append(top)
    letters = as_list(opt.sig_letters)
    if letters:
        if len(letters) != len(groups):
            raise DataError(f"--sig-letters gives {len(letters)} letters for {len(groups)} groups")
        for i, l in enumerate(letters):
            ax.annotate(l, (xpos[i], tops[i]), xytext=(0, 2.5), textcoords="offset points", ha="center",
                        va="bottom", fontsize=opt.font_size)
    ax.set_xticks(xpos, [g["name"] for g in groups])
    if np.mean([len(g["name"]) for g in groups]) > 9:
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")
    ax.tick_params(axis="x", which="both", length=0)
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    if all(g["mean"] - (g["err"] if np.isfinite(g["err"]) else 0) >= 0 for g in groups):
        ax.set_ylim(bottom=0)
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + (0.08 if letters else 0.03) * (hi - lo))
    if opt.ylim:
        ax.set_ylim(*parse_range(opt.ylim, "--ylim"))
    ax.set_xlabel(opt.xlabel or "")
    ax.set_ylabel(opt.ylabel or "Value")
    if not opt.ylabel:
        print("  note: pass --ylabel with the quantity and unit, e.g. 'Tensile strength (MPa)'")
    rows = [{"group": g["name"], "n": g["n"], "mean": g["mean"],
             "sd": g.get("sd", np.nan), "error_plotted": g["err"]} for g in groups]
    tab = pd.DataFrame(rows)
    print(tab.to_string(index=False, float_format=lambda v: f"{v:.4g}"))
    supplied = opt.mean is not None
    etxt = {"sd": "standard deviation (SD)", "sem": "standard error of the mean (SEM)",
            "ci95": "95 % confidence interval (t-distribution)"}[opt.error]
    ns = sorted({g["n"] for g in groups if g["n"] is not None})
    ntxt = (f"n = {ns[0]}" if len(ns) == 1 else f"n = {', '.join(map(str, ns))} per group") if ns else "n not supplied"
    cap = (f"Bar chart of {opt.ylabel or 'the measured value'} for {', '.join(g['name'] for g in groups)}. "
           + (f"Bars and error bars are the mean and error values as supplied in the file ({ntxt}; "
              f"error type stated by the user as {etxt})" if supplied else
              f"Bars show mean ± {etxt} ({ntxt}); open circles are individual replicate values"
              if not opt.no_points else f"Bars show mean ± {etxt} ({ntxt})"))
    if letters:
        cap += ("; letters above bars were supplied by the user (groups sharing a letter are not "
                "significantly different) — state the test and α here; this script did not run a test")
    info["caption"] = cap
    info["tables"].append(("Bar values", tab))
    return info


PLOTTERS = {
    "ftir": lambda ax, ds, o: plot_stacked(ax, ds, o, "ftir"),
    "xrd": lambda ax, ds, o: plot_stacked(ax, ds, o, "xrd"),
    "dsc": lambda ax, ds, o: plot_stacked(ax, ds, o, "dsc"),
    "tga": plot_tga, "dtg": plot_dtg, "tensile": plot_tensile, "xy": plot_xy, "bar": plot_bar,
}


def draw_panel(ax, kind, path, opt):
    if kind == "bar":
        groups, illus = load_bar(path, opt)
        info = plot_bar(ax, groups, opt)
        n_desc = f"{len(groups)} groups"
    else:
        ds = load_dataset(path, opt)
        info = PLOTTERS[kind](ax, ds, opt)
        illus = ds.illustrative
        n_desc = f"{len(ds.series)} {'curve' if len(ds.series) == 1 else 'curves'}"
    info.update(path=Path(path), illustrative=illus, n_desc=n_desc, kind=kind)
    if opt.report_csv and info["tables"]:
        out = Path(opt.report_csv)
        frames = [t for _, t in info["tables"]]
        pd.concat(frames, ignore_index=True).to_csv(out, index=False)
        with open(out, "r", encoding="utf-8") as fh:
            body = fh.read()
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("# values computed by plot_data.py from " + Path(path).name + "\n")
            for t, _ in info["tables"]:
                fh.write("# " + t + "\n")
            if illus:
                fh.write("# WARNING: source is ILLUSTRATIVE synthetic data, not measurements\n")
            fh.write(body)
        print(f"  wrote {out}")
    return info


# ----------------------------------------------------------------------------- figure handling
def apply_style(opt):
    plt.rcdefaults()
    style = opt.style
    if style == "science" and not HAVE_SCIENCEPLOTS:
        print("  note: SciencePlots not installed; using built-in style")
    if style in ("auto", "science") and HAVE_SCIENCEPLOTS:
        plt.style.use(["science", "no-latex"])
    fs = opt.font_size
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
        "mathtext.default": "regular",
        "font.size": fs, "axes.labelsize": fs, "axes.titlesize": fs,
        "xtick.labelsize": fs - 1, "ytick.labelsize": fs - 1, "legend.fontsize": fs - 1,
        "axes.linewidth": 0.6, "lines.linewidth": opt.linewidth,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.minor.width": 0.45,
        "ytick.minor.width": 0.45, "xtick.major.size": 2.8, "ytick.major.size": 2.8,
        "xtick.minor.size": 1.6, "ytick.minor.size": 1.6,
        "xtick.direction": "in", "ytick.direction": "in", "xtick.top": False, "ytick.right": False,
        "axes.prop_cycle": matplotlib.cycler(color=OKABE_ITO),
        "legend.frameon": False, "axes.unicode_minus": True,
        "svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42,
        "savefig.dpi": opt.dpi, "figure.dpi": 100, "axes.grid": False,
        "text.usetex": False,
    })


def add_panel_letters(fig, axes_letters, fs):
    """Bold (a)(b)... at the top-left of each panel's full extent (incl. y label)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    pad = 2.0 / 72 / fig.get_figheight()
    for ax, letter in axes_letters:
        bb = ax.get_tightbbox(r)
        x0 = max(inv.transform((bb.x0, 0))[0], 0.004)
        ytop = ax.get_position().y1 + pad
        fig.text(x0, ytop, f"({letter})", fontweight="bold", fontsize=fs + 1, ha="left", va="bottom")


def prepare_letter_space(ax, fs):
    ax.set_title(" ", loc="left", fontsize=fs + 1, fontweight="bold", pad=3)


def save_all(fig, out, opt):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    written = []
    for fmt in as_list(opt.formats):
        p = out.with_suffix(f".{fmt.lower()}") if out.suffix.lower() in (".svg", ".png", ".pdf") \
            else Path(str(out) + f".{fmt.lower()}")
        fig.savefig(p, dpi=opt.dpi if fmt.lower() == "png" else None, facecolor="white")
        written.append(p)
    return written


def write_caption(out, infos, letters=None, width_mm=None, height_mm=None):
    out = Path(out)
    stem = out.with_suffix("") if out.suffix.lower() in (".svg", ".png", ".pdf") else out
    cpath = Path(str(stem) + ".caption.txt")
    lines = ["CAPTION DRAFT (edit before submission; check every statement against your methods)", ""]
    parts = []
    for i, inf in enumerate(infos):
        tag = f"({letters[i]}) " if letters else ""
        parts.append(f"{tag}{inf['caption']} [{inf['n_desc']}].")
    lines.append("Figure X. " + " ".join(parts))
    lines.append("")
    srcs = sorted({str(inf["path"].name) for inf in infos})
    lines.append("Data provenance: all curves, bars and computed values were generated by plot_data.py "
                 "directly from the supplied file(s): " + ", ".join(srcs)
                 + ". No values were added, estimated or smoothed unless stated above.")
    if any(inf["illustrative"] for inf in infos):
        lines.append("")
        lines.append("WARNING: at least one source file is ILLUSTRATIVE synthetic data generated for testing "
                     "(not measurements). Do NOT use this figure or these numbers in a manuscript.")
    tabs = [(t, df) for inf in infos for t, df in inf["tables"]]
    if tabs:
        lines += ["", "Computed values (for checking / for a table in the text):"]
        for t, df in tabs:
            lines += ["", t, df.to_string(index=False, float_format=lambda v: f"{v:.4g}")]
    if width_mm:
        lines += ["", f"Figure size: {width_mm:.0f} × {height_mm:.0f} mm; fonts Arial/Helvetica "
                      "(editable text in SVG/PDF)."]
    cpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return cpath


def run_single(opt):
    kind = opt.kind
    if not opt.file:
        raise DataError(f"'{kind}' needs a data file")
    width = parse_width(opt.width) or WIDTHS_MM["single"]
    two = kind == "tga" and opt.dtg == "panel"
    height = float(opt.height) if opt.height else width * (1.15 if two else 0.72)
    apply_style(opt)
    fig = plt.figure(figsize=(width * MM, height * MM), layout="constrained")
    out = opt.out or str(Path(opt.file).with_suffix("")) + f"_{kind}"
    if two:
        ax1, ax2 = fig.subplots(2, 1, sharex=True)
        prepare_letter_space(ax1, opt.font_size)
        prepare_letter_space(ax2, opt.font_size)
        i1 = draw_panel(ax1, "tga", opt.file, opt)
        ax1.set_xlabel("")
        rc = opt.report_csv
        opt.report_csv = None
        i2 = draw_panel(ax2, "dtg", opt.file, opt)
        opt.report_csv = rc
        infos, letters = [i1, i2], ["a", "b"]
        fig.canvas.draw()
        fig.set_layout_engine("none")
        run_post_layout()
        add_panel_letters(fig, [(ax1, "a"), (ax2, "b")], opt.font_size)
    else:
        ax = fig.subplots()
        if opt.letter:
            prepare_letter_space(ax, opt.font_size)
        infos, letters = [draw_panel(ax, kind, opt.file, opt)], None
        fig.canvas.draw()
        fig.set_layout_engine("none")
        run_post_layout()
        if opt.letter:
            add_panel_letters(fig, [(ax, opt.letter)], opt.font_size)
            letters = [opt.letter]
    files = save_all(fig, out, opt)
    files.append(write_caption(out, infos, letters, width, height))
    plt.close(fig)
    return files


def option_defaults(parser, kind):
    return parser.parse_args([kind, "_"])


def run_panel(opt, parser):
    lpath = Path(opt.file)
    if not lpath.exists():
        raise DataError(f"layout file not found: {lpath}")
    try:
        L = json.loads(lpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise DataError(f"layout JSON is invalid: {e}")
    base = lpath.parent
    panels = L.get("panels")
    if not panels:
        raise DataError("layout JSON needs a non-empty 'panels' list")
    n = len(panels)
    ncols = int(L.get("ncols", 2 if n > 1 else 1))
    nrows = int(L.get("nrows", math.ceil(n / ncols)))
    width = parse_width(opt.width) or parse_width(L.get("width", "double"))
    height = float(opt.height or L.get("height_mm") or width / ncols * 0.8 * nrows)
    gopt = option_defaults(parser, "xy")
    for k in ("font_size", "dpi", "formats", "style", "linewidth", "no_markers"):
        if k in L:
            setattr(gopt, k, L[k])
        cli = getattr(opt, k)
        if cli != getattr(option_defaults(parser, "xy"), k):
            setattr(gopt, k, cli)
    apply_style(gopt)
    fig = plt.figure(figsize=(width * MM, height * MM), layout="constrained")
    axes = fig.subplots(nrows, ncols, squeeze=False).ravel()
    valid = set(vars(option_defaults(parser, "xy")))
    infos, letters, pairs = [], [], []
    for i, p in enumerate(panels):
        kind = p.get("kind")
        if kind not in KINDS:
            raise DataError(f"panel {i + 1}: kind must be one of {KINDS}, got {kind!r}")
        if "file" not in p:
            raise DataError(f"panel {i + 1}: missing 'file'")
        po = option_defaults(parser, kind)
        for k in ("font_size", "linewidth", "no_markers", "style"):
            setattr(po, k, getattr(gopt, k))
        merged = {k: v for k, v in p.items() if k not in ("kind", "file", "options", "letter")}
        merged.update(p.get("options", {}))
        for k, v in merged.items():
            k2 = k.replace("-", "_")
            if k2 not in valid or k2 in ("kind", "file", "demo_data"):
                raise DataError(f"panel {i + 1}: unknown option '{k}'. Valid: " + ", ".join(sorted(valid)))
            setattr(po, k2, v)
        if po.report_csv:
            po.report_csv = str(base / po.report_csv)
        letter = p.get("letter", "abcdefghijklmnop"[i])
        prepare_letter_space(axes[i], gopt.font_size)
        print(f"--- panel ({letter}): {kind}")
        infos.append(draw_panel(axes[i], kind, base / p["file"], po))
        letters.append(letter)
        pairs.append((axes[i], letter))
    for ax in axes[n:]:
        ax.set_visible(False)
    fig.canvas.draw()
    fig.set_layout_engine("none")
    run_post_layout()
    if not opt.no_panel_letters:
        add_panel_letters(fig, pairs, gopt.font_size)
    out = opt.out or (str(base / L["output"]) if L.get("output") else str(lpath.with_suffix("")))
    files = save_all(fig, out, gopt)
    files.append(write_caption(out, infos, letters, width, height))
    plt.close(fig)
    return files


# ----------------------------------------------------------------------------- demo data
DEMO_HEADER = "# ILLUSTRATIVE synthetic data for testing the script - not measurements\n"


def write_demo_data(d):
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    wn = np.arange(4000, 399, -2.0)
    # (centre cm-1, depth %T, sigma cm-1)
    common = [(2920, 7, 25), (2875, 5, 18), (1420, 6, 15), (1375, 8, 12), (895, 5, 8)]
    samples = {
        "Chitosan": [(3360, 34, 170), (1650, 14, 18), (1560, 11, 18), (1150, 12, 15), (1065, 21, 20), (1025, 19, 18)],
        "CS/CNC 3 wt%": [(3345, 37, 165), (1650, 13, 18), (1560, 10, 18), (1158, 13, 15), (1060, 24, 20), (1030, 23, 18)],
        "CS/CNC 5 wt%": [(3335, 39, 160), (1650, 12, 18), (1560, 9, 18), (1160, 14, 15), (1058, 26, 20), (1032, 26, 18)],
    }
    ftir = {"Wavenumber": wn}
    for name, bands in samples.items():
        t = 93 - 0.0012 * (4000 - wn)
        for c, a, s in common + bands:
            t = t - a * np.exp(-0.5 * ((wn - c) / s) ** 2)
        ftir[name] = np.round(t + rng.normal(0, 0.12, wn.size), 3)
    T = np.arange(30, 801, 1.0)
    sig = lambda T, c, w: 1 / (1 + np.exp(-(T - c) / w))  # noqa: E731
    params = {  # water loss, main degradation, char loss
        "Chitosan": [(8.0, 75, 14), (45.0, 292, 17), (12.0, 470, 60)],
        "CS/CNC 3 wt%": [(7.0, 75, 14), (48.0, 298, 16), (12.0, 480, 60)],
        "CS/CNC 5 wt%": [(6.5, 75, 14), (50.0, 304, 15), (12.0, 485, 60)],
    }
    tga = {"Temperature": T}
    for name, steps in params.items():
        m = 100.0 - sum(a * (sig(T, c, w) - sig(T[0], c, w)) for a, c, w in steps)
        tga[name] = np.round(m + rng.normal(0, 0.015, T.size), 3)
    files = []
    for fname, data in (("ILLUSTRATIVE_ftir.csv", ftir), ("ILLUSTRATIVE_tga.csv", tga)):
        p = d / fname
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(DEMO_HEADER)
            pd.DataFrame(data).to_csv(fh, index=False)
        files.append(p)
    layout = {
        "_comment": "ILLUSTRATIVE layout using synthetic demo data - not measurements",
        "width": "double", "height_mm": 62, "ncols": 3, "output": "ILLUSTRATIVE_fig_ftir_tga",
        "panels": [
            {"kind": "ftir", "file": "ILLUSTRATIVE_ftir.csv",
             "options": {"peaks": "3350:O–H/N–H;1650:amide I;1560:amide II;1060:C–O–C"}},
            {"kind": "tga", "file": "ILLUSTRATIVE_tga.csv",
             "options": {"dtg_smooth": 11, "report_csv": "ILLUSTRATIVE_tga_values.csv"}},
            {"kind": "dtg", "file": "ILLUSTRATIVE_tga.csv", "options": {"dtg_smooth": 11}},
        ],
    }
    lp = d / "ILLUSTRATIVE_panel_layout.json"
    lp.write_text(json.dumps(layout, indent=2, ensure_ascii=False), encoding="utf-8")
    files.append(lp)
    for f in files:
        print(f"wrote {f}")
    print("These files are ILLUSTRATIVE synthetic data for testing only - not measurements.")
    return files


# ----------------------------------------------------------------------------- CLI
def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kind", nargs="?", choices=KINDS + ["panel"], help="plot kind, or 'panel' with a JSON layout")
    p.add_argument("file", nargs="?", help="CSV/XLSX data file (or JSON layout for 'panel')")
    p.add_argument("--demo-data", metavar="DIR", help="write ILLUSTRATIVE synthetic test CSVs into DIR and exit")

    g = p.add_argument_group("columns")
    g.add_argument("--x", help="x column name (default: first column)")
    g.add_argument("--y", help="y column(s), comma separated (default: all other numeric columns)")
    g.add_argument("--labels", help="legend names for the series, comma or ; separated, in order")
    g.add_argument("--sample-col", help="long format: column holding the sample name")
    g.add_argument("--pairs", action="store_true", help="columns are x1,y1,x2,y2,... pairs")
    g.add_argument("--sheet", help="Excel sheet name")
    g.add_argument("--decimal", default=".", help="decimal separator in CSV (default '.')")

    g = p.add_argument_group("output and style")
    g.add_argument("-o", "--out", help="output base path without extension")
    g.add_argument("--formats", default="svg,png,pdf")
    g.add_argument("--dpi", type=int, default=600)
    g.add_argument("--width", help="single (85 mm), onehalf (114 mm), double (170 mm) or mm")
    g.add_argument("--height", type=float, help="figure height in mm")
    g.add_argument("--style", choices=["auto", "science", "plain"], default="auto")
    g.add_argument("--font-size", type=float, default=7.0)
    g.add_argument("--linewidth", type=float, default=0.9)
    g.add_argument("--no-markers", action="store_true", help="lines only (styles still differ)")
    g.add_argument("--legend", choices=["auto", "legend", "inline", "none"], default="auto")
    g.add_argument("--legend-loc", help="matplotlib legend location, e.g. 'upper right'")
    g.add_argument("--xlabel")
    g.add_argument("--ylabel")
    g.add_argument("--xlim", help="e.g. 1800,800")
    g.add_argument("--ylim")
    g.add_argument("--letter", help="single plot: draw this panel letter, e.g. b")
    g.add_argument("--no-panel-letters", action="store_true")
    g.add_argument("--report-csv", help="write computed values (TGA/Segal/extrema/tensile/bar) to CSV")

    g = p.add_argument_group("spectra (ftir, xrd, dsc)")
    g.add_argument("--mode", choices=["transmittance", "absorbance"], default="transmittance")
    g.add_argument("--offset", default="auto", help="vertical offset between curves (data units) or auto")
    g.add_argument("--normalize", choices=["none", "max", "minmax"], default="none")
    g.add_argument("--peaks", help='label ONLY these positions: "1650:amide I;1560:amide II"')
    g.add_argument("--peak-headroom", type=float, default=0.22, help="extra space above curves for labels")
    g.add_argument("--extrema", help="mark measured local extrema in windows, e.g. 1700-1600,1100-1000")
    g.add_argument("--extrema-type", choices=["auto", "min", "max"], default="auto")
    g.add_argument("--extrema-decimals", type=int)
    g.add_argument("--segal", help="XRD Segal CrI: PEAK:AMORPHOUS 2θ positions, e.g. 22.6:18.0")
    g.add_argument("--segal-window", type=float, default=0.5, help="± search window in ° (default 0.5)")
    g.add_argument("--exo", choices=["up", "down"], default="up", help="DSC: direction of exotherm in the data")
    g.add_argument("--invert", action="store_true", help="DSC: multiply heat flow by −1 (stated in caption)")
    g.add_argument("--ylabel-keep-ticks", action="store_true", help="keep y tick labels on stacked plots")

    g = p.add_argument_group("thermal (tga, dtg)")
    g.add_argument("--dtg", choices=["none", "twin", "panel"], default="none")
    g.add_argument("--dtg-smooth", type=int, default=0, help="Savitzky-Golay window (points) before d/dT")
    g.add_argument("--tga-normalize", action="store_true", help="scale mass so the first point = 100 %%")
    g.add_argument("--tga-ref-temp", type=float, help="reference T for T5%%/T10%% (e.g. 120 to exclude water)")
    g.add_argument("--tmax-windows", help="report Tmax(DTG) in windows, e.g. 200-400,400-600")
    g.add_argument("--no-tmax-marks", action="store_true", help="dtg: do not print Tmax next to peaks")

    g = p.add_argument_group("tensile")
    g.add_argument("--modulus-range", help="strain range for linear fit, e.g. 0,1")
    g.add_argument("--strain-unit", choices=["percent", "fraction"], default="percent")
    g.add_argument("--break-frac", type=float, default=0.0,
                   help="break = last point with stress >= frac*max (default 0: last point)")

    g = p.add_argument_group("bar")
    g.add_argument("--mean", help="column with means (summary input)")
    g.add_argument("--sd", help="column with error values (summary input)")
    g.add_argument("--n-col", help="column with n (summary input)")
    g.add_argument("--error", choices=["sd", "sem", "ci95"], default="sd")
    g.add_argument("--orient", choices=["auto", "rows", "columns"], default="auto",
                   help="replicates: rows = groups (first col names) or columns = groups")
    g.add_argument("--sig-letters", help="user-supplied significance letters per group, e.g. a,b,ab")
    g.add_argument("--no-points", action="store_true")
    g.add_argument("--hatch", action="store_true", help="add hatching to bars (grayscale)")

    g = p.add_argument_group("xy")
    g.add_argument("--scatter", action="store_true")
    g.add_argument("--logx", action="store_true")
    g.add_argument("--logy", action="store_true")
    return p


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):   # Windows consoles: print °, θ, − safely
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = build_parser()
    opt = parser.parse_args(argv)
    try:
        if opt.demo_data:
            write_demo_data(opt.demo_data)
            return 0
        if not opt.kind:
            parser.print_help()
            return 1
        files = run_panel(opt, parser) if opt.kind == "panel" else run_single(opt)
        for f in files:
            print(f"wrote {f}")
        return 0
    except DataError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
