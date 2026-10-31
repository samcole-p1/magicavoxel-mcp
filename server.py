#!/usr/bin/env python3
"""
MagicaVoxel MCP Server - Minimal Version
Provides basic tools for creating and modifying MagicaVoxel .vox files
"""

import asyncio
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from vox_utils import VoxelModel, read_vox_file, write_vox_file, render_model_all_angles

INSTRUCTIONS = """\
Edits MagicaVoxel .vox models in the server's vox folder. Every edit is saved to the file immediately.
- Axes match MagicaVoxel: X is width, Y is depth, Z is up. Build upward along +Z.
- Coordinates run 0-255 on each axis; voxels placed outside that are dropped and reported.
- Colour index 0 means empty; 1-255 are palette colours.
- Filenames are bare names inside the vox folder, without paths.
- Only the first model of a multi-model file is editable; the rest of the file is preserved.
  In animation files that model is frame 0 only.
- Tools that create files (create_voxel_model, copy_model, take_snapshot) refuse to replace an
  existing file unless overwrite is true.
- Default palette for new models: 1 white, 2 red, 3 green, 4 blue, 5 yellow, 6 magenta, 7 cyan,
  8-255 a grey ramp (index i is grey level i). Use set_palette_color for your own colours.
- To check a result visually, call take_snapshot and look at the PNG renders it lists. They are
  orthographic views shaded by depth (farther surfaces are darker), so holes show as dark areas."""

# Initialize MCP server
app = Server("magicavoxel-mcp", instructions=INSTRUCTIONS)

# Default paths, resolved from this file so the launch cwd doesn't matter
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_VOX_DIR = Path(os.getenv("VOX_DIR") or BASE_DIR / "vox")
DEFAULT_VOX_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_EXPORT_DIR = Path(os.getenv("EXPORT_DIR") or BASE_DIR / "export")
DEFAULT_EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def model_name(filename: str) -> str:
    """Validate a model name and strip any .vox extension. Names are confined to the vox
    folder: no separators, drive letters, colons (NTFS streams) or leading dots."""
    name = filename[:-4] if filename.lower().endswith('.vox') else filename
    if not re.fullmatch(r"[A-Za-z0-9_\- ][A-Za-z0-9_\-. ]*", name) or ".." in name:
        raise ValueError(f"Invalid model name {filename!r}: use letters, digits, spaces, '_', '-' and '.' only")
    return name


def get_vox_path(filename: str) -> Path:
    """Get full path to a .vox file inside the vox folder"""
    path = (DEFAULT_VOX_DIR / f"{model_name(filename)}.vox").resolve()
    if path.parent != DEFAULT_VOX_DIR.resolve():
        raise ValueError(f"Invalid model name {filename!r}")
    return path


def save(filepath: Path, model: VoxelModel, message: str) -> list[TextContent]:
    """Write the model and report the result: voxel count, size changes, voxels dropped off
    the grid, and anything that may look different in a MagicaVoxel scene"""
    note = write_vox_file(filepath, model)
    count = model.get_voxel_count()
    if model.loaded_size is None:
        message += f"\nVoxels: {count}"
    else:
        message += f"\nVoxels: {model.loaded_count} -> {count}"
        size = model.file_size()
        if size != model.loaded_size:
            message += f"\nModel size (X x Y x Z) changed from {fmt_size(model.loaded_size)} to {fmt_size(size)}"
    if model.clipped:
        message += "\nWarning: part of this edit fell outside the 0-255 grid and was dropped"
    if note:
        message += f"\nNote: {note}"
    return [TextContent(type="text", text=message)]


def fmt_size(size) -> str:
    return "x".join(str(n) for n in size)


def refuse_overwrite(path: Path, arguments: dict[str, Any]):
    """Stop a tool from silently replacing an existing file"""
    if path.exists() and not arguments.get("overwrite", False):
        raise FileExistsError(f"'{path.name}' already exists; pass overwrite=true to replace it")


def describe_model(filename: str, filepath: Path) -> str:
    """Size, extent and contents of a model file, for read_voxel_model and get_model_info"""
    model = read_vox_file(filepath)
    text = (f"Model '{filename}':\n  Size (X x Y x Z, as MagicaVoxel shows it): {fmt_size(model.file_size())}"
            f"\n  Voxel count: {model.get_voxel_count()}, colours used: {len(set(model.voxels.values()))}")
    if model.voxels:
        lo, hi = model.get_extent()
        text += f"\n  Voxels occupy {lo} to {hi}"
    if model.model_count > 1:
        text += f"\n  File holds {model.model_count} models; the tools edit only the first and keep the rest"
    chunks = {}
    for item in model.layout:
        if isinstance(item, bytes) and item[:4] not in (b'SIZE', b'XYZI'):
            chunk_id = item[:4].decode('latin-1')
            chunks[chunk_id] = chunks.get(chunk_id, 0) + 1
    if chunks:
        text += "\n  Other chunks, kept as they are: " + ", ".join(f"{k} x{n}" for k, n in chunks.items())
    return text


