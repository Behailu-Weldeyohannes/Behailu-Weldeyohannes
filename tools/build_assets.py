#!/usr/bin/env python3
"""Build the animated SVG figures used by the profile README.

Every figure is self-contained:
  * fonts (STIX Two Text, IBM Plex Mono; SIL OFL 1.1) are subset to the glyphs
    each figure uses and embedded as data URIs, so nothing loads at render time;
  * colours follow prefers-color-scheme and match GitHub's light/dark canvas;
  * all motion is CSS keyframes, and the resting style of every animated element
    is its final state, so prefers-reduced-motion shows a complete still figure.

Usage:  python3 tools/build_assets.py      (writes ../assets/*.svg)
"""
import base64
import io
import math
import os
from collections import defaultdict

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "assets"))

FONTS = {  # key: (css family, weight, style, file)
    "serif": ("S", 400, "normal", "stix-two-text-latin-400-normal.woff2"),
    "serif-i": ("S", 400, "italic", "stix-two-text-latin-400-italic.woff2"),
    "serif-b": ("S", 600, "normal", "stix-two-text-latin-600-normal.woff2"),
    "greek-i": ("G", 400, "italic", "stix-two-text-greek-400-italic.woff2"),
    "mono": ("M", 400, "normal", "ibm-plex-mono-latin-400-normal.woff2"),
    "mono-b": ("M", 500, "normal", "ibm-plex-mono-latin-500-normal.woff2"),
}
_font_cache = {}


def _font(key):
    if key not in _font_cache:
        _font_cache[key] = TTFont(os.path.join(HERE, "fonts", FONTS[key][3]))
    return _font_cache[key]


def font_key(cls):
    c = set(cls.split())
    if "g" in c:
        return "greek-i"
    if "m" in c:
        return "mono-b" if "b" in c else "mono"
    if "b" in c:
        return "serif-b"
    if "i" in c:
        return "serif-i"
    return "serif"


def measure(s, cls, size):
    f = _font(font_key(cls))
    cmap, hmtx = f.getBestCmap(), f["hmtx"]
    upm = f["head"].unitsPerEm
    return sum(hmtx[cmap[ord(ch)]][0] for ch in s if ord(ch) in cmap) * size / upm


