# Elliptic geometry — closed disk model

Interactive visualisation of the **closed disk (hemisphere) model** of the elliptic
plane. Build constructions out of points, lines, segments, triangles and circles
and watch them behave the way elliptic geometry says they must — on a flat disk
on the left, and on the sphere the disk is a picture of on the right. What you
build can be exported as a PNG image, a [GCLC](https://poincare.matf.bg.ac.rs/~janicic/gclc/)
file or TikZ source for LaTeX.

**Contents**

1. [Install and run locally](#1-install-and-run-locally) — Linux, Windows, checking the install, updating, uninstalling
2. [Using the program](#2-using-the-program) — the palette, the sphere pane, the two projections, the command line
3. [Exporting](#3-exporting) — TikZ and GCLC
4. [The geometry](#4-the-geometry) — what every object means
5. [Project layout](#5-project-layout)

---

## 1. Install and run locally

The program is a plain Python application. It is not "installed" in the usual
sense: everything it needs goes into a **virtual environment** (a private
folder named `.venv`) inside the project folder, nothing is written anywhere
else on the machine, and deleting the folder removes it completely. The steps
below are the same on every machine; only the shell commands differ between
Linux and Windows.

### What you need

| | |
| --- | --- |
| **Python** | 3.10 or newer. Developed and tested on 3.13. |
| **Packages** | `numpy` and `PySide6` (Qt 6) — both listed in [requirements.txt](requirements.txt) and installed in step 3 below. |
| **Git** | optional, only to clone and later update the repository. A downloaded ZIP works just as well. |
| **LaTeX** | optional, only to rebuild the PDF in [docs/](docs/) or to typeset the TikZ exports. |

The source lives at <https://github.com/aleksandarivke96/ElipticDiskVisualisation>.

### Linux

1. **Install Python** together with its `venv` module. On Debian and Ubuntu:

   ```bash
   sudo apt install python3 python3-venv python3-pip
   ```

   On Fedora: `sudo dnf install python3`. On Arch: `sudo pacman -S python`.

2. **Get the code** and go into the folder:

   ```bash
   git clone https://github.com/aleksandarivke96/ElipticDiskVisualisation.git
   cd ElipticDiskVisualisation
   ```

   Without Git: download the repository as a ZIP from GitHub (*Code → Download
   ZIP*), unpack it and `cd` into the unpacked folder.

3. **Create the virtual environment** and install the two packages into it:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

   The prompt gains a `(.venv)` prefix while the environment is active.

4. **Run it:**

   ```bash
   python main.py
   ```

   A window opens with the tool palette on the left, the disk in the middle and
   the 3-D sphere on the right. Start clicking in the disk.

**Every later time:** open a terminal in the folder, `source .venv/bin/activate`,
`python main.py`. You can also skip the activation and call the environment's
interpreter directly: `.venv/bin/python main.py`.

**If no window opens.** PySide6 brings its own copy of Qt, but Qt relies on a
handful of system libraries that a minimal installation may lack. The error
looks like *"Could not load the Qt platform plugin 'xcb'"*. On Debian/Ubuntu:

```bash
sudo apt install libxcb-cursor0 libxcb-xinerama0 libxkbcommon-x11-0 \
                 libegl1 libgl1 libfontconfig1 libdbus-1-3
```

On a Wayland desktop, if the window behaves oddly, force the X11 backend with
`QT_QPA_PLATFORM=xcb python main.py`. If `pip install` complains about an
*externally-managed-environment*, the virtual environment is not active — run
the `source` line from step 3 again; nothing here should ever be installed into
the system Python.

### Windows

1. **Install Python** from [python.org](https://www.python.org/downloads/) and
   tick **"Add python.exe to PATH"** in the installer. From a terminal,
   `winget install Python.Python.3.12` does the same. Prefer this over the
   Microsoft Store build: the Store version lives under a very long path, which
   can make the PySide6 install fail.

2. **Get the code.** In a terminal:

   ```powershell
   git clone https://github.com/aleksandarivke96/ElipticDiskVisualisation.git
   cd ElipticDiskVisualisation
   ```

   Without Git: download the ZIP from GitHub, unpack it, then open a terminal
   in that folder (in Explorer, right-click the folder → *Open in Terminal*, or
   type `powershell` into the address bar).

3. **Create the virtual environment** and install the two packages into it.
   In **PowerShell**:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

   In **Command Prompt** the activation line is `.venv\Scripts\activate.bat`
   instead. If PowerShell refuses the activation script with *"running scripts
   is disabled on this system"*, allow it once for your user account and try again:

   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```

   The prompt gains a `(.venv)` prefix while the environment is active.

4. **Run it:**

   ```powershell
   python main.py
   ```

**Every later time:** open a terminal in the folder, run the activation line,
`python main.py`. Without activating: `.venv\Scripts\python.exe main.py`.

### Checking the install

With the environment active, from the project folder:

```bash
python main.py --help     # lists the command-line options
python -m tests           # runs every check; ends with "258 passed, 0 failed"
```

The tests need no screen — the window tests run on Qt's offscreen platform —
so they work over SSH and in CI as well.

### Running without a screen

Give `main.py` something to export and it draws the construction to a file and
exits instead of opening a window:

```bash
python main.py --points 0.35 0.45 -0.6 0.2 0.1 -0.7 --lines 0 1 --perps 2 0 --save out.png
```

On Linux the program switches to Qt's offscreen platform by itself when neither
`DISPLAY` nor `WAYLAND_DISPLAY` is set, so this also works on a headless server.
`--gclc`, `--tikz` and `--tikz-3d` export in the same way; see
[the command line](#the-command-line) for the full set of options.

### Updating, leaving, uninstalling

- **Update** — inside the folder, with the environment active:
  `git pull` then `pip install --upgrade -r requirements.txt`. (For a ZIP
  install, unpack the new version over the old one and run the `pip` line.)
- **Leave the environment** — type `deactivate`, or just close the terminal.
- **Uninstall** — delete the `.venv` folder, or the whole project folder.
  Nothing was written anywhere else.

### Building the write-up (optional)

[docs/elliptic-disk-model.pdf](docs/elliptic-disk-model.pdf) is the mathematics
behind the program — both projections, every object, with proofs — and it is
already built. To rebuild it after editing the `.tex` source you need a LaTeX
distribution (TeX Live on Linux, [MiKTeX](https://miktex.org/) or TeX Live on
Windows). Then `make -C docs` on Linux, or on either system run
`pdflatex elliptic-disk-model.tex` twice inside the `docs` folder.

---

## 2. Using the program

### The palette

Pick a tool on the left (or press its key), then click in the disk.

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
| **Rotate about** | `t` | click the point the **Rotate** slider should turn the figure around |
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
the orthogonal one (see [two ways of looking at it](#two-ways-of-looking-at-it)),
`b` **plain** — black ink on white, with line weight doing the work colour was
doing, and the rest of each line dashed. Turn it on and the picture is the
figure you would put in a paper; **Save GCLC** or **Save TikZ** then exports
that style. And for the right-hand pane: `s` shows or hides the **3-D sphere**,
`r` its **projector** rays, `a` the **antipodes**.

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
`c` clear everything. **Save GCLC** (`g`), **Save TikZ** (`k`) and **Save 3D
TikZ** (`v`) open a box over the disk: type a file name, press enter, `esc`
cancels. The capital letters `G`, `K` and `V` save the same thing plain, in
black and white. **Colour** swatches set the colour of the *next* object;
`auto` cycles the palette. Clicks outside the disk snap to the rim.

### The sphere on the right

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
Start with `--no-sphere` to leave the pane out altogether.

### Two ways of looking at it

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

### The command line

Everything the palette can build, the command line can build too, and then
either open the window on it or export it and exit. Coordinates name positions
in the view being rendered, exactly like mouse clicks do.

| option | meaning |
| --- | --- |
| `--points X Y X Y …` | start with these points placed; they are numbered 0, 1, 2, … in this order |
| `--lines I J …` | join points by index into full lines |
| `--segments I J …` | like `--lines` but draws the shortest path |
| `--triangles I J K …` | triangles on three point indices each, with their angles |
| `--perps P L …` | drop a perpendicular from point `P` onto line `L` |
| `--polars I …` | the polar line of each of those points |
| `--bisects I J …` | both angle bisectors of two lines, by line index |
| `--midpoints I J …` | the midpoint of each pair of points |
| `--meets I J …` | name the point where two lines cross, by line index |
| `--circles C T …` | a circle about point `C` through point `T` |
| `--save PATH` | render to an image file and exit |
| `--gclc PATH` | write a GCLC file and exit |
| `--tikz PATH` | write the disk as TikZ source and exit |
| `--tikz-3d PATH` | write the sphere view as TikZ source and exit |
| `--plain` | with the exports: monochrome, construction lines dashed |
| `--conformal` / `--orthogonal` | choose the projection (conformal is the default) |
| `--no-sphere` | leave out the 3-D pane |

Line indices count in creation order: `--lines`, then `--segments`, then the
three sides of each `--triangles` entry, then `--perps`, then `--polars` — so a
perpendicular can be dropped onto a triangle's side. This draws a triangle, its
three altitudes and the orthocentre they share:

```bash
python main.py --points 0.0 0.35 0.55 -0.3 -0.5 -0.25 \
               --triangles 0 1 2 --perps 2 0 0 1 1 2 --meets 3 4
```

(On Windows write it on one line without the backslashes.)

---

## 3. Exporting

### TikZ

**Save TikZ** (`k`, or `--tikz drawing.txt` on the command line) writes the
2-D disk construction as a TikZ `tikzpicture` in a plain text file. The export
uses the current conformal or orthogonal view. If the filename has no extension,
`.txt` is added automatically; the default filename is `construction.txt`.

Use `K` to save in black and white, or turn on **Plain** (`b`) before saving.
On the command line, add `--plain`:

```bash
python main.py --points 0.0 0.35 0.55 -0.3 -0.5 -0.25 \
               --triangles 0 1 2 --tikz drawing.txt --plain
```

Add `\usepackage{tikz}` to your LaTeX document's preamble, then paste the exported
text into the document or load the file with `\input{drawing.txt}`:

```latex
\documentclass{article}
\usepackage{tikz}
\begin{document}
\input{drawing.txt}
\end{document}
```

**Save 3D TikZ** (`v`) exports the sphere view to `sphere.txt`. Turn and zoom the
sphere before saving to choose the camera. The file includes the sphere grid,
the construction on its surface, its flattened copy in the equatorial disk,
and the enabled labels, poles, intersections, projector rays and antipodes.
Rear curves are faded through the sphere. The **Conformal** toggle determines
how the construction lands on the equatorial disk and how the projector rays run.
Use `V`, or the **Plain** toggle, for a monochrome figure.

The 3-D export is an editable vector picture of that camera view. Include it
with `\input{sphere.txt}` using the same `\usepackage{tikz}` preamble above.
On the command line, `--tikz-3d sphere.txt` uses the default camera; it can be
combined with the disk export:

```bash
python main.py --points 0.0 0.35 0.55 -0.3 -0.5 -0.25 \
               --triangles 0 1 2 --tikz drawing.txt --tikz-3d sphere.txt
```

Add `--plain` for monochrome output or `--orthogonal` for the orthogonal
projection. These exports combine freely with `--gclc drawing.gcl` and
`--save drawing.png`.

### GCLC

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

---

## 4. The geometry

The elliptic plane is the sphere with antipodal points identified. Each class
`{v, −v}` has a representative on the closed upper hemisphere, and projecting
that hemisphere straight down gives the closed unit disk — with **opposite
boundary points being one and the same point**, which is what the dashed rim is
there to remind you of. The full account, with proofs, is in
[docs/elliptic-disk-model.pdf](docs/elliptic-disk-model.pdf).

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

---

## 5. Project layout

| path | contents |
| --- | --- |
| [main.py](main.py) | entry point: the window, or the command-line exports |
| [requirements.txt](requirements.txt) | the two packages the program needs |
| [elliptic/geometry.py](elliptic/geometry.py) | the maths: lifting, lines, segments, circles, distance, duality, angles and area |
| [elliptic/model.py](elliptic/model.py) | the construction: what is built on what, and how it comes apart again |
| [elliptic/scene.py](elliptic/scene.py) | what to draw, in sphere coordinates — both panes consume it |
| [elliptic/viewer.py](elliptic/viewer.py) | the tools: what a click does, toolkit-free |
| [elliptic/ui/](elliptic/ui/) | the PySide6 window: the disk pane, the 3-D sphere pane, image rendering |
| [elliptic/sphere.py](elliptic/sphere.py) | shared sphere camera and visibility geometry |
| [elliptic/gclc.py](elliptic/gclc.py) | the GCLC exporter |
| [elliptic/tikz.py](elliptic/tikz.py) | the TikZ exporter for the disk |
| [elliptic/tikz_sphere.py](elliptic/tikz_sphere.py) | the TikZ exporter for the 3-D sphere view |
| [tests/](tests/) | `python -m tests` — checks over the maths, the model, the exports, the tools and the window |
| [docs/](docs/) | the mathematics written out, as LaTeX source and the built PDF; `make -C docs` rebuilds it |

Nothing in the construction stores a position or a normal: every object holds
references to the objects it was built from and re-derives itself on demand.
That is what makes dragging work, and it is why deleting something takes
everything downstream of it with it.