# Numeric limits added to every tool schema by parameter name; limits written in a schema win.
# They keep each call inside the 256-voxel grid, which also bounds how long a call can run.
PARAM_LIMITS = {
    **{key: (0, 255) for key in (
        "x", "y", "z", "x1", "y1", "z1", "x2", "y2", "z2",
        "center_x", "center_y", "center_z", "base_x", "base_y", "base_z",
        "target_x", "target_y", "target_z", "color_index", "old_color", "new_color",
        "r", "g", "b", "a", "radius", "base_radius", "major_radius", "minor_radius")},
    **{key: (-255, 255) for key in ("offset_x", "offset_y", "offset_z")},
    **{key: (1, 256) for key in (
        "width", "height", "depth", "base_width", "base_depth", "count_x", "count_y", "count_z")},
    **{key: (0.01, 256) for key in ("factor", "factor_x", "factor_y", "factor_z")},
    "distance": (1, 255),
    "iterations": (1, 64),
    "min_index": (1, 255),
    "max_index": (1, 255),
}


def with_limits(tools: list[Tool]) -> list[Tool]:
    """Add PARAM_LIMITS to the tools' input schemas; the SDK rejects calls outside them"""
    for tool in tools:
        for key, prop in tool.inputSchema.get("properties", {}).items():
            if key in PARAM_LIMITS:
                prop.setdefault("minimum", PARAM_LIMITS[key][0])
                prop.setdefault("maximum", PARAM_LIMITS[key][1])
    return tools


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools"""
    return with_limits([
        Tool(
            name="create_voxel_model",
            description="Create a new empty voxel model with specified dimensions. Refuses to replace an existing model unless overwrite is true.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file (without .vox extension)"},
                    "width": {"type": "integer", "description": "Width (X dimension)", "default": 10},
                    "height": {"type": "integer", "description": "Height (Z dimension, up)", "default": 10},
                    "depth": {"type": "integer", "description": "Depth (Y dimension)", "default": 10},
                    "overwrite": {"type": "boolean", "description": "Replace the target if it already exists (default: refuse)", "default": False}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="read_voxel_model",
            description="Inspect a .vox file: model size, occupied extent, voxel and colour counts, and what else the file holds (other models, layers, materials, scene)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file (without .vox extension)"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="place_voxel",
            description="Place a voxel at a specific coordinate in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "z": {"type": "integer", "description": "Z coordinate"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1}
                },
                "required": ["filename", "x", "y", "z"]
            }
        ),
        Tool(
            name="remove_voxel",
            description="Remove a voxel at specific coordinates in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "z": {"type": "integer", "description": "Z coordinate"}
                },
                "required": ["filename", "x", "y", "z"]
            }
        ),
        Tool(
            name="fill_box",
            description="Fill a rectangular region with voxels",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate"},
                    "y1": {"type": "integer", "description": "Start Y coordinate"},
                    "z1": {"type": "integer", "description": "Start Z coordinate"},
                    "x2": {"type": "integer", "description": "End X coordinate"},
                    "y2": {"type": "integer", "description": "End Y coordinate"},
                    "z2": {"type": "integer", "description": "End Z coordinate"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2"]
            }
        ),
        Tool(
            name="clear_region",
            description="Remove all voxels in a rectangular region",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate"},
                    "y1": {"type": "integer", "description": "Start Y coordinate"},
                    "z1": {"type": "integer", "description": "Start Z coordinate"},
                    "x2": {"type": "integer", "description": "End X coordinate"},
                    "y2": {"type": "integer", "description": "End Y coordinate"},
                    "z2": {"type": "integer", "description": "End Z coordinate"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2"]
            }
        ),
        Tool(
            name="create_sphere",
            description="Create a sphere in a model at specified center with given radius",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "center_x": {"type": "integer", "description": "X coordinate of sphere center"},
                    "center_y": {"type": "integer", "description": "Y coordinate of sphere center"},
                    "center_z": {"type": "integer", "description": "Z coordinate of sphere center"},
                    "radius": {"type": "integer", "description": "Radius of the sphere"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create hollow sphere (surface only)", "default": False}
                },
                "required": ["filename", "center_x", "center_y", "center_z", "radius"]
            }
        ),
        Tool(
            name="create_cylinder",
            description="Create a cylinder in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "center_x": {"type": "integer", "description": "X coordinate of cylinder base center"},
                    "center_y": {"type": "integer", "description": "Y coordinate of cylinder base center"},
                    "center_z": {"type": "integer", "description": "Z coordinate of cylinder base center (bottom for the default Z axis)"},
                    "radius": {"type": "integer", "description": "Radius of the cylinder"},
                    "height": {"type": "integer", "description": "Height of the cylinder"},
                    "axis": {"type": "string", "enum": ["x", "y", "z"], "description": "Axis the cylinder rises along (z is up)", "default": "z"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create a closed hollow shell", "default": False}
                },
                "required": ["filename", "center_x", "center_y", "center_z", "radius", "height"]
            }
        ),
        Tool(
            name="create_pyramid",
            description="Create a pyramid in a model, rising along +Z from its base",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "base_x": {"type": "integer", "description": "X coordinate of pyramid base corner"},
                    "base_y": {"type": "integer", "description": "Y coordinate of pyramid base corner"},
                    "base_z": {"type": "integer", "description": "Z coordinate of pyramid base (bottom)"},
                    "base_width": {"type": "integer", "description": "Width of pyramid base (along X)"},
                    "base_depth": {"type": "integer", "description": "Depth of pyramid base (along Y)"},
                    "height": {"type": "integer", "description": "Height of the pyramid"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create hollow pyramid", "default": False}
                },
                "required": ["filename", "base_x", "base_y", "base_z", "base_width", "base_depth", "height"]
            }
        ),
        Tool(
            name="create_torus",
            description="Create a torus (donut) shape in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "center_x": {"type": "integer", "description": "X coordinate of center"},
                    "center_y": {"type": "integer", "description": "Y coordinate of center"},
                    "center_z": {"type": "integer", "description": "Z coordinate of center"},
                    "major_radius": {"type": "integer", "description": "Distance from center to tube center"},
                    "minor_radius": {"type": "integer", "description": "Radius of the tube"},
                    "axis": {"type": "string", "enum": ["x", "y", "z"], "description": "Axis through the hole; the default z lays the ring flat", "default": "z"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create hollow torus", "default": False}
                },
                "required": ["filename", "center_x", "center_y", "center_z", "major_radius", "minor_radius"]
            }
        ),
        Tool(
            name="create_cone",
            description="Create a cone shape in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "base_x": {"type": "integer", "description": "X coordinate of base center"},
                    "base_y": {"type": "integer", "description": "Y coordinate of base center"},
                    "base_z": {"type": "integer", "description": "Z coordinate of base (bottom for the default Z axis)"},
                    "base_radius": {"type": "integer", "description": "Radius of base"},
                    "height": {"type": "integer", "description": "Height of cone"},
                    "axis": {"type": "string", "enum": ["x", "y", "z"], "description": "Axis the cone rises along (z is up)", "default": "z"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create hollow cone", "default": False}
                },
                "required": ["filename", "base_x", "base_y", "base_z", "base_radius", "height"]
            }
        ),
        Tool(
            name="set_palette_color",
            description="Set a specific color in the model's palette",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "color_index": {"type": "integer", "description": "Palette index to set (1-255)", "minimum": 1},
                    "r": {"type": "integer", "description": "Red component (0-255)"},
                    "g": {"type": "integer", "description": "Green component (0-255)"},
                    "b": {"type": "integer", "description": "Blue component (0-255)"},
                    "a": {"type": "integer", "description": "Alpha component (0-255)", "default": 255}
                },
                "required": ["filename", "color_index", "r", "g", "b"]
            }
        ),
        Tool(
            name="replace_color",
            description="Replace all voxels of one color with another color in a model; reports how many changed",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "old_color": {"type": "integer", "description": "Color index to replace (0-255)"},
                    "new_color": {"type": "integer", "description": "New color index (0-255; 0 removes the voxels)"}
                },
                "required": ["filename", "old_color", "new_color"]
            }
        ),
        Tool(
            name="get_voxel",
            description="Get the color index of a voxel at specific coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "z": {"type": "integer", "description": "Z coordinate"}
                },
                "required": ["filename", "x", "y", "z"]
            }
        ),
        Tool(
            name="get_palette",
            description="List the RGBA colour of every palette index the model uses, plus indices 1-8 for reference",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="get_model_info",
            description="Get a model's size (as MagicaVoxel shows it, X x Y x Z), the extent its voxels occupy, and its voxel count",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="delete_model",
            description="Delete a .vox file from the vox directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="copy_model",
            description="Copy a .vox file to a new filename. Refuses to replace an existing model unless overwrite is true.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_filename": {"type": "string", "description": "Source .vox file name"},
                    "target_filename": {"type": "string", "description": "Target .vox file name"},
                    "overwrite": {"type": "boolean", "description": "Replace the target if it already exists (default: refuse)", "default": False}
                },
                "required": ["source_filename", "target_filename"]
            }
        ),
        Tool(
            name="take_snapshot",
            description="Snapshot a model into the export folder: a backup .vox copy plus depth-shaded PNG views from 6 sides (front from -Y, back, left from -X, right, top from +Z, bottom). The vox folder is not touched.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file to snapshot"},
                    "snapshot_name": {"type": "string", "description": "Optional name for the snapshot (without .vox). If not provided, uses timestamp"},
                    "overwrite": {"type": "boolean", "description": "Replace the target if it already exists (default: refuse)", "default": False}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="rotate_region",
            description="Rotate a region of voxels around a center point. The region is moved: its original voxels are cleared. Rotation follows the right-hand rule, e.g. 90 degrees about z turns +X toward +Y.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate of region"},
                    "y1": {"type": "integer", "description": "Start Y coordinate of region"},
                    "z1": {"type": "integer", "description": "Start Z coordinate of region"},
                    "x2": {"type": "integer", "description": "End X coordinate of region"},
                    "y2": {"type": "integer", "description": "End Y coordinate of region"},
                    "z2": {"type": "integer", "description": "End Z coordinate of region"},
                    "center_x": {"type": "integer", "description": "X coordinate of rotation center"},
                    "center_y": {"type": "integer", "description": "Y coordinate of rotation center"},
                    "center_z": {"type": "integer", "description": "Z coordinate of rotation center"},
                    "axis": {"type": "string", "enum": ["x", "y", "z"], "description": "Rotation axis"},
                    "degrees": {"type": "integer", "enum": [90, 180, 270], "description": "Rotation angle"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "center_x", "center_y", "center_z", "axis", "degrees"]
            }
        ),
        Tool(
            name="mirror_region",
            description="Add a mirrored copy of a region on the other side of a plane. The original voxels stay; overlapping voxels take the copy's colour.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate of region"},
                    "y1": {"type": "integer", "description": "Start Y coordinate of region"},
                    "z1": {"type": "integer", "description": "Start Z coordinate of region"},
                    "x2": {"type": "integer", "description": "End X coordinate of region"},
                    "y2": {"type": "integer", "description": "End Y coordinate of region"},
                    "z2": {"type": "integer", "description": "End Z coordinate of region"},
                    "plane": {"type": "string", "enum": ["x", "y", "z"], "description": "Axis the mirror plane is perpendicular to"},
                    "position": {"type": "number", "description": "Position of the mirror plane along the axis; use a .5 value (e.g. 4.5) to mirror between two voxel layers", "minimum": 0, "maximum": 255}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "plane", "position"]
            }
        ),
        Tool(
            name="copy_region",
            description="Copy a region of voxels to a new location; the copy overwrites voxels already there",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate of source region"},
                    "y1": {"type": "integer", "description": "Start Y coordinate of source region"},
                    "z1": {"type": "integer", "description": "Start Z coordinate of source region"},
                    "x2": {"type": "integer", "description": "End X coordinate of source region"},
                    "y2": {"type": "integer", "description": "End Y coordinate of source region"},
                    "z2": {"type": "integer", "description": "End Z coordinate of source region"},
                    "target_x": {"type": "integer", "description": "Target X of the copy's minimum corner (lowest x, y, z)"},
                    "target_y": {"type": "integer", "description": "Target Y of the copy's minimum corner"},
                    "target_z": {"type": "integer", "description": "Target Z of the copy's minimum corner"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "target_x", "target_y", "target_z"]
            }
        ),
        Tool(
            name="extrude_region",
            description="Extrude a region: repeat its voxels step by step in a direction for the given distance, overwriting any voxels in the way",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate of region"},
                    "y1": {"type": "integer", "description": "Start Y coordinate of region"},
                    "z1": {"type": "integer", "description": "Start Z coordinate of region"},
                    "x2": {"type": "integer", "description": "End X coordinate of region"},
                    "y2": {"type": "integer", "description": "End Y coordinate of region"},
                    "z2": {"type": "integer", "description": "End Z coordinate of region"},
                    "direction": {"type": "string", "enum": ["x+", "x-", "y+", "y-", "z+", "z-"], "description": "Extrusion direction"},
                    "distance": {"type": "integer", "description": "Distance to extrude"},
                    "color_index": {"type": "integer", "description": "Optional color override (uses original colors if not specified)"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "direction", "distance"]
            }
        ),
        Tool(
            name="find_connected_components",
            description="Find all disconnected parts in a model (useful for detecting floating pieces)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="get_surface_voxels",
            description="Get all surface (exposed) voxels in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="subtract_region",
            description="Remove all voxels in a region (boolean subtract operation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate"},
                    "y1": {"type": "integer", "description": "Start Y coordinate"},
                    "z1": {"type": "integer", "description": "Start Z coordinate"},
                    "x2": {"type": "integer", "description": "End X coordinate"},
                    "y2": {"type": "integer", "description": "End Y coordinate"},
                    "z2": {"type": "integer", "description": "End Z coordinate"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2"]
            }
        ),
        Tool(
            name="union_models",
            description="Combine two models together (boolean union operation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "target_filename": {"type": "string", "description": "Target model to modify"},
                    "source_filename": {"type": "string", "description": "Source model to add"},
                    "offset_x": {"type": "integer", "description": "X offset for source model", "default": 0},
                    "offset_y": {"type": "integer", "description": "Y offset for source model", "default": 0},
                    "offset_z": {"type": "integer", "description": "Z offset for source model", "default": 0}
                },
                "required": ["target_filename", "source_filename"]
            }
        ),
        Tool(
            name="intersect_region",
            description="Keep only voxels within a region (boolean intersect operation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "x1": {"type": "integer", "description": "Start X coordinate"},
                    "y1": {"type": "integer", "description": "Start Y coordinate"},
                    "z1": {"type": "integer", "description": "Start Z coordinate"},
                    "x2": {"type": "integer", "description": "End X coordinate"},
                    "y2": {"type": "integer", "description": "End Y coordinate"},
                    "z2": {"type": "integer", "description": "End Z coordinate"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2"]
            }
        ),
        Tool(
            name="scale_model",
            description="Scale the model uniformly or per-axis, about the origin; each voxel becomes the block it covers, so scaling up leaves no gaps",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "factor": {"type": "number", "description": "Uniform scale factor", "default": 2.0},
                    "factor_x": {"type": "number", "description": "X-axis scale factor (overrides factor if set)"},
                    "factor_y": {"type": "number", "description": "Y-axis scale factor (overrides factor if set)"},
                    "factor_z": {"type": "number", "description": "Z-axis scale factor (overrides factor if set)"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="dilate",
            description="Dilate: grow the model by one voxel layer per iteration; new voxels take the colour of the voxel they grow from",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "iterations": {"type": "integer", "description": "Number of dilation iterations", "default": 1}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="erode",
            description="Erode: remove surface voxels (shrinks model, refines shape)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "iterations": {"type": "integer", "description": "Number of erosion iterations", "default": 1}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="flood_fill",
            description="Fill all fully enclosed hollow spaces with a color",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "color_index": {"type": "integer", "description": "Color index to fill with (1-255)", "minimum": 1, "default": 1}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="shell",
            description="Remove all interior voxels, keep only surface (hull operation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="invert",
            description="Invert: swap solid and empty space within the occupied bounding box (new voxels use color 1)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="shrink",
            description="Shrink the model to fit its voxels: move them to the origin and trim the empty space on every side. In a MagicaVoxel scene the model keeps its place.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="repeat_pattern",
            description="Repeat/tile the model pattern across axes (create patterns)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "count_x": {"type": "integer", "description": "Repeat count on X axis", "default": 2},
                    "count_y": {"type": "integer", "description": "Repeat count on Y axis", "default": 1},
                    "count_z": {"type": "integer", "description": "Repeat count on Z axis", "default": 1},
                    "mirror": {"type": "boolean", "description": "Mirror on odd repetitions", "default": False}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="apply_noise",
            description="Add colour variation: each voxel draws a random value between min_val and max_val, and where it is above 0.5 the voxel's colour index rises by (value - 0.5) * 10, up to 5. Works best with a palette whose neighbouring indices are similar shades.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "seed": {"type": "integer", "description": "Random seed for noise", "default": 0},
                    "min_val": {"type": "number", "description": "Lowest random value (raise it to change more voxels)", "default": 0.0, "minimum": 0, "maximum": 1},
                    "max_val": {"type": "number", "description": "Highest random value (at most 1.0, a shift of 5 indices)", "default": 1.0, "minimum": 0, "maximum": 1}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="randomize_colors",
            description="Randomize voxel colors within palette range",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "min_index": {"type": "integer", "description": "Minimum color index", "default": 1},
                    "max_index": {"type": "integer", "description": "Maximum color index", "default": 255}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="optimize_palette",
            description="Renumber the colours the model uses to indices 1..N, moving unused palette entries after them; voxels, palette and materials move together so nothing changes appearance. Refused for files holding several models, which share one palette.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="list_models",
            description="List all .vox files in the vox directory",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ])


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls. Errors are raised, and the SDK returns them as isError results."""
    # The voxel work is synchronous; keep it off the event loop
    return await asyncio.to_thread(handle_tool, name, arguments)