def face_css(key, chars):
    fam, weight, style, _ = FONTS[key]
    f = TTFont(os.path.join(HERE, "fonts", FONTS[key][3]))
    missing = [c for c in chars if ord(c) not in f.getBestCmap() and c not in " \n"]
    if missing:
        raise SystemExit(f"font {key} lacks glyphs: {missing!r}")
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"] if key.startswith("serif") else []
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(unicodes={ord(c) for c in chars} | {0x20})
    sub.subset(f)
    buf = io.BytesIO()
    f.flavor = "woff2"
    f.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return (f"@font-face{{font-family:{fam};font-weight:{weight};font-style:{style};"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")


def n(v):
    """Compact number formatting for SVG/CSS."""
    if isinstance(v, int):
        return str(v)
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


BASE_CSS = """
:root{--paper:#ffffff;--ink:#1f2328;--ink2:#59636e;--line:#8c959f;--rule:#d0d7de;--faint:#f6f8fa;
--blue:#1f5bd8;--red:#cf3a24;--teal:#0b8a76;--amber:#a86b12}
@media (prefers-color-scheme:dark){:root{--paper:#0d1117;--ink:#e6edf3;--ink2:#9198a1;--line:#6e7681;
--rule:#30363d;--faint:#161b22;--blue:#7da2ff;--red:#ff7b5e;--teal:#3fcfb6;--amber:#e8b44f}}
text{font-family:S,'STIX Two Text',Georgia,serif;fill:var(--ink)}
.m{font-family:M,'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace}
.g{font-family:G,S,serif;font-style:italic}
.i{font-style:italic}.b{font-weight:600}.m.b{font-weight:500}
.k2{fill:var(--ink2)}.kb{fill:var(--blue)}.kr{fill:var(--red)}.kt{fill:var(--teal)}.ka{fill:var(--amber)}
.bg{fill:var(--paper);stroke:var(--rule)}.nf{stroke:none}
.ln{fill:none;stroke:var(--line);stroke-width:1.5}
.gr{fill:none;stroke:var(--rule);stroke-width:1}
.bx{fill:var(--paper);stroke:var(--ink);stroke-width:1.5}
.tile{fill:var(--faint);stroke:var(--line);stroke-width:1.25}
.fb{fill:var(--blue)}.fr{fill:var(--red)}.ft{fill:var(--teal)}.fa{fill:var(--amber)}.ff{fill:var(--faint)}
.fl{fill:var(--line)}.fp{fill:var(--paper)}
.sb{fill:none;stroke:var(--blue);stroke-width:2.5;stroke-linecap:round}
.st{fill:none;stroke:var(--teal);stroke-width:2.5;stroke-linecap:round}
.sr{fill:none;stroke:var(--red);stroke-width:2.5;stroke-linecap:round}
.sa{fill:none;stroke:var(--amber);stroke-width:2.5;stroke-linecap:round}
.ck{fill:none;stroke:var(--teal);stroke-width:2.6;stroke-linecap:round;stroke-linejoin:round}
.xx{fill:none;stroke:var(--red);stroke-width:2.6;stroke-linecap:round}
.pk{fill:var(--blue);stroke:var(--paper);stroke-width:2.5}
.dr{stroke-dasharray:1 2}
.dash{stroke-dasharray:4 4}
"""
MOTION_OFF = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


# --------------------------------------------------------------------------- timing
def kf_block(name, T, pts):
    """pts: [(t_seconds, 'css decls', optional easing)] -> @keyframes rule."""
    pts = sorted(pts, key=lambda p: p[0])
    if pts[0][0] > 0:
        pts.insert(0, (0.0,) + tuple(pts[0][1:]))
    if pts[-1][0] < T:
        pts.append((T,) + tuple(pts[-1][1:2]))
    out, last = [], -1.0
    for p in pts:
        t, decl = p[0], p[1]
        ease = p[2] if len(p) > 2 else None
        pct = round(100.0 * min(max(t, 0), T) / T, 3)
        if pct <= last:
            pct = round(last + 0.001, 3)
        last = pct
        e = f"animation-timing-function:{ease};" if ease else ""
        out.append(f"{pct}%{{{decl};{e}}}")
    return f"@keyframes {name}{{{''.join(out)}}}"


def vis(T, windows, fin=0.2, fout=0.25, lo=0.0, hi=1.0):
    """Opacity keyframes: visible during each (on, off) window (fade in after `on`,
    fade out after `off`)."""
    pts = [(0.0, f"opacity:{n(lo)}")]
    for on, off in windows:
        if on <= 0:
            pts = [(0.0, f"opacity:{n(hi)}")]
        else:
            pts.append((on, f"opacity:{n(lo)}"))
            pts.append((min(on + fin, T), f"opacity:{n(hi)}"))
        if off >= T:
            pts.append((T, f"opacity:{n(hi)}"))
        else:
            pts.append((off, f"opacity:{n(hi)}"))
            pts.append((min(off + fout, T), f"opacity:{n(lo)}"))
    if pts[-1][0] < T:
        pts.append((T, pts[-1][1]))
    return pts


def draw(T, t0, t1, fade_at=None, fade_len=0.3):
    """Stroke 'drawing' via dashoffset on a pathLength=1 element (+ optional fade)."""
    pts = [(0.0, "stroke-dashoffset:1;opacity:1"), (t0, "stroke-dashoffset:1;opacity:1")]
    k = 16
    for i in range(1, k + 1):
        u = i / k
        e = u * u * (3 - 2 * u)
        pts.append((t0 + (t1 - t0) * u, f"stroke-dashoffset:{n(1 - e)};opacity:1"))
    if fade_at is not None:
        pts.append((fade_at, "stroke-dashoffset:0;opacity:1"))
        pts.append((min(fade_at + fade_len, T), "stroke-dashoffset:0;opacity:0"))
        pts.append((T, "stroke-dashoffset:1;opacity:0"))
    else:
        pts.append((T, "stroke-dashoffset:0;opacity:1"))
    return pts


def smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


# --------------------------------------------------------------------------- paths
class Path:
    def __init__(self, x, y):
        self.start = (x, y)
        self.cur = (x, y)
        self.segs = []

    def L(self, x, y):
        self.segs.append(("L", self.cur, (x, y)))
        self.cur = (x, y)
        return self

    def C(self, x1, y1, x2, y2, x, y):
        self.segs.append(("C", self.cur, (x1, y1), (x2, y2), (x, y)))
        self.cur = (x, y)
        return self

    def d(self):
        out = [f"M{n(self.start[0])},{n(self.start[1])}"]
        for s in self.segs:
            if s[0] == "L":
                out.append(f"L{n(s[2][0])},{n(s[2][1])}")
            else:
                out.append("C" + " ".join(f"{n(p[0])},{n(p[1])}" for p in s[2:]))
        return "".join(out)

    def table(self):
        pts, marks = [self.start], [0.0]
        acc = 0.0
        for s in self.segs:
            if s[0] == "L":
                samp = [s[1], s[2]]
            else:
                p0, p1, p2, p3 = s[1:]
                samp = []
                for i in range(61):
                    t = i / 60
                    a = (1 - t) ** 3
                    b = 3 * (1 - t) ** 2 * t
                    c = 3 * (1 - t) * t * t
                    d = t ** 3
                    samp.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                                 a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
            for q in samp[1:]:
                p = pts[-1]
                acc += math.hypot(q[0] - p[0], q[1] - p[1])
                pts.append(q)
                marks.append(acc)
        self._pts, self._marks = pts, marks
        return self

    def length(self):
        if not hasattr(self, "_marks"):
            self.table()
        return self._marks[-1]

    def seg_end_lengths(self):
        """Cumulative length at the end of each segment (index i -> after segment i)."""
        ends, acc = [], 0.0
        for s in self.segs:
            acc += Path(*s[1]).__class__._seglen(s)
            ends.append(acc)
        return ends

    @staticmethod
    def _seglen(s):
        p = Path(*s[1])
        if s[0] == "L":
            p.L(*s[2])
        else:
            p.C(*s[2], *s[3], *s[4])
        return p.length()

    def at(self, L):
        if not hasattr(self, "_marks"):
            self.table()
        marks, pts = self._marks, self._pts
        L = min(max(L, 0.0), marks[-1])
        lo, hi = 0, len(marks) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if marks[mid] < L:
                lo = mid
            else:
                hi = mid
        span = marks[hi] - marks[lo] or 1.0
        u = (L - marks[lo]) / span
        return (pts[lo][0] + (pts[hi][0] - pts[lo][0]) * u,
                pts[lo][1] + (pts[hi][1] - pts[lo][1]) * u)


def motion(T, path, schedule, dt=0.04, ease=True, origin=(0.0, 0.0)):
    """Translate keyframes moving along `path`.
    schedule: [(t, L)] arc-length keypoints; holds between equal L values."""
    pts = []
    sched = sorted(schedule)
    if sched[0][0] > 0:
        sched.insert(0, (0.0, sched[0][1]))
    if sched[-1][0] < T:
        sched.append((T, sched[-1][1]))
    ox, oy = origin

    def tr(L):
        x, y = path.at(L)
        return f"transform:translate({n(x - ox)}px,{n(y - oy)}px)"

    for (t0, L0), (t1, L1) in zip(sched, sched[1:]):
        if abs(L1 - L0) < 1e-6 or t1 - t0 < 1e-6:
            pts.append((t0, tr(L0)))
            pts.append((t1, tr(L1)))
            continue
        k = max(2, int((t1 - t0) / dt))
        for i in range(k + 1):
            u = i / k
            e = smooth(u) if ease else u
            pts.append((t0 + (t1 - t0) * u, tr(L0 + (L1 - L0) * e)))
    return pts


def time_at(schedule, L, ease=True):
    """Invert a motion schedule: first time the mover reaches arc length L."""
    sched = sorted(schedule)
    for (t0, L0), (t1, L1) in zip(sched, sched[1:]):
        if (L0 <= L <= L1) and L1 > L0:
            target = (L - L0) / (L1 - L0)
            lo, hi = 0.0, 1.0
            for _ in range(40):
                mid = (lo + hi) / 2
                if (smooth(mid) if ease else mid) < target:
                    lo = mid
                else:
                    hi = mid
            return t0 + (t1 - t0) * lo
    raise ValueError(L)


# --------------------------------------------------------------------------- figure
class Fig:
    def __init__(self, name, w, h, title, desc):
        self.name, self.w, self.h = name, w, h
        self.title, self.desc = title, desc
        self.body, self.css = [], []
        self.used = defaultdict(set)
        self.count = 0
        self.defs = []

    def uid(self, p="a"):
        self.count += 1
        return f"{p}{self.count}"

    def add(self, *parts):
        self.body.extend(parts)

    def text(self, x, y, s, cls="", size=16, anchor="start", extra=""):
        a = "" if anchor == "start" else f' text-anchor="{anchor}"'
        c = f' class="{cls}"' if cls else ""
        if "\u03c3" in s and "g" not in cls.split():
            # Greek sigma comes from the STIX Greek subset; the rest from the Latin face.
            self.used["greek-i"].add("\u03c3")
            self.used[font_key(cls)].update(s.replace("\u03c3", ""))
            body = '<tspan class="g">\u03c3</tspan>'.join(esc(part) for part in s.split("\u03c3"))
        else:
            self.used[font_key(cls)].update(s)
            body = esc(s)
        return f'<text x="{n(x)}" y="{n(y)}"{c} font-size="{n(size)}"{a}{extra}>{body}</text>'

    def anim(self, T, pts, rest="", delay=0.0, prefix="a"):
        cls = self.uid(prefix)
        self.css.append(kf_block("k" + cls, T, pts))
        d = f" {n(delay)}s" if delay else ""
        self.css.append(f".{cls}{{{rest}animation:k{cls} {n(T)}s linear{d} infinite}}")
        return cls

    def arrow_marker(self):
        self.defs.append('<marker id="ah" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" '
                         'markerHeight="7" orient="auto"><path d="M0,1.2 L9,5 L0,8.8 z" class="fl"/></marker>')

    def render(self):
        faces = "".join(face_css(k, "".join(sorted(v))) for k, v in sorted(self.used.items()))
        css = faces + BASE_CSS + "".join(self.css) + MOTION_OFF
        defs = "".join(self.defs)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t d">\n'
                f"<!-- Built by tools/build_assets.py. Fonts: STIX Two Text and IBM Plex Mono, "
                f"subset, SIL Open Font License 1.1. -->\n"
                f'<title id="t">{esc(self.title)}</title><desc id="d">{esc(self.desc)}</desc>\n'
                f"<defs><style>{css}</style>{defs}</defs>\n" + "\n".join(self.body) + "\n</svg>\n")

    def save(self):
        os.makedirs(OUT, exist_ok=True)
        path = os.path.join(OUT, self.name + ".svg")
        with open(path, "w") as fh:
            fh.write(self.render())
        return path


