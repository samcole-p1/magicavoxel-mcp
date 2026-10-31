# MagicaVoxel MCP Server

An MCP (Model Context Protocol) server for creating and editing MagicaVoxel `.vox` files. Claude Code calls its tools to place voxels, generate shapes, transform regions and render snapshots.

## Requirements

- Python 3.10 or newer (the `mcp` SDK requires it)
- `mcp` 1.x — the server uses the low-level `Server` decorator API, which was removed in `mcp` 2.x
- Pillow, optional, for `take_snapshot` PNG renders

## Installation

Create a virtual environment in the repo folder and install the dependencies:

```bash
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Any Python 3.10+ works; use its full path in place of `py -3.12` if the launcher doesn't list it.

## Claude Code setup

### In this repo (project scope)

`.mcp.json` at the repo root registers the server for any Claude Code session opened in this folder. Claude Code asks you to approve it the first time. It launches `.venv/Scripts/python.exe server.py`; set `MAGICAVOXEL_PYTHON` to use a different interpreter (on macOS or Linux, `.venv/bin/python`).

### From other projects (user scope)

To use the tools from any project, register the server once for your user, with absolute paths:

```bash
claude mcp add --transport stdio -s user -e VOX_DIR=C:\path\to\MagicaVoxel\vox -e EXPORT_DIR=C:\path\to\MagicaVoxel\export magicavoxel -- E:\magicavoxel-mcp\.venv\Scripts\python.exe E:\magicavoxel-mcp\server.py
```

Check it with `claude mcp list`, or `/mcp` inside a session.

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `VOX_DIR` | `vox/` next to `server.py` | Where models are read and written |
| `EXPORT_DIR` | `export/` next to `server.py` | Where `take_snapshot` writes renders |
| `MAGICAVOXEL_PYTHON` | `.venv/Scripts/python.exe` | Interpreter used by `.mcp.json` |

Point `VOX_DIR` at MagicaVoxel's own `vox/` folder to open the results straight from the editor.

## Tools

There are 40 tools. Models are named without the `.vox` extension and live in `VOX_DIR`. The server also sends Claude short instructions covering axes, colours and naming.

**Models:** `create_voxel_model`, `read_voxel_model`, `get_model_info`, `list_models`, `copy_model`, `delete_model`, `take_snapshot`

**Voxels and regions:** `place_voxel`, `remove_voxel`, `get_voxel`, `fill_box`, `clear_region`, `copy_region`, `rotate_region`, `mirror_region`, `extrude_region`

**Shapes:** `create_sphere`, `create_cylinder`, `create_pyramid`, `create_torus`, `create_cone`

**Booleans:** `union_models`, `subtract_region`, `intersect_region`

**Morphology and resizing:** `dilate`, `erode`, `shell`, `invert`, `flood_fill`, `shrink`, `scale_model`, `repeat_pattern`

**Colour:** `get_palette`, `set_palette_color`, `replace_color`, `randomize_colors`, `apply_noise`, `optimize_palette`

**Analysis:** `find_connected_components`, `get_surface_voxels`

## Notes

- **Axes match MagicaVoxel:** X is width, Y is depth, **Z is up**. Shapes rise along +Z by default.
- Coordinates are 0–255 on each axis. Voxels that land outside the grid are dropped, and the tool result says so.
- Colour index 0 is empty; 1–255 are palette colours.
- Each edit reads the file, changes it and writes it back immediately. Writes go to a temporary file that then replaces the original, so a failed edit leaves the file as it was.
- Model names are bare names inside `VOX_DIR`: letters, digits, spaces, `_`, `-` and `.`, with no paths.
- One model or operation holds at most 4,194,304 voxels (for example 256×128×128).
- `create_voxel_model`, `copy_model` and `take_snapshot` refuse to replace an existing file unless you pass `overwrite: true`.
- `take_snapshot` writes a backup `.vox` and front, back, left, right, top and bottom PNGs into `EXPORT_DIR`, never into `VOX_DIR`. The PNGs are orthographic and shaded by depth, so holes and recesses show darker.
- Edit results report the voxel count before and after, and say when the model's size changed.
- New models use a simple default palette: 1 white, 2 red, 3 green, 4 blue, 5 yellow, 6 magenta, 7 cyan, then a grey ramp.

## Files saved by MagicaVoxel

The tools edit the first model in a file. Further models, the scene graph (transforms, groups, shapes), layers, materials and cameras are kept byte for byte.

- **Placement:** MagicaVoxel places a model by its centre. When an edit changes the first model's size, or `shrink` moves its voxels, the server moves the model's scene transform to match, so it stays where it was.
- **Animations:** in an animation file the first model is frame 0 only. Edits change that frame, and a size change can make it jump against the other frames; the tool result says so.
- **Palette:** all models in a file share one palette, so `optimize_palette` refuses files with several models. On single-model files it renumbers the materials along with the colours, so emissive and glass materials stay on the right voxels.
- A file without a palette chunk gets this server's default palette rather than MagicaVoxel's.

## Tests

```bash
.venv\Scripts\python -m unittest discover tests
```

`tests/test_vox_utils.py` covers the file format, geometry and rendering. `tests/test_server.py` starts the server over stdio and drives it with the MCP client.

## Troubleshooting

- **Server fails with `'Server' object has no attribute 'list_tools'`**: `mcp` 2.x is installed. Reinstall from `requirements.txt`.
- **`TypeError: 'type' object is not subscriptable`**: the interpreter is older than 3.10.
- **Models don't appear in MagicaVoxel**: check that `VOX_DIR` points at the editor's `vox/` folder.
