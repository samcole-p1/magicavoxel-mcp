# MagicaVoxel MCP Server

Python MCP server (stdio) that edits MagicaVoxel `.vox` files. See README.md for setup.

## Layout

- `server.py` declares the tool schemas in `list_tools()` and runs them in `handle_tool()` through one long `if/elif` chain. Adding a tool means updating both. `PARAM_LIMITS` adds 0–255 style bounds to schemas by parameter name; the SDK rejects calls outside them.
- `vox_utils.py` holds `VoxelModel` (voxels as a `{(x, y, z): color_index}` dict plus a 256-entry RGBA palette), `.vox` reading and writing, and the Pillow renderer. The proportion and validation helpers after `read_vox_file` aren't used by the server.
- `tests/` holds unittest suites; `vox/` holds the sample models; `export/` (gitignored) gets snapshot renders.

## Environment

- Python 3.10+ in `.venv` (`.venv\Scripts\python.exe`); the system `python` on this machine is 3.7 and can't run it.
- `mcp` is pinned below 2.0, because 2.x removed the low-level `Server.list_tools`/`call_tool` decorators.
- Never load pickle files from this repo or elsewhere.

## Conventions

- Z is up, as in MagicaVoxel: X is width, Y is depth. Shapes default to the Z axis; `create_voxel_model` maps width/depth/height to X/Y/Z.
- `model.palette[i]` is the colour of index i, and `palette[0]` is empty. In the file's RGBA chunk, entry i holds colour i + 1; the reader and writer convert between the two.
- Go through `set_voxel` to change voxels. It validates colours, drops positions off the 0–255 grid (recording that in `model.clipped`) and enforces `MAX_VOXELS`. Loops over boxes use `_span`/`_clamp_box` so they never iterate past the grid.
- `read_vox_file` keeps every chunk it doesn't edit as raw bytes in `model.layout`, and `write_vox_file` writes them back in order. Keep that round-trip lossless.
- MagicaVoxel places a model in its scene by its centre, `size // 2`. `_keep_scene_placement` shifts the nTRN transforms of model 0's shape when its size changes or its voxels move (`model.shift`). An edit that moves voxels should update `model.shift`.
- The palette is shared by every model in a file, and MATL chunks are keyed by palette index. Anything that renumbers colours must renumber MATL too, and must refuse multi-model files.
- `write_vox_file` validates first and replaces the file atomically. Don't write model files any other way.
- Tool handlers raise exceptions for errors; the SDK turns them into `isError` results. Return through `save()` after an edit so voxel counts, size changes, clipping and scene notes get reported. Tools that create files call `refuse_overwrite()`.
- Model names go through `model_name()`/`get_vox_path()`, which keep them inside `VOX_DIR`.

## Verifying changes

- Run `.venv\Scripts\python -m unittest discover tests`.
- To check geometry visually, run `take_snapshot` (or `render_model_all_angles`) and open the PNGs with the Read tool.
- Test edits on copies of the files in `vox/`, never on the user's real MagicaVoxel models.