def background(f, frame=True):
    cls = "bg" if frame else "bg nf"
    return f'<rect class="{cls}" x="0.5" y="0.5" width="{f.w - 1}" height="{f.h - 1}" rx="14"/>'


def check(cx, cy, s=8, cls="ck", extra=""):
    return (f'<path class="{cls}"{extra} d="M{n(cx - s * .55)},{n(cy)} L{n(cx - s * .12)},{n(cy + s * .45)} '
            f'L{n(cx + s * .6)},{n(cy - s * .5)}"/>')


def cross(cx, cy, s=7, cls="xx", extra=""):
    return (f'<path class="{cls}"{extra} d="M{n(cx - s / 2)},{n(cy - s / 2)} L{n(cx + s / 2)},{n(cy + s / 2)} '
            f'M{n(cx + s / 2)},{n(cy - s / 2)} L{n(cx - s / 2)},{n(cy + s / 2)}"/>')


def rect(x, y, w, h, cls, rx=8, extra=""):
    return f'<rect class="{cls}"{extra} x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="{n(rx)}"/>'


def path_el(d, cls, extra=""):
    return f'<path class="{cls}"{extra} d="{d}"/>'


# =========================================================================== hero
def hero():
    T = 9.0
    f = Fig("hero", 1200, 560,
            "Behailu Weldeyohannes, AI engineer",
            "I build AI systems on the assumption that generation fails. Animated diagram: a request "
            "goes through a gateway to provider A, which times out, returns schema-breaking JSON or "
            "crashes mid-batch; the gateway reroutes to provider B, the answer passes a schema check "
            "and a valid response comes out.")
    f.arrow_marker()
    f.add(background(f, frame=False))
    f.add(f.text(64, 104, "Behailu Weldeyohannes", "b", 60))
    f.add(f.text(64, 146, "AI engineer working on LLM orchestration, RAG, and GPU inference "
                          "on self-hosted models", "i k2", 23))
    f.add(f.text(64, 236, "I build AI systems on the assumption that generation fails.", "", 40))
    f.add(f.text(64, 280, "The engineering that matters is what happens next.", "i k2", 23))

    cy = 436
    A = (330, 352, 190, 50)
    B = (330, 470, 190, 50)
    V = (650, cy - 25, 190, 50)
    O = (946, cy - 25, 190, 50)
    G = (206, cy - 22, 48, 44)
    ay, by = A[1] + 25, B[1] + 25

    e0 = Path(99, cy).L(G[0], cy)
    eA = Path(G[0] + G[2], cy).C(292, cy, 292, ay, A[0], ay)
    eB = Path(G[0] + G[2], cy).C(292, cy, 292, by, B[0], by)
    eAV = Path(A[0] + A[2], ay).C(585, ay, 585, cy, V[0], cy)
    eBV = Path(B[0] + B[2], by).C(585, by, 585, cy, V[0], cy)
    eO = Path(V[0] + V[2], cy).L(O[0], cy)
    for e in (e0, eA, eB, eAV, eBV, eO):
        f.add(path_el(e.d(), "ln", ' marker-end="url(#ah)"'))

    # packet 1: request -> gateway -> provider A (swallowed there)
    p1 = Path(92, cy).L(230, cy).L(G[0] + G[2], cy).C(292, cy, 292, ay, A[0], ay).L(A[0] + A[2] / 2, ay)
    p1.table()
    L_gw = 138.0
    L1 = p1.length()
    s1 = [(0.0, 0.0), (0.3, 0.0), (0.8, L_gw), (1.4, L1), (T, L1)]
    # packet 2: gateway -> B -> schema check -> output
    p2 = (Path(230, cy).L(G[0] + G[2], cy).C(292, cy, 292, by, B[0], by).L(B[0] + B[2] / 2, by)
          .L(B[0] + B[2], by).C(585, by, 585, cy, V[0], cy).L(V[0] + V[2] / 2, cy)
          .L(V[0] + V[2], cy).L(O[0], cy).L(O[0] + O[2] / 2, cy))
    p2.table()
    ends = p2.seg_end_lengths()
    Lb_mid, Lb_out, Lv_in, Lv_mid, Lv_out, Lo_in, Lo_mid = ends[2], ends[3], ends[4], ends[5], ends[6], ends[7], ends[8]
    s2 = [(0.0, 0.0), (2.3, 0.0), (3.1, Lb_mid), (3.7, Lb_mid), (4.6, Lv_mid), (5.1, Lv_mid),
          (5.7, Lo_mid), (T, Lo_mid)]

    # highlight overlays (drawn in step with the packets)
    t_bo = time_at(s2, Lb_out)
    t_vi = time_at(s2, Lv_in)
    t_vo = time_at(s2, Lv_out)
    t_oi = time_at(s2, Lo_in)
    t_gw_out = time_at(s1, L_gw + 24)
    t_a_in = time_at(s1, p1.seg_end_lengths()[2])
    fade = 8.4
    h = [
        (e0, 0.3, 0.8, fade),
        (eA, t_gw_out - 0.05, t_a_in, 1.55),
        (eB, 2.3, time_at(s2, ends[2 - 1]) + 0.02, fade),
        (eBV, t_bo, t_vi, fade),
        (eO, t_vo, t_oi, fade),
    ]
    for i, (e, a, b, fa) in enumerate(h):
        rest = "stroke-dashoffset:0;opacity:1;" if i != 1 else "stroke-dashoffset:0;opacity:0;"
        c = f.anim(T, draw(T, a, b, fade_at=fa, fade_len=0.4 if i else 0.4), rest=rest)
        f.add(path_el(e.d(), f"sb dr {c}", ' pathLength="1"'))

    # packets (drawn beneath the boxes so they disappear "into" a stage)
    c1m = f.anim(T, motion(T, p1, s1), rest="transform:translate(0px,0px);")
    c1o = f.anim(T, vis(T, [(0.02, 1.45)], fin=0.25, fout=0.1), rest="opacity:0;")
    f.add(f'<g transform="translate(0,0)"><g class="{c1o}"><circle class="pk {c1m}" r="6.5"/></g></g>')
    c2m = f.anim(T, motion(T, p2, s2), rest="transform:translate(0px,0px);")
    c2o = f.anim(T, vis(T, [(2.3, 5.75)], fin=0.05, fout=0.1), rest="opacity:0;")
    f.add(f'<g class="{c2o}"><circle class="pk {c2m}" r="6.5"/></g>')

    # nodes
    f.add(f'<circle cx="92" cy="{cy}" r="7" class="bx"/>')
    f.add(f.text(92, cy + 36, "request", "i k2", 18, "middle"))
    f.add(rect(*G, "bx", 8))
    cg = f.anim(T, vis(T, [(0.62, 0.95), (2.22, 2.6)], fin=0.1, fout=0.2), rest="opacity:0;")
    f.add(rect(*G, f"sb {cg}", 8))
    f.add(f.text(230, cy + 46, "gateway", "i k2", 18, "middle"))
    for (x, y, w, hh), label in ((A, "provider A"), (B, "provider B"), (V, "schema check"), (O, "valid response")):
        f.add(rect(x, y, w, hh, "bx", 8))
        f.add(f.text(x + w / 2, y + hh / 2 + 7, label, "", 20, "middle"))

    # provider A fails
    ca = f.anim(T, vis(T, [(1.45, fade)], fin=0.15, fout=0.45), rest="opacity:1;")
    f.add(f'<g class="{ca}">' + rect(*A, "sr", 8) + cross(A[0] + A[2] - 18, ay, 9) + "</g>")
    labels = ["timed out", "returned schema-breaking JSON", "crashed mid-batch"]
    for k, lab in enumerate(labels):
        TT = 3 * T
        w = [(k * T + 1.6, k * T + fade)]
        c = f.anim(TT, vis(TT, w, fin=0.2, fout=0.45), rest=f"opacity:{1 if k == 0 else 0};")
        f.add(f'<g class="{c}">' + f.text(A[0] + A[2] / 2, A[1] - 14, lab, "i kr", 18, "middle") + "</g>")

    # reroute to provider B
    cb = f.anim(T, vis(T, [(3.05, fade)], fin=0.2, fout=0.45), rest="opacity:1;")
    f.add(rect(*B, f"sb {cb}", 8))
    cr = f.anim(T, vis(T, [(2.45, fade)], fin=0.3, fout=0.45), rest="opacity:1;")
    f.add(f'<g class="{cr}">' + f.text(B[0] + B[2] / 2, B[1] + B[3] + 24, "rerouted", "i kb", 18, "middle") + "</g>")

    # schema check passes, response comes out valid
    t_v = time_at(s2, Lv_mid) + 0.25
    cv = f.anim(T, vis(T, [(t_v, fade)], fin=0.2, fout=0.45), rest="opacity:1;")
    f.add(f'<g class="{cv}">' + rect(*V, "st", 8) + check(V[0] + V[2] - 20, cy, 11) + "</g>")
    co = f.anim(T, vis(T, [(5.7, fade)], fin=0.2, fout=0.45), rest="opacity:1;")
    f.add(f'<g class="{co}">' + rect(*O, "st", 8) + check(O[0] + O[2] - 20, cy, 11) + "</g>")
    return f