def handle_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Run one tool call"""
    if name == "create_voxel_model":
        filename = arguments["filename"]
        width = arguments.get("width", 10)
        height = arguments.get("height", 10)
        depth = arguments.get("depth", 10)
        
        filepath = get_vox_path(filename)
        refuse_overwrite(filepath, arguments)
        # Z is up: width runs along X, depth along Y, height along Z
        model = VoxelModel(width, depth, height)
        return save(filepath, model, f"Created model '{filename}' with size {width}x{depth}x{height} (X x Y x Z)")

    elif name in ("read_voxel_model", "get_model_info"):
        filename = arguments["filename"]
        filepath = get_vox_path(filename)

        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")

        return [TextContent(type="text", text=describe_model(filename, filepath))]
    
    elif name == "place_voxel":
        filename = arguments["filename"]
        x = arguments["x"]
        y = arguments["y"]
        z = arguments["z"]
        color_index = arguments.get("color_index", 1)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.set_voxel(x, y, z, color_index)
        return save(filepath, model, f"Placed voxel at ({x}, {y}, {z}) with color {color_index}")
    
    elif name == "remove_voxel":
        filename = arguments["filename"]
        x = arguments["x"]
        y = arguments["y"]
        z = arguments["z"]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.remove_voxel(x, y, z)
        return save(filepath, model, f"Removed voxel at ({x}, {y}, {z})")
    
    elif name == "fill_box":
        filename = arguments["filename"]
        x1 = arguments["x1"]
        y1 = arguments["y1"]
        z1 = arguments["z1"]
        x2 = arguments["x2"]
        y2 = arguments["y2"]
        z2 = arguments["z2"]
        color_index = arguments.get("color_index", 1)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.fill_box(x1, y1, z1, x2, y2, z2, color_index)
        return save(filepath, model, f"Filled box from ({x1}, {y1}, {z1}) to ({x2}, {y2}, {z2})")
    
    elif name == "clear_region":
        filename = arguments["filename"]
        x1 = arguments["x1"]
        y1 = arguments["y1"]
        z1 = arguments["z1"]
        x2 = arguments["x2"]
        y2 = arguments["y2"]
        z2 = arguments["z2"]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.clear_region(x1, y1, z1, x2, y2, z2)
        return save(filepath, model, f"Cleared region from ({x1}, {y1}, {z1}) to ({x2}, {y2}, {z2})")
    
    elif name == "create_sphere":
        filename = arguments["filename"]
        center_x = arguments["center_x"]
        center_y = arguments["center_y"]
        center_z = arguments["center_z"]
        radius = arguments["radius"]
        color_index = arguments.get("color_index", 1)
        hollow = arguments.get("hollow", False)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            model = VoxelModel(1, 1, 1)
            write_vox_file(filepath, model)
        
        model = read_vox_file(filepath)
        model.create_sphere(center_x, center_y, center_z, radius, color_index, hollow)
        return save(filepath, model, f"Created sphere at ({center_x}, {center_y}, {center_z}) with radius {radius}")
    
    elif name == "create_cylinder":
        filename = arguments["filename"]
        center_x = arguments["center_x"]
        center_y = arguments["center_y"]
        center_z = arguments["center_z"]
        radius = arguments["radius"]
        height = arguments["height"]
        axis = arguments.get("axis", "z")
        color_index = arguments.get("color_index", 1)
        hollow = arguments.get("hollow", False)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            model = VoxelModel(1, 1, 1)
            write_vox_file(filepath, model)
        
        model = read_vox_file(filepath)
        model.create_cylinder(center_x, center_y, center_z, radius, height, axis, color_index, hollow)
        return save(filepath, model, f"Created cylinder at ({center_x}, {center_y}, {center_z}) with radius {radius} and height {height}")
    
    elif name == "create_pyramid":
        filename = arguments["filename"]
        base_x = arguments["base_x"]
        base_y = arguments["base_y"]
        base_z = arguments["base_z"]
        base_width = arguments["base_width"]
        base_depth = arguments["base_depth"]
        height = arguments["height"]
        color_index = arguments.get("color_index", 1)
        hollow = arguments.get("hollow", False)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            model = VoxelModel(1, 1, 1)
            write_vox_file(filepath, model)
        
        model = read_vox_file(filepath)
        model.create_pyramid(base_x, base_y, base_z, base_width, base_depth, height, color_index, hollow)
        return save(filepath, model, f"Created pyramid at ({base_x}, {base_y}, {base_z})")
    
    elif name == "create_torus":
        filename = arguments["filename"]
        center_x = arguments["center_x"]
        center_y = arguments["center_y"]
        center_z = arguments["center_z"]
        major_radius = arguments["major_radius"]
        minor_radius = arguments["minor_radius"]
        axis = arguments.get("axis", "z")
        color_index = arguments.get("color_index", 1)
        hollow = arguments.get("hollow", False)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            model = VoxelModel(1, 1, 1)
            write_vox_file(filepath, model)
        
        model = read_vox_file(filepath)
        model.create_torus(center_x, center_y, center_z, major_radius, minor_radius, axis, color_index, hollow)
        return save(filepath, model, f"Created torus at ({center_x}, {center_y}, {center_z})")
    
    elif name == "create_cone":
        filename = arguments["filename"]
        base_x = arguments["base_x"]
        base_y = arguments["base_y"]
        base_z = arguments["base_z"]
        base_radius = arguments["base_radius"]
        height = arguments["height"]
        axis = arguments.get("axis", "z")
        color_index = arguments.get("color_index", 1)
        hollow = arguments.get("hollow", False)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            model = VoxelModel(1, 1, 1)
            write_vox_file(filepath, model)
        
        model = read_vox_file(filepath)
        model.create_cone(base_x, base_y, base_z, base_radius, height, axis, color_index, hollow)
        return save(filepath, model, f"Created cone at ({base_x}, {base_y}, {base_z})")
    
    elif name == "set_palette_color":
        filename = arguments["filename"]
        color_index = arguments["color_index"]
        r = arguments["r"]
        g = arguments["g"]
        b = arguments["b"]
        a = arguments.get("a", 255)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.set_palette_color(color_index, r, g, b, a)
        return save(filepath, model, f"Set palette color {color_index} to RGBA({r}, {g}, {b}, {a})")
    
    elif name == "replace_color":
        filename = arguments["filename"]
        old_color = arguments["old_color"]
        new_color = arguments["new_color"]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        replaced = model.replace_color(old_color, new_color)
        return save(filepath, model, f"Replaced color {old_color} with {new_color} on {replaced} voxel(s)")
    
    elif name == "get_voxel":
        filename = arguments["filename"]
        x = arguments["x"]
        y = arguments["y"]
        z = arguments["z"]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        color = model.get_voxel(x, y, z)
        
        return [TextContent(type="text", text=f"Voxel at ({x}, {y}, {z}) has color index {color}")]
    
    elif name == "get_palette":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        # List the colours the model uses, then the first entries for reference
        used = sorted(set(model.voxels.values()))
        shown = used + [i for i in range(1, 9) if i not in used]
        palette_info = [f"  {i}: RGBA{model.palette[i]}" + (" (used)" if i in used else "") for i in shown]

        return [TextContent(type="text", text=f"Palette for '{filename}':\n" + "\n".join(palette_info))]
    
    elif name == "delete_model":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        filepath.unlink()
        return [TextContent(type="text", text=f"Deleted model '{filename}'")]
    
    elif name == "copy_model":
        source_filename = arguments["source_filename"]
        target_filename = arguments["target_filename"]
        
        source_path = get_vox_path(source_filename)
        target_path = get_vox_path(target_filename)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source file '{source_filename}' not found")
        refuse_overwrite(target_path, arguments)

        shutil.copyfile(source_path, target_path)
        return [TextContent(type="text", text=f"Copied '{source_filename}' to '{target_filename}'")]
    
    elif name == "take_snapshot":
        filename = arguments["filename"]
        snapshot_name = arguments.get("snapshot_name")
        
        source_path = get_vox_path(filename)
        if not source_path.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        # Generate snapshot name if not provided
        if snapshot_name:
            snapshot_name = model_name(snapshot_name)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_name = f"{model_name(filename)}_snapshot_{timestamp}"

        # Snapshots live in the export folder, so they don't clutter MagicaVoxel's project list
        target_path = DEFAULT_EXPORT_DIR / f"{snapshot_name}.vox"
        refuse_overwrite(target_path, arguments)

        model = read_vox_file(source_path)
        shutil.copyfile(source_path, target_path)

        # Render images from all 6 angles
        image_base_path = DEFAULT_EXPORT_DIR / snapshot_name
        image_results = render_model_all_angles(model, image_base_path)

        result_text = f"Snapshot saved as {target_path}"
        if image_results:
            result_text += f"\nImages saved from {len(image_results)} angles:"
            for angle, img_path in image_results.items():
                result_text += f"\n  - {angle}: {img_path}"
        else:
            result_text += "\nNote: Image rendering requires Pillow (pip install Pillow)"
        
        return [TextContent(type="text", text=result_text)]
    
    elif name == "rotate_region":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        center_x = arguments["center_x"]
        center_y = arguments["center_y"]
        center_z = arguments["center_z"]
        axis = arguments["axis"]
        degrees = arguments["degrees"]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.rotate_region(x1, y1, z1, x2, y2, z2, center_x, center_y, center_z, axis, degrees)
        return save(filepath, model, f"Rotated region {degrees}° around {axis}-axis")
    
    elif name == "mirror_region":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        plane = arguments["plane"]
        position = arguments["position"]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.mirror_region(x1, y1, z1, x2, y2, z2, plane, position)
        return save(filepath, model, f"Mirrored region across {plane}={position} plane")
    
    elif name == "copy_region":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        target_x = arguments["target_x"]
        target_y = arguments["target_y"]
        target_z = arguments["target_z"]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.copy_region(x1, y1, z1, x2, y2, z2, target_x, target_y, target_z)
        return save(filepath, model, f"Copied region to ({target_x}, {target_y}, {target_z})")
    
    elif name == "extrude_region":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        direction = arguments["direction"]
        distance = arguments["distance"]
        color_index = arguments.get("color_index")
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.extrude_region(x1, y1, z1, x2, y2, z2, direction, distance, color_index)
        return save(filepath, model, f"Extruded region {distance} units in {direction} direction")
    
    elif name == "find_connected_components":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        components = model.find_connected_components()
        
        result_text = f"Found {len(components)} connected component(s):\n"
        for i, comp in enumerate(components, 1):
            result_text += f"  Component {i}: {comp['voxel_count']} voxels, bounds {comp['bounds']}\n"
        
        return [TextContent(type="text", text=result_text)]
    
    elif name == "get_surface_voxels":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        surface = model.get_surface_voxels()
        
        return [TextContent(type="text", text=f"Found {len(surface)} surface voxels (exposed faces)")]
    
    elif name == "subtract_region":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.subtract_region(x1, y1, z1, x2, y2, z2)
        return save(filepath, model, f"Subtracted region from ({x1}, {y1}, {z1}) to ({x2}, {y2}, {z2})")
    
    elif name == "union_models":
        target_filename = arguments["target_filename"]
        source_filename = arguments["source_filename"]
        offset_x = arguments.get("offset_x", 0)
        offset_y = arguments.get("offset_y", 0)
        offset_z = arguments.get("offset_z", 0)
        
        target_path = get_vox_path(target_filename)
        source_path = get_vox_path(source_filename)
        
        if not target_path.exists():
            raise FileNotFoundError(f"Target file '{target_filename}' not found")
        if not source_path.exists():
            raise FileNotFoundError(f"Source file '{source_filename}' not found")
        
        target_model = read_vox_file(target_path)
        source_model = read_vox_file(source_path)
        target_model.union_with_model(source_model, offset_x, offset_y, offset_z)
        return save(target_path, target_model, f"Combined '{source_filename}' into '{target_filename}' with offset ({offset_x}, {offset_y}, {offset_z})")
    
    elif name == "intersect_region":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        before_count = model.get_voxel_count()
        model.intersect_region(x1, y1, z1, x2, y2, z2)
        after_count = model.get_voxel_count()
        return save(filepath, model, f"Intersected region: kept {after_count} voxels (removed {before_count - after_count})")
    
    elif name == "scale_model":
        filename = arguments["filename"]
        factor = arguments.get("factor", 2.0)
        factor_x = arguments.get("factor_x", factor)
        factor_y = arguments.get("factor_y", factor)
        factor_z = arguments.get("factor_z", factor)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.scale_model(factor_x, factor_y, factor_z)
        return save(filepath, model, f"Scaled model by ({factor_x}, {factor_y}, {factor_z})")
    
    elif name == "dilate":
        filename = arguments["filename"]
        iterations = arguments.get("iterations", 1)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.dilate(iterations)
        return save(filepath, model, f"Dilated model {iterations} time(s)")
    
    elif name == "erode":
        filename = arguments["filename"]
        iterations = arguments.get("iterations", 1)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.erode(iterations)
        return save(filepath, model, f"Eroded model {iterations} time(s)")
    
    elif name == "flood_fill":
        filename = arguments["filename"]
        color_index = arguments.get("color_index", 1)

        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")

        model = read_vox_file(filepath)
        before_count = model.get_voxel_count()
        model.flood_fill(color_index)
        filled = model.get_voxel_count() - before_count
        return save(filepath, model, f"Flood fill: filled {filled} enclosed voxel(s) with color {color_index}")
    
    elif name == "shell":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        before_count = model.get_voxel_count()
        model.shell()
        after_count = model.get_voxel_count()
        return save(filepath, model, f"Shell operation: {after_count} surface voxels (removed {before_count - after_count} interior)")
    
    elif name == "invert":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.invert()
        return save(filepath, model, "Inverted model (swapped solid/empty space)")
    
    elif name == "shrink":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.shrink()
        message = "Shrank the model to fit its voxels"
        if any(model.shift):
            message += f"; voxels moved by {model.shift} so the model starts at the origin"
        return save(filepath, model, message)
    
    elif name == "repeat_pattern":
        filename = arguments["filename"]
        count_x = arguments.get("count_x", 2)
        count_y = arguments.get("count_y", 1)
        count_z = arguments.get("count_z", 1)
        mirror = arguments.get("mirror", False)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.repeat_pattern(count_x, count_y, count_z, mirror)
        return save(filepath, model, f"Repeated pattern {count_x}x{count_y}x{count_z} times")
    
    elif name == "apply_noise":
        filename = arguments["filename"]
        seed = arguments.get("seed", 0)
        min_val = arguments.get("min_val", 0.0)
        max_val = arguments.get("max_val", 1.0)

        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")

        model = read_vox_file(filepath)
        changed = model.apply_noise(seed, min_val, max_val)
        return save(filepath, model, f"Applied noise with seed {seed}: {changed} voxel(s) changed colour")
    
    elif name == "randomize_colors":
        filename = arguments["filename"]
        min_index = arguments.get("min_index", 1)
        max_index = arguments.get("max_index", 255)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        model.randomize_colors(min_index, max_index)
        return save(filepath, model, f"Randomized colors between {min_index} and {max_index}")
    
    elif name == "optimize_palette":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File '{filename}' not found")
        
        model = read_vox_file(filepath)
        used = model.optimize_palette()
        return save(filepath, model, f"Optimized palette: the {used} colour(s) in use are now indices 1-{used}; unused entries follow")
    
    elif name == "list_models":
        vox_files = sorted(DEFAULT_VOX_DIR.glob("*.vox"))
        if not vox_files:
            return [TextContent(type="text", text="No .vox files found in vox directory")]
        
        file_list = "\n".join([f"  - {f.name}" for f in vox_files])
        return [TextContent(type="text", text=f"Found {len(vox_files)} .vox files:\n{file_list}")]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
