# Elliptic geometry: closed disk model

Explore elliptic geometry with the **closed disk (hemisphere) model**. Build
points, lines, segments, triangles and circles, then view them on a flat disk
and a 3D sphere side by side. Export your construction as a PNG image, a
[GCLC](https://poincare.matf.bg.ac.rs/~janicic/gclc/) file or TikZ source for LaTeX.

**Contents**

1. [Install and run locally](#1-install-and-run-locally)
2. [Using the program](#2-using-the-program)
3. [Exporting](#3-exporting)
4. [The geometry](#4-the-geometry)
5. [Project layout](#5-project-layout)

## 1. Install and run locally

The program runs in Python. Its packages go into a **virtual environment**,
a folder named `.venv` inside the project. Follow the steps for your system below.

### What you need

| | |
| --- | --- |
| **Python** | 3.10 or newer. Developed and tested on 3.13. |
| **Packages** | `numpy` and `PySide6` (Qt 6), installed from [requirements.txt](requirements.txt) in step 3. |
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

   The terminal prompt shows `(.venv)` while the environment is active.

4. **Run it:**

   ```bash
   python main.py
   ```

   A window opens with the tool palette on the left, the disk in the middle and
   the 3D sphere on the right. Click in the disk to start building.

**To run again:** open a terminal in the project folder and run
`.venv/bin/python main.py`. You can also activate the environment and run
`python main.py`.

**If no window opens:** Qt may need extra system libraries. If you see
*"Could not load the Qt platform plugin 'xcb'"*, install these on Debian/Ubuntu:

```bash
sudo apt install libxcb-cursor0 libxcb-xinerama0 libxkbcommon-x11-0 \
                 libegl1 libgl1 libfontconfig1 libdbus-1-3
```

On a Wayland desktop, if the window behaves oddly, force the X11 backend with
`QT_QPA_PLATFORM=xcb python main.py`. If `pip install` complains about an
*externally-managed-environment*, activate the virtual environment with the
`source` line from step 3, then try again.

### Windows

1. **Install Python** from [python.org](https://www.python.org/downloads/) and
   tick **"Add python.exe to PATH"** in the installer. You can also use
   `winget install Python.Python.3.12` in a terminal.

2. **Get the code.** In a terminal:

   ```powershell
   git clone https://github.com/aleksandarivke96/ElipticDiskVisualisation.git
   cd ElipticDiskVisualisation
   ```

   Without Git: download the ZIP from GitHub, unpack it, then open a terminal
   in that folder (in Explorer, right click the folder → *Open in Terminal*, or
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

   The terminal prompt shows `(.venv)` while the environment is active.

4. **Run it:**

   ```powershell
   python main.py
   ```

**To run again:** open a terminal in the project folder and run
`.venv\Scripts\python.exe main.py`. You can also activate the environment and
run `python main.py`.

### Checking the install

With the environment active, from the project folder:

```bash
python main.py --help     # lists the available options
python -m tests           # runs all checks
```

The window tests use Qt's offscreen platform, so the tests also work over SSH
and in CI without a display.

### Running without a screen

Add an export option to save a file without opening a window:

```bash
python main.py --points 0.35 0.45 -0.6 0.2 0.1 -0.7 --lines 0 1 --perps 2 0 --save out.png
```

On Linux the program switches to Qt's offscreen platform by itself when neither
`DISPLAY` nor `WAYLAND_DISPLAY` is set, so this also works on a headless server.
`--gclc`, `--tikz` and `--tikz-3d` export in the same way; see
[the command line](#the-command-line) for the full set of options.

### Updating, leaving, uninstalling

* **Update:** in the project folder, with the environment active, run `git pull`
  then `pip install --upgrade -r requirements.txt`. For a ZIP download, unpack
  the new version over the old one and run the same `pip` command.
* **Leave the environment:** type `deactivate` or close the terminal.
* **Uninstall:** delete `.venv` to remove the packages, or delete the whole
  project folder.

### Building the PDF (optional)

[docs/elliptic-disk-model.pdf](docs/elliptic-disk-model.pdf) explains both
projections and the geometry, with proofs. The PDF is included in the repository.
To rebuild it, install TeX Live or [MiKTeX](https://miktex.org/), then run
`make -C docs` on Linux. On either system, you can instead run
`pdflatex elliptic-disk-model.tex` twice from the `docs` folder.

## 2. Using the program

### The palette

Pick a tool on the left (or press its key), then click in the disk.

| tool | key | what a click does |
| --- | --- | --- |
| **Point** | `1` | place a point; hold and drag to adjust it |
| **Line** | `2` | click two points to draw a full elliptic line |
| **Segment** | `3` | click two points to draw the shortest path, with the rest of the line faint |
| **Perpendicular** | `4` | click a point and a line in either order to draw a perpendicular |
| **Triangle** | `5` | click three points to draw the sides and measure the angles |
| **Circle** | `0` | click the centre, then any point the circle should pass through |
| **Midpoint** | `m` | click two points for the middle of the shortest path between them |
| **Meet** | `6` | click two lines to name the point where they cross |
| **Bisect angle** | `n` | click two lines to draw both angle bisectors |
| **Polar / Pole** | `7` | click a point for its polar line, or a line for its pole |
| **Move** | `8` | drag a point and update everything built on it |
| **Rotate about** | `t` | click the point the **Rotate** slider should turn the figure around |
| **Delete** | `9` | remove an object and everything that depends on it |

Line, Segment, Perpendicular, Triangle and Circle use an existing point when
you click within about 13 pixels of it. Otherwise they create a new point.
For example, two clicks on empty space create a line and its two points.
Press `esc` to cancel an unfinished construction. Clicks outside the disk snap
to the rim.

**Filled points** can be dragged directly. **Hollow diamonds**, such as
intersections and poles, are calculated from other objects. Move those objects
to change them. Everything built on a moved point updates automatically.

**Display controls:**

| key | action |
| --- | --- |
| `l` | show labels and triangle measurements |
| `p` | show poles |
| `x` | show intersections |
| `e` | show line endpoints on the rim |
| `o` | switch between conformal and orthogonal projection |
| `b` | use black and white, with dashed line continuations |
| `s` | show the 3D sphere |
| `r` | show projection rays |
| `a` | show antipodes |

The **Rotate** slider turns the construction around a chosen point while
preserving distances, angles and areas. Use `←`/`→` for small adjustments.
Select the pivot with **Rotate about** (`t`), then click a point or an empty
spot to create one. A small ring marks the pivot. The default pivot is the disk
centre. A pivot on the rim moves the figure through the boundary and back in
on the opposite side.

Rotation is not added to the undo history. Choosing a new pivot resets the
slider to zero; returning the slider to zero restores the starting position
for that pivot.

**Editing and saving:** press `u` to undo the last action or `c` to clear
everything. Undo removes a triangle and its sides together. **Save GCLC** (`g`),
**Save TikZ** (`k`) and **Save 3D TikZ** (`v`) open a filename box. Type a name
and press enter, or `esc` to cancel. Use `G`, `K` or `V` to save in black and
white. The **Colour** swatches set the next object's colour; `auto` cycles
through the palette.

### The sphere on the right

The right pane shows the construction on the sphere and its projection onto
the equatorial disk. Dotted **projector** rays connect each sphere point to its
disk position. Changes made on the left appear on the right immediately.

The tinted upper hemisphere contains a representative of every elliptic point.
Turn on **Antipodes** (`a`) to show each point's opposite representative `−v`,
joined to it through the sphere's centre. These two representatives are the
same elliptic point.

In the default **conformal** view, projection rays start at the south pole.
Press `o` for the orthogonal view, where rays drop straight down. Changing the
projection does not change the construction on the sphere.

Drag to turn the camera, scroll to zoom, and double click to reset the view.
Curves behind the sphere appear faint. Edit the construction in the disk pane;
dragging in the sphere pane only moves the camera. Use `--no-sphere` to hide it
at startup.

### Two ways of looking at it

Press `o` to switch between two projections of the hemisphere onto the disk.
This changes how the construction looks, but preserves its geometry and
measurements. Here `n` is the unit normal of a line and `p`, `q` are unit sphere
vectors.

| | **conformal** (default) | **orthogonal** (`o`) |
| --- | --- | --- |
| how | from the south pole: `(x,y)/(1+z)` | straight down: drop `z` |
| a line is | a circular arc, centre `(n_x,n_y)/n_z`, radius `1/\|n_z\|` | half an ellipse with semi-major axis 1 and semi-minor axis `\|n_z\|` |
| angles | preserved | generally distorted |
| distance | `arccos(\|p·q\|)` on the sphere | the same sphere distance |
| in GCLC | `drawellipsearc2` on a circle | `drawellipsearc2` |

Both projections keep the rim fixed and identify opposite boundary points.
When `n_z = 0`, the line is a diameter in both views. The equator is the whole
rim circle. Use `--orthogonal` to select the orthogonal view at startup.

### The command line

Use command line options to create a construction, then open it in the window
or export it. Coordinates refer to positions in the selected disk projection.

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
| `--no-sphere` | hide the 3D pane |

Line indices count in creation order: `--lines`, then `--segments`, then the
three sides of each `--triangles` entry, then `--perps`, then `--polars`.
For example, this draws a triangle, its three altitudes and their intersection
(the orthocentre):

```bash
python main.py --points 0.0 0.35 0.55 -0.3 -0.5 -0.25 \
               --triangles 0 1 2 --perps 2 0 0 1 1 2 --meets 3 4
```

(On Windows write it on one line without the backslashes.)

## 3. Exporting

### TikZ

**Save TikZ** (`k`, or `--tikz drawing.txt` on the command line) writes the
2D disk construction as a TikZ `tikzpicture` in a plain text file. The export
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
sphere before saving to choose the view. The file includes the sphere grid,
the construction on the sphere and disk, and any enabled labels, poles,
intersections, projection rays and antipodes. Curves behind the sphere appear
faded. Use `V` or the **Plain** toggle for black and white.

Include the file with `\input{sphere.txt}` using the same LaTeX preamble above.
On the command line, `--tikz-3d sphere.txt` uses the default camera and can be
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
construction as a [GCLC](https://poincare.matf.bg.ac.rs/~janicic/gclc/) file.
GCLC is Predrag Janičić's *Geometry Constructions → LaTeX Converter* from the
University of Belgrade. Convert the exported file with:

```bash
gclc drawing.gcl          # -> a LaTeX picture
gclc -svg drawing.gcl     # -> SVG
```

The export uses the selected projection: circular arcs in the conformal view
and elliptical arcs in the orthogonal view. Line and segment arcs use
`drawellipsearc2`. Diameters are straight segments, and the equator is the rim
circle.

Coordinates stay in the model's unit disk. The file includes point names,
labels, colours, the disk boundary, identification chords and angle marks.
GCLC uses paler colours for faint objects because it has no transparency.
Triangle angle and area measurements are saved as comments.

**Plain** (`G` in the viewer, or `--gclc out.gcl --plain`) uses black and white,
bold construction lines and dashed continuations.

GCLC shortens arcs slightly at their endpoints, usually hidden by the point
marks. Increase `circleprecision <n>` if arcs look rough in a large LaTeX export.

## 4. The geometry

The elliptic plane is the unit sphere with antipodal points identified: `v` and
`−v` represent the same point. The program uses the closed upper hemisphere and
projects it onto the unit disk. **Opposite boundary points represent the same
point** in both projections. See
[docs/elliptic-disk-model.pdf](docs/elliptic-disk-model.pdf) for proofs.

* **Point.** A disk point `(x, y)` lifts to a unit vector on the hemisphere.
  In the orthogonal view this is `(x, y, √(1 − x² − y²))`. In the default
  conformal view it is `(2x, 2y, 1 − r²)/(1 + r²)`, where `r² = x² + y²`.
* **Line.** Two distinct elliptic points with unit vectors `p` and `q` define
  a great circle with unit normal `n = (p × q)/‖p × q‖`. Its points satisfy
  `n·v = 0`. In the orthogonal view, its upper half is half an ellipse with
  semi-major axis 1 and semi-minor axis `|n_z|`. In the conformal view, it is
  a circular arc with centre `(n_x/n_z, n_y/n_z)` and radius `1/|n_z|`.
  In either view, `n_z = 0` gives a diameter, and a vertical normal gives the
  boundary circle. Two distinct, non-antipodal rim points define that boundary
  line. Hollow markers show a line's antipodal rim ends when enabled.
* **No parallels.** Any two distinct lines meet in exactly one elliptic point.
  The *Meets* toggle marks intersections with `✕` and combines coincident
  intersections. The *Meet* tool creates a derived point at an intersection
  so other objects can use it.
* **Pole.** A line's unit normal represents its pole, the point at distance
  π/2 from every point of the line. The pole toggle shows it as a star in the
  line's colour.
* **Segment and midpoint.** The segment tool draws a shortest path between two
  points. Their line also contains a second arc between them. Each arc has a
  midpoint, and the two midpoints are π/2 apart. *Midpoint* chooses the midpoint
  of the shortest arc and updates it when either endpoint moves. At distance
  π/2, both arcs are equally short, so the choice can switch as an endpoint
  moves. Deleting an endpoint also deletes the derived midpoint.
* **Angle bisectors.** Two distinct lines with unit normals `m` and `n` have
  two bisectors, with normals proportional to `m + n` and `m − n`. The
  bisectors are perpendicular and pass through the original intersection.
  *Bisect angle* creates both and updates them when their parent lines move.
* **Duality.** The polar of a point `P` is the line of points at distance π/2
  from `P`. Taking a pole and taking a polar undo each other. *Polar / Pole*
  creates a polar from a point or a pole from a line. This correspondence
  takes collinear points to concurrent lines.
* **Perpendicular.** The perpendicular from `P` to a line `ℓ` joins `P` to
  the pole of `ℓ`. It is unique unless `P` is the pole, in which case every
  line through `P` is perpendicular to `ℓ`. The bold segment ends at the foot,
  marked by a small square. For unit vectors `p` and `n`, its length is
  `arcsin(|p·n|)`, or π/2 minus the distance to the pole. Perpendiculars can
  be used as lines in further constructions.
* **Angle marks.** Right-angle squares and triangle angle arcs are constructed
  on the sphere and projected. Orthogonal projection distorts angles; the
  conformal view preserves them. Marks near the rim are omitted when they
  would cross the boundary.
* **Distance.** For unit vectors `p` and `q`, `d = arccos(|p·q|)`, so distances
  lie between 0 and π/2. A shortest segment that crosses the hemisphere's
  equator appears as two pieces, joined at opposite points of the disk rim.
* **Triangle.** The sides are shortest segments. For a nondegenerate triangle
  that bounds a disk, the angles sum to more than π, and Girard's formula gives
  `area = α + β + γ − π`. Small triangles approach Euclidean geometry.
  Some triples of points have shortest sides that form a loop which does not
  bound a disk. Away from the case of sides of length π/2, this happens when
  `(a·b)(b·c)(c·a) < 0`: the lifted loop ends at `−a` instead of `a`. The program
  reports that no disk is bounded and omits the area.
* **Circle.** A circle contains the points at a fixed elliptic distance from
  its centre. Select the centre and a point on the circle; moving either
  updates it. On the sphere it is represented by antipodal plane sections.
  Its visible pieces are ellipse arcs in the orthogonal view and circular
  arcs in the conformal view, with degenerate cases possible. Its elliptic
  centre generally differs from the centre of its projected curve. A circle
  crossing the equator appears in two pieces joined at opposite rim points.
  At radius π/2 it is exactly the polar line of its centre.

For a triangle that bounds a disk, intersect two interior angle bisectors to
construct the incentre, then drop a perpendicular to a side. A circle about the
incentre through that foot is the incircle. The three altitudes meet at the
orthocentre, which can be constructed with *Perpendicular* and *Meet*.

## 5. Project layout

| path | contents |
| --- | --- |
| [main.py](main.py) | starts the window or exports from the command line |
| [requirements.txt](requirements.txt) | the two packages the program needs |
| [elliptic/geometry.py](elliptic/geometry.py) | the maths: lifting, lines, segments, circles, distance, duality, angles and area |
| [elliptic/model.py](elliptic/model.py) | construction objects and their dependencies |
| [elliptic/scene.py](elliptic/scene.py) | shared drawing data in sphere coordinates |
| [elliptic/viewer.py](elliptic/viewer.py) | tool actions and interaction logic |
| [elliptic/ui/](elliptic/ui/) | the PySide6 window, disk and 3D sphere panes, and image rendering |
| [elliptic/sphere.py](elliptic/sphere.py) | shared sphere camera and visibility geometry |
| [elliptic/gclc.py](elliptic/gclc.py) | the GCLC exporter |
| [elliptic/tikz.py](elliptic/tikz.py) | the TikZ exporter for the disk |
| [elliptic/tikz_sphere.py](elliptic/tikz_sphere.py) | the TikZ exporter for the 3D sphere view |
| [tests/](tests/) | checks for geometry, constructions, exports, tools and the window; run with `python -m tests` |
| [docs/](docs/) | mathematical explanations and proofs in LaTeX and PDF; rebuild with `make -C docs` |

Derived objects keep references to the objects they depend on and recalculate
when needed. Moving a point updates the construction; deleting an object also
removes anything that depends on it.