# =========================================================================== figure 1
def hyperflow():
    T = 7.2
    f = Fig("hyperflow", 1200, 430,
            "ComfyUI-HyperFlow: interval conditioning and A/V envelope lock",
            "(a) An eight-step sigma schedule: the sampler hops from each sigma to the next, and each "
            "step is conditioned on its interval, the current sigma and its endpoint. (b) Audio and "
            "video envelopes scroll in lock-step; measured correlation at 0 ms lag is +0.974 and "
            "+0.980 against a +0.136 unrelated-audio control.")
    f.add(background(f))

    # ---- (a) sigma schedule
    x0, x1, yt, yb = 112, 548, 78, 318
    f.add(path_el(f"M{x0},{yt} L{x0},{yb} L{x1},{yb}", "ln"))
    ys = lambda s: 306 - s * 216  # noqa: E731
    for s, lab in ((1, "1"), (0.5, "0.5"), (0, "0")):
        f.add(path_el(f"M{x0 - 6},{n(ys(s))} L{x0},{n(ys(s))}", "ln"))
        f.add(f.text(x0 - 12, ys(s) + 5, lab, "k2", 15, "end"))
    f.add(f.text(72, 206, "σ", "g", 24, "middle"))
    xs = [136 + 50 * i for i in range(9)]
    for i, x in enumerate(xs):
        f.add(path_el(f"M{x},{yb} L{x},{yb + 6}", "ln"))
        f.add(f.text(x, yb + 26, str(i), "k2", 15, "middle"))
    f.add(f.text(x1 + 10, yb + 5, "step", "i k2", 16))

    shift = 3.0
    sig = []
    for i in range(9):
        t = 1 - i / 8
        sig.append(shift * t / (1 + (shift - 1) * t))
    pts = [(xs[i], ys(sig[i])) for i in range(9)]
    arcs = []
    for i in range(8):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        arcs.append(Path(ax, ay).C(ax + 14, ay - 26, bx - 14, by - 26, bx, by))
    for a in arcs:
        f.add(path_el(a.d(), "gr"))
    hop, draw_t, t0 = 0.7, 0.45, 0.2
    end_hold, fade = 6.75, 0.35
    # interval brackets + guides + readout, one per step
    for i in range(8):
        a, b = t0 + hop * i, t0 + hop * (i + 1)
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        g = (f'<path class="sb" d="M{x0 + 16},{n(ay)} L{x0 + 16},{n(by)} M{x0 + 10},{n(ay)} L{x0 + 22},{n(ay)} '
             f'M{x0 + 10},{n(by)} L{x0 + 22},{n(by)}"/>'
             f'<path class="gr dash" style="stroke:var(--blue);opacity:.55" d="M{x0 + 24},{n(ay)} L{n(ax - 7)},{n(ay)} '
             f'M{x0 + 24},{n(by)} L{n(bx - 7)},{n(by)}"/>')
        last = i == 7
        win = [(a, b - 0.07)] if not last else [(a, end_hold)]
        c = f.anim(T, vis(T, win, fin=0.06, fout=0.06), rest=f"opacity:{1 if last else 0};")
        f.add(f'<g class="{c}">{g}' + f.text(x1, 96, f"step {i + 1} of 8", "k2", 16, "end") + "</g>")
    for i, a in enumerate(arcs):
        s = t0 + hop * i
        c = f.anim(T, draw(T, s, s + draw_t, fade_at=end_hold, fade_len=fade), rest="stroke-dashoffset:0;opacity:1;")
        f.add(path_el(a.d(), f"sb dr {c}", ' pathLength="1"'))
    for i, (px, py) in enumerate(pts):
        f.add(f'<circle cx="{n(px)}" cy="{n(py)}" r="4.5" class="bx" style="stroke:var(--line)"/>')
        on = 0.1 if i == 0 else t0 + hop * (i - 1) + draw_t
        c = f.anim(T, vis(T, [(on, end_hold)], fin=0.1, fout=fade), rest="opacity:1;")
        f.add(f'<circle cx="{n(px)}" cy="{n(py)}" r="4.5" class="fb {c}"/>')
    f.add(f.text(64, 404, "(a) Eight steps, each conditioned on its own σ interval", "i k2", 18))

    # ---- (b) envelopes
    px0, pw, pt, pb = 660, 476, 80, 196
    P = pw

    def gauss_sum(u, bumps, wmul=1.0):
        v = 0.0
        for c, hgt, wid in bumps:
            for k in (-1, 0, 1):
                d = u - (c + k)
                v += hgt * math.exp(-(d * d) / (2 * (wid * wmul) ** 2))
        return v

    bumps = [(0.030, 0.62, 0.010), (0.062, 0.95, 0.013), (0.098, 0.70, 0.011), (0.128, 0.42, 0.009),  # word 1
             (0.245, 0.80, 0.012), (0.282, 0.55, 0.010),                                         # word 2
             (0.335, 0.50, 0.009), (0.368, 0.88, 0.012), (0.405, 0.98, 0.014), (0.445, 0.60, 0.010),
             (0.482, 0.36, 0.009),                                                               # word 3
             (0.640, 0.74, 0.013),                                                               # word 4
             (0.765, 0.46, 0.010), (0.800, 0.83, 0.013), (0.842, 0.66, 0.011), (0.905, 0.90, 0.014)]
    ea, ev = [], []
    x = px0
    while x <= px0 + pw + P + 0.1:
        u = ((x - px0) % P) / P
        a = 0.035 + gauss_sum(u, bumps)
        v = 0.035 + 0.9 * gauss_sum(u, bumps, 1.25) + 0.02 * (1 + math.sin(2 * math.pi * 9 * u))
        ea.append((x, pb - 104 * min(a, 1.05)))
        ev.append((x, pb - 104 * min(v, 1.05)))
        x += 1.5
    line_a = "M" + " L".join(f"{n(p[0])},{n(p[1])}" for p in ea)
    area_a = line_a + f" L{n(ea[-1][0])},{pb} L{px0},{pb} Z"
    line_v = "M" + " L".join(f"{n(p[0])},{n(p[1])}" for p in ev)
    f.defs.append(f'<clipPath id="cp"><rect x="{px0}" y="{pt - 12}" width="{pw}" height="{pb - pt + 14}"/></clipPath>')
    cs = f.anim(9.0, [(0, "transform:translate(0px,0px)"), (9.0, f"transform:translate({n(-P)}px,0px)")],
                rest="transform:translate(0px,0px);")
    f.add(f'<g clip-path="url(#cp)"><g class="{cs}">'
          f'<path d="{area_a}" class="fb" style="opacity:.14"/>'
          f'<path d="{line_a}" class="sb" style="stroke-width:1.6"/>'
          f'<path d="{line_v}" class="st" style="stroke-width:2.2"/></g></g>')
    f.add(path_el(f"M{px0},{pb} L{px0 + pw},{pb}", "ln"))
    f.add(path_el(f"M{px0},62 L{px0 + 24},62", "sb"))
    f.add(f.text(px0 + 32, 67, "audio envelope", "k2", 15))
    f.add(path_el(f"M{px0 + 170},62 L{px0 + 194},62", "st"))
    f.add(f.text(px0 + 202, 67, "video envelope", "k2", 15))
    f.add(f.text(px0 + pw, 67, "0 ms lag", "i k2", 15, "end"))

    # correlation bars (measured values; static on purpose)
    r0, r1 = 790, 1070
    rx = lambda r: r0 + (r1 - r0) * r  # noqa: E731
    rows = [(232, 0.974, "ft"), (258, 0.980, "ft"), (300, 0.136, "fl")]
    for y, r, cls in rows:
        f.add(rect(r0, y - 8, rx(r) - r0, 16, cls, 2))
        f.add(f.text(rx(r) + 8, y + 5.5, f"+{r:.3f}", "", 16))
    f.add(f.text(r0 - 12, 250, "matched audio", "k2", 15, "end"))
    f.add(f.text(r0 - 12, 305, "unrelated audio", "k2", 15, "end"))
    f.add(path_el(f"M{r0},322 L{r1},322", "ln"))
    for r, lab in ((0, "0"), (0.5, "0.5"), (1, "1")):
        f.add(path_el(f"M{n(rx(r))},322 L{n(rx(r))},328", "ln"))
        f.add(f.text(rx(r), 346, lab, "k2", 14, "middle"))
    f.add(f.text(640, 404, "(b) Audio and video envelopes, correlation at 0 ms lag", "i k2", 18))
    return f


