# Elliptic geometry — closed disk model

Interactive visualisation of the **closed disk (hemisphere) model** of the elliptic
plane: build constructions out of as many points, lines, segments, triangles
and circles as you like and watch them behave the way elliptic geometry says
they must.

## How to run it

You need Python 3.10 or newer and two packages, `numpy` and `PySide6`.

**Linux** — in a terminal, from this folder:

```bash
pip3 install --user numpy PySide6   # first time only
python3 main.py
```

(If your distribution refuses the install with *externally-managed-environment*,
use a virtual environment: `python3 -m venv .venv && . .venv/bin/activate &&
pip install numpy PySide6`, then `python main.py`.)

**Windows** — install Python from [python.org](https://www.python.org/downloads/)
(tick *"Add python.exe to PATH"* in the installer), then in Command Prompt or
PowerShell, from this folder:

```bat
pip install numpy PySide6           REM first time only
python main.py
```

Either way a window opens with the tool palette on the left, the disk in the
middle and the 3-D sphere on the right — start clicking in the disk. Everything
below explains what the tools do and what the geometry means.

## The palette

Pick a tool on the left (or press its number), then click in the disk.

| tool | key | what a click does |
| --- | --- | --- |
| **Point** | `1` | drops a point; keep the button held to slide it into place |
| **Line** | `2` | first click picks a point, second click joins them into a full elliptic line |
| **Segment** | `3` | same, but draws the shortest path between the two points, with the rest of the line faint |
| **Perpendicular** | `4` | click a point and a line, **in either order**, to drop the perpendicular from the point onto the line |
| **Triangle** | `5` | three clicks; the sides are ordinary segments and the angles are measured |
| **Circle** | `0` | click the centre, then any point the circle should pass through |
| **Midpoint** | `m` | click two points for the middle of the shortest path between them |
| **Meet** | `6` | click two lines to name the point where they cross |
| **Bisect angle** | `n` | click two lines; both bisectors of their angles appear, as one action |
| **Polar / Pole** | `7` | click a point for its polar line, or a line for its pole |
| **Move** | `8` | drags a point; everything built on it follows |
| **Delete** | `9` | removes a point (and its lines) or a line on its own |

Line, Segment, Perpendicular, Triangle and Circle snap onto an existing point if you
click within ~13 px of one, and otherwise create a new point where you clicked —
so two clicks on empty space give you a line without placing its points first.
`esc` cancels a half-finished one.

Points come in two sorts. **Filled** ones are free: you put them there and you
can drag them. **Hollow diamonds** are derived — a meet or a pole — and they go
where their lines say they go. Drag what they are built on instead. Everything
is live: move one vertex and the triangles, perpendiculars, poles and meets
downstream of it all follow.

**Show** toggles: `l` labels (and the triangle readouts), `p` poles, `x` meets
(intersections), `e` rim ends, `o` switches the default **conformal** view to
the orthogonal one (see below), `b` **plain** — black ink on white, with line
weight doing the work colour was doing, and the rest of each line dashed. Turn
it on and the picture is the figure you would put in a paper; **Save GCLC**
then exports exactly that. And for the right-hand pane: `s` shows or hides the
**3-D sphere**, `r` its **projector** rays, `a` the **antipodes**.
The **Rotate** slider (`←`/`→` to nudge) turns the whole construction about a
point of your choosing — a live isometry of the plane, since a rotation about
an elliptic point *is* the rotation of the sphere about that point's axis.
Pick the pivot with the **Rotate about** tool (`t`): click any point — or any
empty spot, which makes one — and it wears a small ring; with none chosen the
figure turns about the centre of the disk. A pivot near the middle spins the
picture; a pivot at the rim rolls the figure out through the boundary and back
in on the far side. Watch the triangle readout while you drag: everything
moves except the pivot, and no distance, angle or area changes — that is what
a rigid motion of elliptic geometry means. Only free points really move
(derived points follow), nothing lands in the undo history, choosing a new
pivot restarts the slider at zero, and dragging it back to zero brings the
figure back exactly.
**Edit**: `u` undo the last action — a triangle and its three sides go together —
`c` clear everything, `g` **Save GCLC** (a box opens over the disk: type a file
name, press enter, `esc` cancels) — `G` saves the same thing plain, in black and
white. **Colour** swatches set the colour of the *next* object; `auto` cycles the
palette. Clicks outside the disk snap to the rim.

`python3 main.py --points 0.35 0.45 -0.6 0.2 0.1 -0.7 --lines 0 1 --perps 2 0
--save out.png` renders a fixed construction to an image instead of opening a
window. `--triangles`, `--circles`, `--polars` and `--meets` build the rest;
this draws a triangle, its three altitudes and the orthocentre they share:

```bash
python3 main.py --points 0.0 0.35 0.55 -0.3 -0.5 -0.25 \
                --triangles 0 1 2 --perps 2 0 0 1 1 2 --meets 3 4
```

## The sphere on the right

The disk is the upper hemisphere flattened out, and the right-hand pane
un-flattens it. The same construction is drawn twice over: once on the ball it
actually lives on, as arcs of real great circles, and once lying in the
equatorial plane underneath — which is the picture the left-hand pane shows.
Dotted **projector** rays join the two, one per point, so you can see exactly
which point of the sphere became which point of the disk. **Drag a vertex on the
left and the great circle swings round on the right.**

The tinted half is the model: `{v : v·ẑ ≥ 0}`, one representative of every
elliptic point. Turn on **Antipodes** (`a`) and each point's other
representative `−v` appears, joined to it through the centre — that dotted line
*is* the identification, and you can watch a point cross the rim on the left
while its antipode crosses in from the other side.

The rays change with the projection. In the default **conformal** view they
start at the south pole, which is what stereographic projection is; press `o`
and they drop straight down for the orthogonal view. Everything else in the
pane stays put, because nothing about the sphere depends on how you choose to
flatten it.

Drag to turn the camera, wheel to zoom, double-click to go back to where you
started. The camera is orthographic, so the silhouette is exactly the unit
circle and a point is in front exactly when it is on the camera's side of the
plane through the centre — hidden lines are cut on that boundary rather than
guessed at, and what goes round the back is drawn faintly through the ball.
Dragging here only turns the camera; the construction is edited on the disk.

## Two ways of looking at it

The disk is the hemisphere drawn flat, and there is more than one way to draw it
flat. `o` switches between them; the model, the tools and every measurement are
untouched — only where a point of the sphere lands on the page.

| | **conformal** (default) | **orthogonal** (`o`) |
| --- | --- | --- |
| how | from the south pole: `(x,y)/(1+z)` | straight down: drop `z` |
| a line is | an arc of a circle, centre `(n₁,n₂)/n₃`, radius `1/\|n₃\|` | half an ellipse, semi-axes 1 and `\|n_z\|` |
| angles | **true everywhere** — the right-angle marks square up | distorted away from the centre |
| distance | not read off the page | `arccos\|p·q\|`, rim at exactly π/2 |
| in GCLC | `drawellipsearc2` on a circle | `drawellipsearc2` |

Both fix the rim, so opposite boundary points stay identified either way, and a
diameter stays a diameter in both. The default conformal view is the textbook
disk picture, including circles that may appear as two circular arcs; the
orthogonal view is useful when the figure is about distance. Use
`--orthogonal` to select it on the command line.

## Exporting to GCLC

**Save GCLC** (`g`, or `--gclc out.gcl` on the command line) writes the current
construction as a [GCLC](https://poincare.matf.bg.ac.rs/~janicic/gclc/) file —
Predrag Janičić's *Geometry Constructions → LaTeX Converter*, University of
Belgrade. From there:

```bash
gclc drawing.gcl          # -> a LaTeX picture
gclc -svg drawing.gcl     # -> SVG
```

**The curves stay curves.** A great circle projects to an *ellipse* about the
centre of the disk — semi-major axis 1, semi-minor axis `|n_z|` — and an elliptic
line is exactly half of it. So each line is one `drawellipsearc` and each segment
one `drawellipsearc2`, not a few hundred little straight pieces. The two
degenerate cases say what they are: `n_z = 0` is a diameter, drawn straight, and
the equator is the rim circle itself.

Everything is written in the model's own coordinates — GCLC's Cartesian layer
(`ang_origin`, `ang_unit`, `ang_point`) puts the unit disk on the page, so the
numbers in the file are the numbers in the construction rather than millimetres.
Points arrive under their own names with their labels and colours; the disk, the
identification chords, the right-angle marks and the angle arcs come across too.
GCLC has no transparency, so what the viewer draws faintly is written as a paler
shade of the same colour. The measurements with no GCLC home (a triangle's angles
and its area) go into the comments, where they travel with the file anyway.

**Plain** (`G` in the viewer, or `--gclc out.gcl --plain`) draws it the way it
would have been drawn on paper: no colour at all, and the rest of each line
*dashed* rather than faint — `drawdashellipsearc`, which is the same arc in the
same place, only broken. Black ink, bold construction, dashed continuations,
italic labels: an old textbook figure.

Two things worth knowing. GCLC insets an arc by about a quarter of a millimetre
at each end — invisible under the point marks, but that is why a segment stops
a hair short of its point. And `circleprecision <n>` will make arcs smoother if
you are exporting to LaTeX at a large size.

The elliptic plane is the sphere with antipodal points identified. Each class
`{v, −v}` has a representative on the closed upper hemisphere, and projecting
that hemisphere straight down gives the closed unit disk — with **opposite
boundary points being one and the same point**, which is what the dashed rim is
there to remind you of.

* **Point** — a disk point `(x, y)` lifts to `(x, y, √(1 − x² − y²))`.
* **Line** — a great circle, i.e. the unit vectors orthogonal to a normal
  `n = p × q`. Its upper half projects to *half* an ellipse with semi-major axis
  1 and semi-minor axis `|n_z|`, running from a rim point to its antipode (the
  hollow markers, joined by a dotted chord). `n_z = 0` degenerates to a diameter;
  two rim points give the boundary circle itself.
* **No parallels** — every pair of lines meets in exactly one point, marked `✕`
  when *Meets* is on. Three lines through one point report a single meet. The
  *Meet* tool turns a crossing into a real point you can build on, and the `✕`
  gives way to it.
* **Pole** — every line has one, the point at distance π/2 from all of it, drawn
  as a star in the line's colour.
* **A segment really has two midpoints.** *Midpoint* halves the shortest path —
  the one the segment tool draws — but the two points also cut their line into a
  second, longer arc, and that one has a middle too, a quarter turn (π/2) along
  the line from the first. Drag the ends until they are exactly π/2 apart and
  the two halvings trade places. The midpoint is derived: it stays halfway
  through every drag, and it goes when either end goes.
* **Angle bisectors come in pairs.** Two lines cross in one point but make two
  pairs of vertical angles, so *Bisect angle* draws **two** bisectors — with
  normals `m̂+n̂` and `m̂−n̂` — always perpendicular to each other and crossing at
  the meet. They are live: drag a parent line and both halvings follow. A good
  thing to try: bisect the angles at two vertices of a triangle, *Meet* the two
  interior bisectors — that is the incentre — drop a *Perpendicular* from it
  onto a side, and the circle about the incentre through the foot is the
  inscribed circle, tangent to all three sides through every drag.
* **Duality** — a point and a line are the same kind of thing here. The polar of
  a point `P` is the line of everything π/2 away from it; the pole of a line is
  the point π/2 from all of it; and each undoes the other exactly. So *Polar /
  Pole* is one tool: click a point to get a line, click a line to get a point.
  Dualise a whole figure and collinear points become concurrent lines.
* **Perpendicular** — the perpendicular from a point `P` to a line `ℓ` is just
  the join of `P` and the pole of `ℓ`, since every line through that pole crosses
  `ℓ` at a right angle. So it exists and is unique for every `P` *except* the pole
  itself, where every line through `P` is perpendicular and the tool says so. The
  bold part runs from `P` down to the foot (small square); the distance shown is
  `arcsin|p·n|`, which is π/2 minus the distance to the pole. A perpendicular is a
  line like any other — you can drop a perpendicular onto a perpendicular, and
  deleting a line takes everything built on it.
* **The right-angle mark is honestly slanted.** Orthogonal projection is not
  conformal, so a genuine right angle only *looks* like one near the centre. The
  mark is a real square on the sphere, projected — the further out it sits, the
  more it leans. It is dropped entirely at the rim, where it would tear across
  the disk. A good check: drop perpendiculars from two different points onto the
  same line and watch them meet at that line's pole.
* **Distance** — the angle between the lifted vectors, folded by the
  identification: `d = arccos(|p·q|)`, never more than π/2. When two points are
  far apart the shortest path leaves the disk through the rim and re-enters
  opposite; the segment is then drawn in two pieces.
* **Triangle** — the angles are read off at the vertices, marked with little arcs
  that are drawn on the sphere and projected, so they lean like the right-angle
  mark does. Their sum always beats π, and by Girard's theorem the excess *is*
  the area: `area = α + β + γ − π`. Drag a vertex and watch it move. Shrink the
  triangle towards the centre and the excess goes to zero — Euclidean geometry
  is what elliptic geometry looks like when you stop paying attention.
* **A triangle that bounds nothing.** Three points do not always cut a piece out
  of the plane. Follow the three shortest sides around and each one picks the
  nearer lift of its far end; walking all three lands you back on `a` or on `−a`
  according to the sign of `(a·b)(b·c)(c·a)`. When it lands on `−a` the loop runs
  out through the rim and back in on the other side without ever enclosing a
  disk, Girard's formula has nothing to apply to, and the readout says so
  instead of printing a number. Pull one vertex back in and the area returns.
* **Circle** — everything at one distance from a centre: a plane section of the
  sphere, which the disk shows as a closed curve (an ellipse seen straight down,
  a true circle in the conformal view — the centre visibly off-middle in both,
  because the geometry's centre is not the picture's). Two clicks make one:
  the centre, then any point it should pass through, and dragging either
  resizes it live. Push the centre towards the rim and the far side of the
  circle slips out through the boundary and comes back in opposite, in two
  arcs, exactly as a long segment does. And grow the radius towards π/2 and
  the circle flattens into a *line* — the polar of its centre, which the
  readout names when you hit it. In this geometry a big enough circle is a
  line, and that is duality made visible.

Things worth trying: drag a triangle vertex to the rim and watch a side jump to
the other side of the disk, and the area give up; turn on poles and see that a
line's pole is where all its perpendiculars meet; drop the three altitudes of a
triangle (perpendicular from each vertex to the opposite side) and use *Meet* to
name the orthocentre — then drag a vertex and watch the three stay concurrent;
circle a line's pole through any point of the line and watch the circle hug the
line itself.

## Layout

| path | contents |
| --- | --- |
| [elliptic/geometry.py](elliptic/geometry.py) | the maths: lifting, lines, segments, circles, distance, duality, angles and area |
| [elliptic/model.py](elliptic/model.py) | the construction: what is built on what, and how it comes apart again |
| [elliptic/scene.py](elliptic/scene.py) | what to draw, in sphere coordinates — both panes consume it |
| [elliptic/viewer.py](elliptic/viewer.py) | the tools: what a click does, toolkit-free |
| [elliptic/ui/](elliptic/ui/) | the PySide6 window: the disk pane, the 3-D sphere pane |
| [elliptic/gclc.py](elliptic/gclc.py) | the GCLC exporter |
| [main.py](main.py) | entry point |
| [docs/](docs/) | `make -C docs` — the mathematics written out: both projections, every object, with proofs |
| [tests/](tests/) | `python3 -m tests` — 227 checks over the maths, the model, the export and the tools |

Nothing in the construction stores a position or a normal: every object holds
references to the objects it was built from and re-derives itself on demand.
That is what makes dragging work, and it is why deleting something takes
everything downstream of it with it.

## Requirements

numpy and PySide6.

```bash
pip3 install --user numpy PySide6
```