# =========================================================================== figure 2
def pulsestudio():
    T = 8.0
    f = Fig("pulsestudio", 1200, 430,
            "ComfyUI-PulseStudio: names instead of ordinals, windows on the 17k+5 grid",
            "(a) Three assets sit in sockets; the prompt references Mimi either by ordinal, "
            "<Picture 3>, or by name, @Mimi. When the sockets are reordered the ordinal points at the "
            "wrong asset while the name still resolves to Mimi. (b) Three render windows snap from "
            "their requested lengths (50, 103 and 69 frames) to the 17k+5 frame grid (56, 107, 73).")
    f.add(background(f))

    # ---- (a) sockets
    sx = [140, 290, 440]
    ty = 130
    for i, x in enumerate(sx):
        f.add(f.text(x, 88, f"socket {i + 1}", "k2", 15, "middle"))
        f.add(rect(x - 60, ty - 26, 120, 52, "gr", 8, ' style="stroke-dasharray:3 4"'))

    xa, xb = 236, 236
    ya, yb = 262, 330
    f.add(f.text(88, ya, "ordinal", "i k2", 16))
    f.add(f.text(88, yb, "name", "i k2", 16))
    wa = measure("<Picture 3>", "m", 17)
    wb = measure("@Mimi", "m", 17)
    f.add(f.text(xa, ya, "<Picture 3>", "m", 17))
    f.add(f.text(xb, yb, "@Mimi", "m", 17))

    ca_d = f"M{n(xa + wa / 2)},{ya - 17} C{n(xa + wa / 2)},205 430,212 430,{ty + 28}"
    f.add(path_el(ca_d, "ln"))
    cred = f.anim(T, vis(T, [(2.6, 6.6)], fin=0.3, fout=0.3), rest="opacity:1;")
    f.add(path_el(ca_d, f"sr {cred}", ' style="stroke-width:2"'))
    old_b = f"M{n(xb + wb + 8)},{yb - 5} C470,{yb - 5} 450,240 450,{ty + 28}"
    new_b = f"M{xb - 8},{yb - 5} C140,{yb - 5} 140,250 140,{ty + 28}"
    cob = f.anim(T, vis(T, [(0, 1.4), (7.25, T)], fin=0.35, fout=0.35), rest="opacity:0;")
    f.add(path_el(old_b, f"sb {cob}", ' style="stroke-width:2"'))
    cnb = f.anim(T, draw(T, 2.6, 3.25, fade_at=6.6, fade_len=0.3), rest="stroke-dashoffset:0;opacity:1;")
    f.add(path_el(new_b, f"sb dr {cnb}", ' pathLength="1" style="stroke-width:2"'))

    # status marks
    ix = 506
    cA_ok = f.anim(T, vis(T, [(0, 2.62), (6.85, T)], fin=0.2, fout=0.15), rest="opacity:0;")
    f.add(check(ix, ya - 6, 11, cls=f"ck {cA_ok}"))
    cA_bad = f.anim(T, vis(T, [(2.72, 6.6)], fin=0.2, fout=0.25), rest="opacity:1;")
    f.add(f'<g class="{cA_bad}">' + cross(ix, ya - 6, 10) + f.text(ix + 14, ya, "wrong asset", "i kr", 16) + "</g>")
    f.add(check(ix, yb - 6, 11))
    cB_lab = f.anim(T, vis(T, [(3.1, 6.6)], fin=0.3, fout=0.25), rest="opacity:1;")
    f.add(f'<g class="{cB_lab}">' + f.text(ix + 14, yb, "still Mimi", "i kt", 16) + "</g>")

    # tiles (drawn last so they sit above the connectors)
    def tile(label, blue=False):
        st = ' style="stroke:var(--blue);stroke-width:2"' if blue else ""
        return rect(-58, -24, 116, 48, "tile", 7, st) + f.text(0, 6, label, "i", 18, "middle")

    def swap_pts(dx, arc):
        pts = []
        for (a, b, fwd) in ((1.4, 2.6, True), (6.6, 7.6, False)):
            k = 24
            for i in range(k + 1):
                u = i / k
                e = smooth(u)
                p = e if fwd else 1 - e
                pts.append((a + (b - a) * u, f"transform:translate({n(dx * p)}px,{n(arc * math.sin(math.pi * u))}px)"))
        return [(0.0, "transform:translate(0px,0px)")] + pts + [(T, "transform:translate(0px,0px)")]

    cbike = f'<g transform="translate({sx[1]},{ty})">' + tile("bike") + "</g>"
    ccafe_c = f.anim(T, swap_pts(300, 60), rest="transform:translate(300px,0px);")
    cmimi_c = f.anim(T, swap_pts(-300, -60), rest="transform:translate(-300px,0px);")
    f.add(cbike)
    f.add(f'<g transform="translate({sx[0]},{ty})"><g class="{ccafe_c}">' + tile("cafe") + "</g></g>")
    f.add(f'<g transform="translate({sx[2]},{ty})"><g class="{cmimi_c}">' + tile("Mimi", True) + "</g></g>")
    f.add(f.text(64, 404, "(a) Reorder the sockets: the ordinal breaks, the name follows", "i k2", 18))

    # ---- (b) 17k+5 grid
    gx0, gx1 = 712, 1112
    fx = lambda fr: gx0 + (gx1 - gx0) * fr / 112  # noqa: E731
    f.add(f.text(gx0, 70, "window length in frames, quantised to 17k + 5", "i k2", 15))
    ticks = "".join(f"M{n(fx(fr))},108 L{n(fx(fr))},{112 if fr % 17 != 5 else 116}" for fr in range(0, 113))
    f.add(path_el(ticks, "gr"))
    for k in range(7):
        fr = 17 * k + 5
        f.add(path_el(f"M{n(fx(fr))},116 L{n(fx(fr))},296", "gr", ' style="stroke-dasharray:2 4"'))
        f.add(f.text(fx(fr), 100, str(fr), "k2", 14, "middle"))
    rows = [(160, 50, 56), (216, 103, 107), (272, 69, 73)]
    for i, (y, req, q) in enumerate(rows):
        f.add(f.text(gx0 - 14, y + 6, f"shot {i + 1}", "k2", 16, "end"))
        a = 1.2 + 0.15 * i
        s0 = req / q
        pts = [(0, f"transform:scaleX({n(s0)})"), (a, f"transform:scaleX({n(s0)})", "cubic-bezier(.3,1.45,.55,1)"),
               (a + 0.7, "transform:scaleX(1)"), (7.0, "transform:scaleX(1)", "ease-in-out"),
               (7.6, f"transform:scaleX({n(s0)})"), (T, f"transform:scaleX({n(s0)})")]
        c = f.anim(T, pts, rest="transform:scaleX(1);transform-box:fill-box;transform-origin:0 50%;")
        f.add(rect(gx0, y - 12, fx(q) - gx0, 24, f"fb {c}", 3, ' style="opacity:.9"'))
        rq = fx(req)
        f.add(path_el(f"M{n(rq)},{y - 17} L{n(rq)},{y + 17}", "ln", ' style="stroke:var(--ink);stroke-width:1.5;stroke-dasharray:3 2"'))
        f.add(f.text(rq, y - 21, str(req), "i k2", 13, "middle"))
        cl = f.anim(T, vis(T, [(a + 0.55, 7.0)], fin=0.2, fout=0.2), rest="opacity:1;")
        f.add(f'<g class="{cl}">' + f.text(fx(q) + 10, y + 6, str(q), "", 16) + "</g>")
    f.add(f.text(640, 404, "(b) Requested lengths (dashed) snap to the 17k + 5 frame grid", "i k2", 18))
    return f


# =========================================================================== figure 3
def publishing():
    T = 6.0
    f = Fig("publishing", 1200, 300,
            "Addis Pulse Publishing pipeline",
            "Articles flow from 109 RSS sources through research, writing, SEO and validation to "
            "git-based publishing on a 10-node LangGraph state machine, with SQLite checkpoints "
            "under every stage; 67 articles have been published unattended.")
    f.arrow_marker()
    f.add(background(f))
    cy = 150
    boxes = [("research", 190), ("writing", 370), ("SEO", 550), ("validation", 730), ("publish (git)", 910)]
    bw, bh = 140, 48
    src = [(92, 94 + 17 * i) for i in range(7)]

    f.add(path_el(f"M190,{cy - 44} L190,{cy - 50} L1050,{cy - 50} L1050,{cy - 44}", "ln"))
    f.add(f.text(620, cy - 60, "10-node LangGraph state machine", "i k2", 16, "middle"))

    fan = []
    for (sx_, sy) in src:
        p = Path(sx_ + 5, sy).C(140, sy, 150, cy, 190, cy)
        fan.append(p)
        f.add(path_el(p.d(), "gr"))
    for i in range(4):
        x = boxes[i][1] + bw
        f.add(path_el(f"M{x},{cy} L{boxes[i + 1][1]},{cy}", "ln", ' marker-end="url(#ah)"'))
    f.add(path_el(f"M1050,{cy} L1088,{cy}", "ln", ' marker-end="url(#ah)"'))

    # checkpoint rail
    rail_y = 222
    f.add(path_el(f"M190,{rail_y} L1050,{rail_y}", "gr", ' style="stroke-dasharray:2 4"'))
    f.add(f.text(176, rail_y + 5, "SQLite checkpoints", "i k2", 16, "end"))

    # packets
    period, travel = 2.0, 5.2
    starts = [1, 4, 6]
    windows = defaultdict(list)
    cps = defaultdict(list)
    arrivals = []
    for k, si in enumerate(starts):
        p = Path(src[si][0] + 5, src[si][1]).C(140, src[si][1], 150, cy, 190, cy).L(1050, cy).L(1098, cy)
        p.table()
        Ltot = p.length()
        sched = [(0.0, 0.0), (travel, Ltot)]
        fan_len = p.seg_end_lengths()[0]
        shift = period * k  # packet k runs `shift` seconds ahead
        for bi, (_, bx) in enumerate(boxes):
            t_in = time_at(sched, fan_len + (bx - 190), ease=False)
            t_out = time_at(sched, fan_len + (bx + bw - 190), ease=False)
            windows[bi].append(((t_in - shift) % T, (t_out - shift) % T))
            cps[bi].append(((t_out - shift) % T))
        arrivals.append((travel - 0.05 - shift) % T)
        cm = f.anim(T, motion(T, p, sched, ease=False), rest="transform:translate(0px,0px);", delay=-shift)
        co = f.anim(T, vis(T, [(0.01, travel - 0.12)], fin=0.25, fout=0.1), rest="opacity:0;", delay=-shift)
        f.add(f'<g class="{co}"><circle class="pk {cm}" r="6"/></g>')

    for (sx_, sy) in src:
        f.add(f'<circle cx="{sx_}" cy="{sy}" r="4.5" class="fl"/>')
    f.add(f.text(92, 76, "109 RSS sources", "i k2", 16, "middle"))

    def split_windows(ws):
        out = []
        for a, b in ws:
            if b < a:
                out += [(a, T), (0.0, b)]
            else:
                out.append((a, b))
        return sorted(out)

    for bi, (label, bx) in enumerate(boxes):
        f.add(rect(bx, cy - bh / 2, bw, bh, "bx", 8))
        c = f.anim(T, vis(T, split_windows(windows[bi]), fin=0.12, fout=0.3), rest="opacity:0;")
        f.add(rect(bx, cy - bh / 2, bw, bh, f"sb {c}", 8))
        f.add(f.text(bx + bw / 2, cy + 6, label, "", 18, "middle"))
        mx = bx + bw / 2
        f.add(path_el(f"M{mx},{cy + bh / 2} L{mx},{rail_y - 7}", "gr"))
        dia = f"M{mx},{rail_y - 7} L{mx + 7},{rail_y} L{mx},{rail_y + 7} L{mx - 7},{rail_y} Z"
        f.add(path_el(dia, "fp", ' style="stroke:var(--line);stroke-width:1.25"'))
        cc = f.anim(T, vis(T, split_windows([(t, (t + 0.55) % T) for t in cps[bi]]), fin=0.08, fout=0.35),
                    rest="opacity:0;")
        f.add(path_el(dia, f"ft {cc}"))

    # published articles stack
    ax, ay_ = 1100, cy - 26
    doc = lambda x, y: (f'<path class="bx" style="stroke:var(--line)" d="M{x},{y} L{x + 26},{y} L{x + 34},{y + 8} '  # noqa: E731
                        f'L{x + 34},{y + 44} L{x},{y + 44} Z"/>'
                        f'<path class="gr" d="M{x + 7},{y + 18} L{x + 27},{y + 18} M{x + 7},{y + 25} L{x + 27},{y + 25} '
                        f'M{x + 7},{y + 32} L{x + 20},{y + 32}"/>')
    f.add(doc(ax + 8, ay_ - 8) + doc(ax + 4, ay_ - 4) + doc(ax, ay_))
    cpub = f.anim(T, vis(T, split_windows([(t, (t + 0.45) % T) for t in arrivals]), fin=0.08, fout=0.4),
                  rest="opacity:0;")
    f.add(f'<path class="sb {cpub}" d="M{ax},{ay_} L{ax + 26},{ay_} L{ax + 34},{ay_ + 8} L{ax + 34},{ay_ + 44} '
          f'L{ax},{ay_ + 44} Z" style="stroke-width:2"/>')
    f.add(f.text(1121, 222, "67 articles", "", 16, "middle"))
    f.add(f.text(1121, 241, "published", "i k2", 15, "middle"))
    f.add(f.text(1121, 258, "unattended", "i k2", 15, "middle"))
    return f


# =========================================================================== figure 4
def principles():
    T = 8.0
    f = Fig("principles", 1200, 520,
            "Engineering approach, four decisions in motion",
            "(a) A build log where an import gate, an egress gate, 882 Python tests and three JS "
            "suites pass, then a change adds 'import torch' and the build fails. (b) Two kinds of "
            "failure are routed to two different named types. (c) Four models take turns on one "
            "32 GB GPU, each holding the single lease while resident. (d) A telemetry frame is "
            "lost while the render keeps going to completion.")
    f.add(background(f))
    f.add(path_el("M600,40 L600,480 M40,260 L1160,260", "gr"))

    # ---- (a) make invariants executable
    f.add(f.text(64, 72, "(a) Make invariants executable", "i", 19))
    rows = [("import gate", "torch, comfy, folder_paths"),
            ("egress gate", "network calls in core: 0"),
            ("python tests", "882"),
            ("js suites", "3 of 3, invoked directly")]
    ry = [110, 138, 166, 194]
    for i, ((a, b), y) in enumerate(zip(rows, ry)):
        f.add(f.text(64, y, a, "m", 14.5))
        f.add(f.text(206, y, b, "m k2", 14.5))
        r = 0.4 + 0.45 * i
        cpend = f.anim(T, vis(T, [(0, r - 0.05), (7.8, T)], fin=0.15, fout=0.1), rest="opacity:0;")
        f.add(f'<g class="{cpend}">' + f.text(566, y, "...", "m k2", 14.5, "end") + "</g>")
        if i == 0:
            cp = f.anim(T, vis(T, [(r, 3.9), (7.15, 7.65)], fin=0.1, fout=0.12), rest="opacity:0;")
            cf = f.anim(T, vis(T, [(3.95, 7.05)], fin=0.1, fout=0.12), rest="opacity:1;")
            f.add(f'<g class="{cp}">' + f.text(566, y, "pass", "m kt", 14.5, "end") + "</g>")
            f.add(f'<g class="{cf}">' + f.text(566, y, "fail", "m b kr", 14.5, "end") + "</g>")
        else:
            cp = f.anim(T, vis(T, [(r, 7.65)], fin=0.1, fout=0.25), rest="opacity:1;")
            f.add(f'<g class="{cp}">' + f.text(566, y, "pass", "m kt", 14.5, "end") + "</g>")
    cdiff = f.anim(T, vis(T, [(3.4, 7.0)], fin=0.2, fout=0.25), rest="opacity:1;")
    f.add(f'<g class="{cdiff}">' + f.text(64, 232, "+ import torch", "m kr", 14.5) + "</g>")
    cok = f.anim(T, vis(T, [(2.05, 3.85), (7.15, 7.65)], fin=0.15, fout=0.12), rest="opacity:0;")
    f.add(f'<g class="{cok}">' + f.text(566, 232, "build passes", "i kt", 16, "end") + "</g>")
    cbad = f.anim(T, vis(T, [(4.0, 7.05)], fin=0.15, fout=0.12), rest="opacity:1;")
    f.add(f'<g class="{cbad}">' + f.text(566, 232, "build fails", "i kr", 16, "end") + "</g>")

    # ---- (b) name the failure
    f.add(f.text(624, 72, "(b) Name the failure", "i", 19))
    split = (768, 158)
    up = Path(640, 158).L(*split).C(812, 158, 812, 116, 866, 116).L(930, 116)
    dn = Path(640, 158).L(*split).C(812, 158, 812, 200, 866, 200).L(930, 200)
    f.add(path_el(Path(640, 158).L(*split).d(), "ln"))
    f.add(path_el(Path(*split).C(812, 158, 812, 116, 866, 116).d(), "ln"))
    f.add(path_el(Path(*split).C(812, 158, 812, 200, 866, 200).d(), "ln"))
    f.add(f.text(640, 186, "failures", "i k2", 15))
    parts = [(0.0, up, "fa"), (1.5, dn, "fr"), (3.0, dn, "fr"), (4.5, up, "fa")]
    Tb = 6.0
    for k, (shift, p, cls) in enumerate(parts):
        p.table()
        sched = [(0.0, 0.0), (0.2, 0.0), (1.7, p.length()), (Tb, p.length())]
        d = -((Tb - shift) % Tb)
        cm = f.anim(Tb, motion(Tb, p, sched), rest="transform:translate(0px,0px);", delay=d)
        co = f.anim(Tb, vis(Tb, [(0.05, 1.62)], fin=0.2, fout=0.08), rest="opacity:0;", delay=d)
        f.add(f'<g class="{co}"><circle class="{cls} {cm}" r="6" style="stroke:var(--paper);stroke-width:2.5"/></g>')
    f.add(f'<circle cx="{split[0]}" cy="{split[1]}" r="5" class="bx" style="stroke:var(--line)"/>')
    for (y, lab, cls, sh) in ((116, "schema violation", "sa", [0.0, 4.5]), (200, "unreachable model", "sr", [1.5, 3.0])):
        f.add(rect(866, y - 22, 186, 44, "bx", 8))
        c = f.anim(Tb, vis(Tb, sorted(((s + 1.62) % Tb, (s + 2.2) % Tb) for s in sh), fin=0.1, fout=0.35),
                   rest="opacity:0;")
        f.add(rect(866, y - 22, 186, 44, f"{cls} {c}", 8))
        f.add(f.text(959, y + 6, lab, "", 17, "middle"))
        colour = "var(--amber)" if cls == "sa" else "var(--red)"
        f.add(f'<path d="M1070,{y - 8} L1112,{y - 8} M1070,{y} L1126,{y} M1070,{y + 8} L1100,{y + 8}" '
              f'style="fill:none;stroke:{colour};stroke-width:2.2;stroke-linecap:round"/>')
    f.add(f.text(1098, 234, "own type, own log line", "i k2", 15, "middle"))

    # ---- (c) serialise structurally
    f.add(f.text(64, 302, "(c) Serialise structurally", "i", 19))
    chips = ["LLM", "image", "audio", "video"]
    qx, qy0 = 110, 338
    gx, gy, gw, gh = 330, 318, 240, 150
    f.add(rect(gx, gy, gw, gh, "bx", 10))
    f.add(f.text(gx + 16, gy + 26, "GPU, 32 GB", "i k2", 16))
    res = (gx + 96, gy + 88)
    # VRAM gauge
    vx, vy, vw, vh = gx + gw - 34, gy + 22, 16, gh - 44
    f.add(rect(vx, vy, vw, vh, "ln", 3))
    levels = [0.62, 0.48, 0.34, 0.86]
    Tc = 8.0
    slot = Tc / 4
    gauge = [(0.0, "transform:scaleY(0)")]
    for k, lv in enumerate(levels):
        s = slot * k
        gauge += [(s + 0.8, "transform:scaleY(0)"), (s + 1.0, f"transform:scaleY({lv})"),
                  (s + 1.4, f"transform:scaleY({lv})"), (s + 1.6, "transform:scaleY(0)")]
    cgv = f.anim(Tc, gauge, rest=f"transform:scaleY({levels[-1]});transform-box:fill-box;transform-origin:50% 100%;")
    f.add(rect(vx + 3, vy + 3, vw - 6, vh - 6, f"fb {cgv}", 2))
    qpos = [(qx, qy0 + 38 * i) for i in range(4)]
    for (x, y) in qpos:
        f.add(rect(x - 44, y - 14, 88, 28, "gr", 6, ' style="stroke-dasharray:3 4"'))
    # lease token rides above the active chip
    tok = []
    for k in range(4):
        s = slot * k
        qx_, qy_ = qpos[k]
        px_, py_ = qpos[k - 1] if k else qpos[3]
        dxr, dyr = res[0] - qx_, res[1] - qy_
        tok += [(s, f"transform:translate({px_}px,{py_}px)"), (s + 0.3, f"transform:translate({qx_}px,{qy_}px)")]
        for i in range(9):
            u = i / 8
            e = smooth(u)
            tok.append((s + 0.3 + 0.5 * u, f"transform:translate({n(qx_ + dxr * e)}px,{n(qy_ + dyr * e)}px)"))
        tok.append((s + 1.4, f"transform:translate({res[0]}px,{res[1]}px)"))
        for i in range(9):
            u = i / 8
            e = smooth(u)
            tok.append((s + 1.4 + 0.5 * u, f"transform:translate({n(res[0] - dxr * e)}px,{n(res[1] - dyr * e)}px)"))
        tok.append((s + slot - 0.001, f"transform:translate({qx_}px,{qy_}px)"))
    for k, name in enumerate(chips):
        s = slot * k
        qx_, qy_ = qpos[k]
        dxr, dyr = res[0] - qx_, res[1] - qy_
        pts = [(0.0, "transform:translate(0px,0px)"), (s + 0.3, "transform:translate(0px,0px)")]
        for i in range(9):
            u = i / 8
            e = smooth(u)
            pts.append((s + 0.3 + 0.5 * u, f"transform:translate({n(dxr * e)}px,{n(dyr * e)}px)"))
        pts.append((s + 1.4, f"transform:translate({n(dxr)}px,{n(dyr)}px)"))
        for i in range(9):
            u = i / 8
            e = smooth(u)
            pts.append((s + 1.4 + 0.5 * u, f"transform:translate({n(dxr * (1 - e))}px,{n(dyr * (1 - e))}px)"))
        pts.append((Tc, "transform:translate(0px,0px)"))
        rest = f"transform:translate({n(dxr)}px,{n(dyr)}px);" if k == 3 else "transform:translate(0px,0px);"
        c = f.anim(Tc, pts, rest=rest)
        f.add(f'<g transform="translate({qx_},{qy_})"><g class="{c}">' + rect(-44, -14, 88, 28, "bx", 6)
              + f.text(0, 5.5, name, "", 16, "middle") + "</g></g>")
    ctok = f.anim(Tc, tok, rest=f"transform:translate({res[0]}px,{res[1]}px);")
    f.add(f'<g class="{ctok}"><g transform="translate(72,0)">' + rect(-22, -10, 44, 20, "fa", 10)
          + f.text(0, 4.5, "lease", "i", 13, "middle", ' style="fill:var(--paper)"') + "</g></g>")
    f.add(f.text(gx + gw / 2, gy + gh + 22, "one lease, one resident model", "i k2", 15, "middle"))

    # ---- (d) degrade, don't die
    f.add(f.text(624, 302, "(d) Degrade, don\u2019t die", "i", 19))
    Td = 8.0
    tx0, tx1 = 744, 1128
    f.add(f.text(624, 360, "telemetry", "i k2", 16))
    f.add(f.text(624, 430, "render", "i k2", 16))
    nd = 14
    step = (tx1 - tx0) / (nd - 1)
    lost = 6
    for i in range(nd):
        x = tx0 + step * i
        t = 0.3 + (6.7 - 0.3) * i / (nd - 1)
        f.add(f'<circle cx="{n(x)}" cy="355" r="4" class="ff" style="stroke:var(--rule)"/>')
        c = f.anim(Td, vis(Td, [(t, 7.55)], fin=0.08, fout=0.3), rest="opacity:1;")
        if i == lost:
            f.add(f'<g class="{c}">' + cross(x, 355, 9) + f.text(x, 384, "frame lost", "i kr", 14, "middle") + "</g>")
        else:
            f.add(f'<circle cx="{n(x)}" cy="355" r="4.5" class="fb {c}"/>')
    f.add(rect(tx0, 418, tx1 - tx0, 16, "ln", 4))
    cbar = f.anim(Td, [(0.0, "transform:scaleX(0)"), (0.3, "transform:scaleX(0)"), (6.7, "transform:scaleX(1)"),
                       (7.55, "transform:scaleX(1)"), (7.85, "transform:scaleX(0)"), (Td, "transform:scaleX(0)")],
                  rest="transform:scaleX(1);transform-box:fill-box;transform-origin:0 50%;")
    f.add(rect(tx0 + 3, 421, tx1 - tx0 - 6, 10, f"fb {cbar}", 3))
    crun = f.anim(Td, vis(Td, [(0.3, 6.65)], fin=0.15, fout=0.15), rest="opacity:0;")
    cdone = f.anim(Td, vis(Td, [(6.75, 7.55)], fin=0.15, fout=0.3), rest="opacity:1;")
    f.add(f'<g class="{crun}">' + f.text(tx1, 460, "rendering", "i k2", 15, "end") + "</g>")
    f.add(f'<g class="{cdone}">' + f.text(tx1, 460, "render complete", "i kt", 15, "end") + "</g>")
    return f


if __name__ == "__main__":
    for build in (hero, hyperflow, pulsestudio, publishing, principles):
        fig = build()
        p = fig.save()
        print(f"{os.path.relpath(p, os.path.join(HERE, '..')):28s} {os.path.getsize(p) / 1024:6.1f} KB")
