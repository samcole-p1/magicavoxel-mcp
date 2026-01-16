#!/usr/bin/env python3
"""
MagicaVoxel MCP Server
Provides tools for creating, modifying, and managing MagicaVoxel .vox files
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from vox_utils import (VoxelModel, read_vox_file, write_vox_file, check_connection, 
                       detect_gaps, suggest_connection_fix, check_proportions, 
                       calculate_human_proportions, suggest_proportions, calculate_minecraft_proportions)

# Import intelligence layer
try:
    from intelligence import MCPIntelligence
    INTELLIGENCE_ENABLED = True
except ImportError:
    INTELLIGENCE_ENABLED = False
    MCPIntelligence = None


# Initialize MCP server
app = Server("magicavoxel-mcp")

# Default paths - can be overridden by environment variables
DEFAULT_VOX_DIR = Path(os.getenv("VOX_DIR", "vox"))
DEFAULT_EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "export"))

# Initialize intelligence if available
intelligence = None
if INTELLIGENCE_ENABLED:
    try:
        intelligence = MCPIntelligence(DEFAULT_VOX_DIR)
    except Exception as e:
        # Intelligence layer optional, continue without it
        intelligence = None


def get_vox_path(filename: str) -> Path:
    """Get full path to a .vox file"""
    if not filename.endswith('.vox'):
        filename += '.vox'
    return DEFAULT_VOX_DIR / filename


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="create_voxel_model",
            description="Create a new empty voxel model with specified dimensions",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the .vox file to create (without .vox extension)"
                    },
                    "width": {
                        "type": "integer",
                        "description": "Width (X dimension) of the model",
                        "default": 10
                    },
                    "height": {
                        "type": "integer",
                        "description": "Height (Y dimension) of the model",
                        "default": 10
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Depth (Z dimension) of the model",
                        "default": 10
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="read_voxel_model",
            description="Read and inspect a .vox file, returning information about its structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the .vox file to read (without .vox extension)"
                    }
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
                    "filename": {
                        "type": "string",
                        "description": "Name of the .vox file to modify"
                    },
                    "x": {
                        "type": "integer",
                        "description": "X coordinate"
                    },
                    "y": {
                        "type": "integer",
                        "description": "Y coordinate"
                    },
                    "z": {
                        "type": "integer",
                        "description": "Z coordinate"
                    },
                    "color_index": {
                        "type": "integer",
                        "description": "Color index (0-255) from the palette",
                        "default": 1
                    }
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
                    "filename": {
                        "type": "string",
                        "description": "Name of the .vox file to modify"
                    },
                    "x1": {
                        "type": "integer",
                        "description": "Start X coordinate"
                    },
                    "y1": {
                        "type": "integer",
                        "description": "Start Y coordinate"
                    },
                    "z1": {
                        "type": "integer",
                        "description": "Start Z coordinate"
                    },
                    "x2": {
                        "type": "integer",
                        "description": "End X coordinate"
                    },
                    "y2": {
                        "type": "integer",
                        "description": "End Y coordinate"
                    },
                    "z2": {
                        "type": "integer",
                        "description": "End Z coordinate"
                    },
                    "color_index": {
                        "type": "integer",
                        "description": "Color index (0-255) from the palette",
                        "default": 1
                    }
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2"]
            }
        ),
        Tool(
            name="list_models",
            description="List all .vox files in the vox directory",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_model_info",
            description="Get detailed information about a voxel model including dimensions and voxel count",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the .vox file to inspect"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="get_proportion_suggestions",
            description="Get suggested body part proportions for a character model based on standard human proportions (8 heads tall) or Minecraft proportions",
            inputSchema={
                "type": "object",
                "properties": {
                    "model_height": {
                        "type": "integer",
                        "description": "Total height of the character model in voxels"
                    },
                    "style": {
                        "type": "string",
                        "description": "Proportion style: 'standard' (8 heads), 'minecraft' (Minecraft player), 'heroic' (9 heads), 'chibi' (4-5 heads)",
                        "default": "standard",
                        "enum": ["standard", "minecraft", "heroic", "chibi"]
                    }
                },
                "required": ["model_height"]
            }
        ),
        Tool(
            name="create_sphere",
            description="Create a sphere in a model at specified center with given radius",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file to modify"},
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
                    "filename": {"type": "string", "description": "Name of the .vox file to modify"},
                    "center_x": {"type": "integer", "description": "X coordinate of cylinder base center"},
                    "center_y": {"type": "integer", "description": "Y coordinate of cylinder base center"},
                    "center_z": {"type": "integer", "description": "Z coordinate of cylinder base center"},
                    "radius": {"type": "integer", "description": "Radius of the cylinder"},
                    "height": {"type": "integer", "description": "Height of the cylinder"},
                    "axis": {"type": "string", "description": "Axis direction: 'x', 'y', or 'z'", "default": "y"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create hollow cylinder", "default": False}
                },
                "required": ["filename", "center_x", "center_y", "center_z", "radius", "height"]
            }
        ),
        Tool(
            name="create_pyramid",
            description="Create a pyramid in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file to modify"},
                    "base_x": {"type": "integer", "description": "X coordinate of pyramid base corner"},
                    "base_y": {"type": "integer", "description": "Y coordinate of pyramid base (bottom)"},
                    "base_z": {"type": "integer", "description": "Z coordinate of pyramid base corner"},
                    "base_width": {"type": "integer", "description": "Width of pyramid base"},
                    "base_depth": {"type": "integer", "description": "Depth of pyramid base"},
                    "height": {"type": "integer", "description": "Height of the pyramid"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create hollow pyramid", "default": False}
                },
                "required": ["filename", "base_x", "base_y", "base_z", "base_width", "base_depth", "height"]
            }
        ),
        Tool(
            name="replace_color",
            description="Replace all voxels of one color with another color in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file to modify"},
                    "old_color": {"type": "integer", "description": "Color index to replace (0-255)"},
                    "new_color": {"type": "integer", "description": "New color index (0-255)"}
                },
                "required": ["filename", "old_color", "new_color"]
            }
        ),
        Tool(
            name="set_palette_color",
            description="Set a specific color in the model's palette",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file to modify"},
                    "color_index": {"type": "integer", "description": "Palette index to set (0-255)"},
                    "r": {"type": "integer", "description": "Red component (0-255)"},
                    "g": {"type": "integer", "description": "Green component (0-255)"},
                    "b": {"type": "integer", "description": "Blue component (0-255)"},
                    "a": {"type": "integer", "description": "Alpha component (0-255)", "default": 255}
                },
                "required": ["filename", "color_index", "r", "g", "b"]
            }
        ),
        Tool(
            name="count_colors",
            description="Count voxels by color index in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file to analyze"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="copy_region",
            description="Copy a region of voxels to another location in the same model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file to modify"},
                    "x1": {"type": "integer", "description": "Start X coordinate of source region"},
                    "y1": {"type": "integer", "description": "Start Y coordinate of source region"},
                    "z1": {"type": "integer", "description": "Start Z coordinate of source region"},
                    "x2": {"type": "integer", "description": "End X coordinate of source region"},
                    "y2": {"type": "integer", "description": "End Y coordinate of source region"},
                    "z2": {"type": "integer", "description": "End Z coordinate of source region"},
                    "target_x": {"type": "integer", "description": "Target X coordinate"},
                    "target_y": {"type": "integer", "description": "Target Y coordinate"},
                    "target_z": {"type": "integer", "description": "Target Z coordinate"},
                    "overwrite": {"type": "boolean", "description": "Overwrite existing voxels", "default": True}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "target_x", "target_y", "target_z"]
            }
        ),
        Tool(
            name="create_stairs",
            description="Create a staircase in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file to modify"},
                    "start_x": {"type": "integer", "description": "Starting X coordinate"},
                    "start_y": {"type": "integer", "description": "Starting Y coordinate (bottom)"},
                    "start_z": {"type": "integer", "description": "Starting Z coordinate"},
                    "width": {"type": "integer", "description": "Width of each step"},
                    "depth": {"type": "integer", "description": "Depth of each step"},
                    "num_steps": {"type": "integer", "description": "Number of steps"},
                    "step_height": {"type": "integer", "description": "Height of each step", "default": 1},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1}
                },
                "required": ["filename", "start_x", "start_y", "start_z", "width", "depth", "num_steps"]
            }
        ),
        Tool(
            name="create_wall",
            description="Create a wall in a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file to modify"},
                    "start_x": {"type": "integer", "description": "Starting X coordinate"},
                    "start_y": {"type": "integer", "description": "Starting Y coordinate (bottom)"},
                    "start_z": {"type": "integer", "description": "Starting Z coordinate"},
                    "length": {"type": "integer", "description": "Length of the wall"},
                    "height": {"type": "integer", "description": "Height of the wall"},
                    "direction": {"type": "string", "description": "Direction: 'x' or 'z'", "default": "x"},
                    "thickness": {"type": "integer", "description": "Wall thickness", "default": 1},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1}
                },
                "required": ["filename", "start_x", "start_y", "start_z", "length", "height"]
            }
        ),
        Tool(
            name="smart_create_model",
            description="Intelligently create a voxel model with template support and smart defaults",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file to create"},
                    "template": {"type": "string", "description": "Template name (character, warrior, building, tree)", "default": None},
                    "width": {"type": "integer", "description": "Width (optional if using template)"},
                    "height": {"type": "integer", "description": "Height (optional if using template)"},
                    "depth": {"type": "integer", "description": "Depth (optional if using template)"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="get_suggestions",
            description="Get intelligent suggestions for next operations on a model",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file to get suggestions for"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="list_templates",
            description="List available templates for model creation",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_operation_stats",
            description="Get statistics about operations performed",
            inputSchema={
                "type": "object",
                "properties": {}
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
            description="Get all palette colors from a model",
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
                    "filename": {"type": "string", "description": "Name of the .vox file to delete"}
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="copy_model",
            description="Copy a .vox file to a new filename",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_filename": {"type": "string", "description": "Source .vox file name"},
                    "target_filename": {"type": "string", "description": "Target .vox file name"}
                },
                "required": ["source_filename", "target_filename"]
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
                    "axis": {"type": "string", "description": "Axis: 'x', 'y', or 'z'", "default": "y"},
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
                    "base_y": {"type": "integer", "description": "Y coordinate of base (bottom)"},
                    "base_z": {"type": "integer", "description": "Z coordinate of base center"},
                    "base_radius": {"type": "integer", "description": "Radius of base"},
                    "height": {"type": "integer", "description": "Height of cone"},
                    "axis": {"type": "string", "description": "Axis: 'x', 'y', or 'z'", "default": "y"},
                    "color_index": {"type": "integer", "description": "Color index (0-255)", "default": 1},
                    "hollow": {"type": "boolean", "description": "Create hollow cone", "default": False}
                },
                "required": ["filename", "base_x", "base_y", "base_z", "base_radius", "height"]
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
            name="merge_models",
            description="Combine two models into one with optional offset",
            inputSchema={
                "type": "object",
                "properties": {
                    "source1_filename": {"type": "string", "description": "First source .vox file"},
                    "source2_filename": {"type": "string", "description": "Second source .vox file"},
                    "target_filename": {"type": "string", "description": "Target .vox file name"},
                    "offset_x": {"type": "integer", "description": "X offset for second model", "default": 0},
                    "offset_y": {"type": "integer", "description": "Y offset for second model", "default": 0},
                    "offset_z": {"type": "integer", "description": "Z offset for second model", "default": 0},
                    "overwrite": {"type": "boolean", "description": "Overwrite overlapping voxels", "default": True}
                },
                "required": ["source1_filename", "source2_filename", "target_filename"]
            }
        ),
        Tool(
            name="rotate_region",
            description="Rotate a region 90, 180, or 270 degrees around an axis",
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
                    "axis": {"type": "string", "description": "Rotation axis: 'x', 'y', or 'z'"},
                    "degrees": {"type": "integer", "description": "Rotation angle: 90, 180, or 270"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "center_x", "center_y", "center_z", "axis", "degrees"]
            }
        ),
        Tool(
            name="mirror_region",
            description="Mirror a region across a plane",
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
                    "plane": {"type": "string", "description": "Mirror plane: 'x', 'y', or 'z'"},
                    "position": {"type": "integer", "description": "Position of the mirror plane"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "plane", "position"]
            }
        ),
        Tool(
            name="move_region",
            description="Move a region to a new location (translates voxels)",
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
                    "target_x": {"type": "integer", "description": "Target X coordinate"},
                    "target_y": {"type": "integer", "description": "Target Y coordinate"},
                    "target_z": {"type": "integer", "description": "Target Z coordinate"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "target_x", "target_y", "target_z"]
            }
        ),
        Tool(
            name="find_connected_components",
            description="Find all separate connected pieces in a model. Use suggest_fixes=True to get suggestions for connecting disconnected parts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the .vox file"},
                    "suggest_fixes": {"type": "boolean", "description": "If true, suggest how to connect disconnected components", "default": False}
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
            name="extrude_region",
            description="Extrude a region in a direction",
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
                    "direction": {"type": "string", "description": "Direction: 'x+', 'x-', 'y+', 'y-', 'z+', 'z-'"},
                    "distance": {"type": "integer", "description": "Distance to extrude"},
                    "color_index": {"type": "integer", "description": "Optional color override"}
                },
                "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "direction", "distance"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""
    
    if name == "create_voxel_model":
        filename = arguments["filename"]
        width = arguments.get("width", 10)
        height = arguments.get("height", 10)
        depth = arguments.get("depth", 10)
        
        filepath = get_vox_path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Use intelligence for validation and tracking
        if intelligence:
            is_valid, error = intelligence.validate_operation(
                "create_voxel_model",
                {"width": width, "height": height, "depth": depth}
            )
            if not is_valid:
                return [TextContent(type="text", text=f"Validation error: {error}")]
        
        try:
            # Create a new empty model
            model = VoxelModel(width, height, depth)
            write_vox_file(filepath, model)
            
            # Track operation
            if intelligence:
                intelligence.track_operation(
                    "create_voxel_model",
                    filename,
                    {"width": width, "height": height, "depth": depth}
                )
            
            result_text = f"Created new voxel model '{filename}' with dimensions {width}x{height}x{depth}"
            
            # Add suggestions if intelligence is available
            if intelligence:
                suggestions = intelligence.suggest_next_operations(filename)
                if suggestions:
                    result_text += f"\n\nSuggestions: {', '.join(suggestions[:3])}"
            
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error creating model: {str(e)}"
            )]
    
    elif name == "read_voxel_model":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            return [TextContent(
                type="text",
                text=f"Error: File '{filename}' not found"
            )]
        
        try:
            model = read_vox_file(filepath)
            
            info = {
                "filename": filename,
                "dimensions": {
                    "x": model.size_x,
                    "y": model.size_y,
                    "z": model.size_z
                },
                "voxel_count": model.get_voxel_count(),
                "palette_size": len(model.palette)
            }
            
            return [TextContent(
                type="text",
                text=f"Model info: {json.dumps(info, indent=2)}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error reading model: {str(e)}"
            )]
    
    elif name == "place_voxel":
        filename = arguments["filename"]
        x = arguments["x"]
        y = arguments["y"]
        z = arguments["z"]
        color_index = arguments.get("color_index", 1)
        
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            return [TextContent(
                type="text",
                text=f"Error: File '{filename}' not found. Create it first using create_voxel_model"
            )]
        
        try:
            # Read existing model
            model = read_vox_file(filepath)
            
            # Place voxel
            model.set_voxel(x, y, z, color_index)
            
            # Write back
            write_vox_file(filepath, model)
            
            return [TextContent(
                type="text",
                text=f"Placed voxel at ({x}, {y}, {z}) with color index {color_index}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error placing voxel: {str(e)}"
            )]
    
    elif name == "fill_box":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        color_index = arguments.get("color_index", 1)
        
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            return [TextContent(
                type="text",
                text=f"Error: File '{filename}' not found. Create it first using create_voxel_model"
            )]
        
        try:
            # Read existing model
            model = read_vox_file(filepath)
            
            # Check if model has existing voxels (not first operation)
            has_existing = len(model.voxels) > 0
            
            # Check connection if there are existing voxels
            warnings = []
            if has_existing:
                connects, nearest = check_connection(model, x1, y1, z1, x2, y2, z2)
                if not connects:
                    suggestion = suggest_connection_fix(model, x1, y1, z1, x2, y2, z2)
                    if suggestion:
                        warnings.append(f"Warning: Box does not connect to existing parts. {suggestion}")
            
            # Fill box region
            model.fill_box(x1, y1, z1, x2, y2, z2, color_index)
            count = (abs(x2 - x1) + 1) * (abs(y2 - y1) + 1) * (abs(z2 - z1) + 1)
            
            # Store box dimensions for proportion checking
            box_width = abs(x2 - x1) + 1
            box_height = abs(y2 - y1) + 1
            box_depth = abs(z2 - z1) + 1
            
            # Check for gaps after filling
            if has_existing:
                gaps = detect_gaps(model, x1, y1, z1, x2, y2, z2)
                if gaps and len(gaps) <= 5:  # Only report small gaps
                    gap_str = ", ".join([f"y={g}" for g in gaps[:3]])
                    if len(gaps) > 3:
                        gap_str += f" (+{len(gaps)-3} more)"
                    warnings.append(f"Detected {len(gaps)}-voxel gap(s) at {gap_str}. Consider filling gaps for better connection.")
                
                # Check proportions for body parts (if box is vertical and tall, might be torso/legs)
                box_height = abs(y2 - y1) + 1
                box_width = abs(x2 - x1) + 1
                box_depth = abs(z2 - z1) + 1
                
                if box_height > 4 and box_width <= 6 and box_depth <= 6:  # Vertical box, might be body part
                    all_y = [y for (x, y, z) in model.voxels.keys()]
                    if all_y:
                        model_height = max(all_y) - min(all_y) + 1
                        # Determine if this might be a body part based on position
                        box_center_y = (y1 + y2) // 2
                        model_top = max(all_y)
                        model_bottom = min(all_y)
                        
                        # If box is in upper third, might be torso
                        if box_center_y > (model_top + model_bottom) * 2 // 3:
                            prop_warning = check_proportions(model, "torso", (box_width, box_height, box_depth), 
                                                            model_height, style="standard")
                            if prop_warning:
                                warnings.append(prop_warning)
                        # If box is in lower third, might be legs
                        elif box_center_y < (model_top + model_bottom) // 3:
                            prop_warning = check_proportions(model, "legs", (box_width, box_height, box_depth), 
                                                            model_height, style="standard")
                            if prop_warning:
                                warnings.append(prop_warning)
            
            # Write back
            write_vox_file(filepath, model)
            
            result_text = f"Filled box from ({x1}, {y1}, {z1}) to ({x2}, {y2}, {z2}) with {count} voxels"
            if warnings:
                result_text += "\n" + "\n".join(warnings)
            
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error filling box: {str(e)}"
            )]
    
    elif name == "list_models":
        try:
            vox_dir = Path(DEFAULT_VOX_DIR)
            if not vox_dir.exists():
                return [TextContent(
                    type="text",
                    text="No vox directory found"
                )]
            
            models = [f.name for f in vox_dir.glob("*.vox")]
            return [TextContent(
                type="text",
                text=f"Available models: {', '.join(models) if models else 'None'}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error listing models: {str(e)}"
            )]
    
    elif name == "get_model_info":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            return [TextContent(
                type="text",
                text=f"Error: File '{filename}' not found"
            )]
        
        try:
            model = read_vox_file(filepath)
            bounds = model.get_bounds()
            
            # Extract model information
            info = {
                "filename": filename,
                "file_size_bytes": filepath.stat().st_size,
                "dimensions": {
                    "x": model.size_x,
                    "y": model.size_y,
                    "z": model.size_z
                },
                "actual_bounds": {
                    "x": bounds[0],
                    "y": bounds[1],
                    "z": bounds[2]
                },
                "voxel_count": model.get_voxel_count(),
                "palette_size": len(model.palette)
            }
            
            return [TextContent(
                type="text",
                text=f"Model information:\n{json.dumps(info, indent=2)}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting model info: {str(e)}"
            )]
    
    elif name == "get_proportion_suggestions":
        model_height = arguments["model_height"]
        style = arguments.get("style", "standard")
        
        try:
            suggestions = suggest_proportions(model_height, style)
            mc_props = calculate_minecraft_proportions()
            
            result_text = f"Proportion suggestions for {model_height}-voxel {style} character:\n\n"
            result_text += "Body Part Dimensions:\n"
            for part, dims in suggestions.items():
                if part == 'head':
                    result_text += f"  {part.capitalize()}: {dims['height']}×{dims['width']}×{dims['depth']} voxels (radius: {dims['radius']})\n"
                elif part == 'arms':
                    result_text += f"  {part.capitalize()}: {dims['length']}×{dims['width']}×{dims['depth']} voxels\n"
                else:
                    result_text += f"  {part.capitalize()}: {dims['height']}×{dims['width']}×{dims['depth']} voxels\n"
            
            if style == "minecraft":
                result_text += f"\nMinecraft Reference:\n"
                result_text += f"  Player height: {mc_props['player_height_standing']} blocks (standing)\n"
                result_text += f"  Player width: {mc_props['player_width']} blocks\n"
                result_text += f"  Eye height: {mc_props['eye_height_standing']} meters\n"
                result_text += f"  Standard skin: {mc_props['player_model_height_voxels']} voxels tall\n"
            
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting proportion suggestions: {str(e)}"
            )]
    
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
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            has_existing = len(model.voxels) > 0
            
            # Check connection if there are existing voxels
            warnings = []
            if has_existing:
                # Check if sphere connects (approximate: check if any sphere voxel would be adjacent)
                sphere_radius = radius
                # Check a few key points on sphere surface
                check_points = [
                    (center_x + sphere_radius, center_y, center_z),
                    (center_x - sphere_radius, center_y, center_z),
                    (center_x, center_y + sphere_radius, center_z),
                    (center_x, center_y - sphere_radius, center_z),
                    (center_x, center_y, center_z + sphere_radius),
                    (center_x, center_y, center_z - sphere_radius),
                ]
                connects = False
                for cx, cy, cz in check_points:
                    for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                        if (cx+dx, cy+dy, cz+dz) in model.voxels:
                            connects = True
                            break
                    if connects:
                        break
                
                if not connects:
                    warnings.append(f"Warning: Sphere may not connect to existing parts. Consider adjusting position or radius.")
            
            model.create_sphere(center_x, center_y, center_z, radius, color_index, hollow)
            write_vox_file(filepath, model)
            
            result_text = f"Created {'hollow' if hollow else 'solid'} sphere at ({center_x}, {center_y}, {center_z}) with radius {radius}"
            if warnings:
                result_text += "\n" + "\n".join(warnings)
            
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating sphere: {str(e)}")]
    
    elif name == "create_cylinder":
        filename = arguments["filename"]
        center_x = arguments["center_x"]
        center_y = arguments["center_y"]
        center_z = arguments["center_z"]
        radius = arguments["radius"]
        height = arguments["height"]
        axis = arguments.get("axis", "y")
        color_index = arguments.get("color_index", 1)
        hollow = arguments.get("hollow", False)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            has_existing = len(model.voxels) > 0
            
            # Check connection if there are existing voxels
            warnings = []
            if has_existing:
                # Calculate cylinder bounds
                if axis == 'y':
                    cyl_x1, cyl_x2 = center_x - radius, center_x + radius
                    cyl_y1, cyl_y2 = center_y, center_y + height - 1
                    cyl_z1, cyl_z2 = center_z - radius, center_z + radius
                elif axis == 'x':
                    cyl_x1, cyl_x2 = center_x, center_x + height - 1
                    cyl_y1, cyl_y2 = center_y - radius, center_y + radius
                    cyl_z1, cyl_z2 = center_z - radius, center_z + radius
                else:  # z
                    cyl_x1, cyl_x2 = center_x - radius, center_x + radius
                    cyl_y1, cyl_y2 = center_y - radius, center_y + radius
                    cyl_z1, cyl_z2 = center_z, center_z + height - 1
                
                connects, nearest = check_connection(model, cyl_x1, cyl_y1, cyl_z1, cyl_x2, cyl_y2, cyl_z2)
                if not connects:
                    suggestion = suggest_connection_fix(model, cyl_x1, cyl_y1, cyl_z1, cyl_x2, cyl_y2, cyl_z2)
                    if suggestion:
                        warnings.append(f"Warning: Cylinder may not connect to existing parts. {suggestion}")
            
            model.create_cylinder(center_x, center_y, center_z, radius, height, axis, color_index, hollow)
            write_vox_file(filepath, model)
            
            result_text = f"Created {'hollow' if hollow else 'solid'} cylinder at ({center_x}, {center_y}, {center_z}) with radius {radius}, height {height}, axis {axis}"
            if warnings:
                result_text += "\n" + "\n".join(warnings)
            
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating cylinder: {str(e)}")]
    
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
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            model.create_pyramid(base_x, base_y, base_z, base_width, base_depth, height, color_index, hollow)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Created {'hollow' if hollow else 'solid'} pyramid at ({base_x}, {base_y}, {base_z}) with base {base_width}x{base_depth}, height {height}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating pyramid: {str(e)}")]
    
    elif name == "replace_color":
        filename = arguments["filename"]
        old_color = arguments["old_color"]
        new_color = arguments["new_color"]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            count_before = sum(1 for c in model.voxels.values() if c == old_color)
            model.replace_color(old_color, new_color)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Replaced {count_before} voxels from color {old_color} to {new_color}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error replacing color: {str(e)}")]
    
    elif name == "set_palette_color":
        filename = arguments["filename"]
        color_index = arguments["color_index"]
        r = arguments["r"]
        g = arguments["g"]
        b = arguments["b"]
        a = arguments.get("a", 255)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            model.set_palette_color(color_index, r, g, b, a)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Set palette color {color_index} to RGB({r}, {g}, {b}, {a})")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error setting palette color: {str(e)}")]
    
    elif name == "count_colors":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            color_counts = model.count_colors()
            result = {str(k): v for k, v in sorted(color_counts.items(), key=lambda x: x[1], reverse=True)}
            return [TextContent(type="text", text=f"Color counts: {json.dumps(result, indent=2)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error counting colors: {str(e)}")]
    
    elif name == "copy_region":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        target_x, target_y, target_z = arguments["target_x"], arguments["target_y"], arguments["target_z"]
        overwrite = arguments.get("overwrite", True)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            model.copy_region(x1, y1, z1, x2, y2, z2, target_x, target_y, target_z, overwrite)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Copied region from ({x1},{y1},{z1}) to ({x2},{y2},{z2}) to ({target_x},{target_y},{target_z})")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error copying region: {str(e)}")]
    
    elif name == "create_stairs":
        filename = arguments["filename"]
        start_x = arguments["start_x"]
        start_y = arguments["start_y"]
        start_z = arguments["start_z"]
        width = arguments["width"]
        depth = arguments["depth"]
        num_steps = arguments["num_steps"]
        step_height = arguments.get("step_height", 1)
        color_index = arguments.get("color_index", 1)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            model.create_stairs(start_x, start_y, start_z, width, depth, num_steps, step_height, color_index)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Created staircase with {num_steps} steps starting at ({start_x}, {start_y}, {start_z})")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating stairs: {str(e)}")]
    
    elif name == "create_wall":
        filename = arguments["filename"]
        start_x = arguments["start_x"]
        start_y = arguments["start_y"]
        start_z = arguments["start_z"]
        length = arguments["length"]
        height = arguments["height"]
        direction = arguments.get("direction", "x")
        thickness = arguments.get("thickness", 1)
        color_index = arguments.get("color_index", 1)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            model.create_wall(start_x, start_y, start_z, length, height, direction, thickness, color_index)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Created wall at ({start_x}, {start_y}, {start_z}) with length {length}, height {height}, direction {direction}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating wall: {str(e)}")]
    
    elif name == "smart_create_model":
        if not intelligence:
            return [TextContent(type="text", text="Intelligence layer not available. Use create_voxel_model instead.")]
        
        filename = arguments["filename"]
        template = arguments.get("template")
        
        # Use template if provided
        width = arguments.get("width")
        height = arguments.get("height")
        depth = arguments.get("depth")
        
        if template:
            template_data = intelligence.get_template(template)
            if template_data:
                dims = template_data["dimensions"]
                width = width or dims[0]
                height = height or dims[1]
                depth = depth or dims[2]
                result_text = f"Using template '{template}': {template_data['description']}\n"
            else:
                return [TextContent(type="text", text=f"Template '{template}' not found. Available: {', '.join(intelligence.list_templates())}")]
        else:
            # Get smart defaults
            defaults = intelligence.get_smart_defaults("create_voxel_model", filename)
            width = width or 16
            height = height or 32
            depth = depth or 16
            result_text = "Created model with smart defaults\n"
        
        # Validate
        is_valid, error = intelligence.validate_operation(
            "create_voxel_model",
            {"width": width, "height": height, "depth": depth}
        )
        if not is_valid:
            return [TextContent(type="text", text=f"Validation error: {error}")]
        
        # Create model
        filepath = get_vox_path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            model = VoxelModel(width, height, depth)
            write_vox_file(filepath, model)
            
            intelligence.track_operation(
                "smart_create_model",
                filename,
                {"width": width, "height": height, "depth": depth, "template": template}
            )
            
            result_text += f"Created '{filename}' with dimensions {width}x{height}x{depth}"
            suggestions = intelligence.suggest_next_operations(filename)
            if suggestions:
                result_text += f"\n\nNext steps: {', '.join(suggestions[:3])}"
            
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    elif name == "get_suggestions":
        if not intelligence:
            return [TextContent(type="text", text="Intelligence layer not available.")]
        
        filename = arguments["filename"]
        suggestions = intelligence.suggest_next_operations(filename)
        
        if suggestions:
            return [TextContent(
                type="text",
                text=f"Suggestions for '{filename}':\n" + "\n".join(f"  - {s}" for s in suggestions)
            )]
        else:
            return [TextContent(type="text", text=f"No suggestions available for '{filename}'")]
    
    elif name == "list_templates":
        if not intelligence:
            return [TextContent(type="text", text="Intelligence layer not available.")]
        
        templates = intelligence.list_templates()
        template_info = []
        for t in templates:
            template_data = intelligence.get_template(t)
            if template_data:
                template_info.append(f"  {t}: {template_data['description']} ({template_data['dimensions']})")
        
        return [TextContent(
            type="text",
            text="Available templates:\n" + "\n".join(template_info) if template_info else "No templates available"
        )]
    
    elif name == "get_operation_stats":
        if not intelligence:
            return [TextContent(type="text", text="Intelligence layer not available.")]
        
        stats = intelligence.get_operation_stats()
        if stats:
            stats_text = "Operation statistics:\n"
            for op, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                stats_text += f"  {op}: {count} times\n"
            return [TextContent(type="text", text=stats_text)]
        else:
            return [TextContent(type="text", text="No operations tracked yet.")]
    
    elif name == "remove_voxel":
        filename = arguments["filename"]
        x, y, z = arguments["x"], arguments["y"], arguments["z"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            model.remove_voxel(x, y, z)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Removed voxel at ({x}, {y}, {z})")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    elif name == "get_voxel":
        filename = arguments["filename"]
        x, y, z = arguments["x"], arguments["y"], arguments["z"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            color_index = model.get_voxel(x, y, z)
            if color_index == 0:
                return [TextContent(type="text", text=f"No voxel at ({x}, {y}, {z})")]
            return [TextContent(type="text", text=f"Voxel at ({x}, {y}, {z}) has color index {color_index}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    elif name == "get_palette":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            palette_data = []
            for i, (r, g, b, a) in enumerate(model.palette):
                if i < 10 or (r, g, b, a) != (0, 0, 0, 0):  # Show first 10 and non-transparent
                    palette_data.append({
                        "index": i,
                        "r": r, "g": g, "b": b, "a": a
                    })
            return [TextContent(type="text", text=f"Palette: {json.dumps(palette_data, indent=2)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    elif name == "delete_model":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            filepath.unlink()
            if intelligence:
                intelligence.track_operation("delete_model", filename, {})
            return [TextContent(type="text", text=f"Deleted model '{filename}'")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error deleting model: {str(e)}")]
    
    elif name == "copy_model":
        source_filename = arguments["source_filename"]
        target_filename = arguments["target_filename"]
        source_path = get_vox_path(source_filename)
        target_path = get_vox_path(target_filename)
        
        if not source_path.exists():
            return [TextContent(type="text", text=f"Error: Source file '{source_filename}' not found")]
        if target_path.exists():
            return [TextContent(type="text", text=f"Error: Target file '{target_filename}' already exists")]
        
        try:
            import shutil
            shutil.copy(source_path, target_path)
            if intelligence:
                intelligence.track_operation("copy_model", target_filename, {"source": source_filename})
            return [TextContent(type="text", text=f"Copied '{source_filename}' to '{target_filename}'")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error copying model: {str(e)}")]
    
    elif name == "create_torus":
        filename = arguments["filename"]
        center_x = arguments["center_x"]
        center_y = arguments["center_y"]
        center_z = arguments["center_z"]
        major_radius = arguments["major_radius"]
        minor_radius = arguments["minor_radius"]
        axis = arguments.get("axis", "y")
        color_index = arguments.get("color_index", 1)
        hollow = arguments.get("hollow", False)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            model.create_torus(center_x, center_y, center_z, major_radius, minor_radius, axis, color_index, hollow)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Created {'hollow' if hollow else 'solid'} torus at ({center_x}, {center_y}, {center_z}) with major radius {major_radius}, minor radius {minor_radius}, axis {axis}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating torus: {str(e)}")]
    
    elif name == "create_cone":
        filename = arguments["filename"]
        base_x = arguments["base_x"]
        base_y = arguments["base_y"]
        base_z = arguments["base_z"]
        base_radius = arguments["base_radius"]
        height = arguments["height"]
        axis = arguments.get("axis", "y")
        color_index = arguments.get("color_index", 1)
        hollow = arguments.get("hollow", False)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            model.create_cone(base_x, base_y, base_z, base_radius, height, axis, color_index, hollow)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Created {'hollow' if hollow else 'solid'} cone at ({base_x}, {base_y}, {base_z}) with base radius {base_radius}, height {height}, axis {axis}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating cone: {str(e)}")]
    
    elif name == "clear_region":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            model.clear_region(x1, y1, z1, x2, y2, z2)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Cleared region from ({x1}, {y1}, {z1}) to ({x2}, {y2}, {z2})")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error clearing region: {str(e)}")]
    
    elif name == "merge_models":
        source1_filename = arguments["source1_filename"]
        source2_filename = arguments["source2_filename"]
        target_filename = arguments["target_filename"]
        offset_x = arguments.get("offset_x", 0)
        offset_y = arguments.get("offset_y", 0)
        offset_z = arguments.get("offset_z", 0)
        overwrite = arguments.get("overwrite", True)
        
        source1_path = get_vox_path(source1_filename)
        source2_path = get_vox_path(source2_filename)
        target_path = get_vox_path(target_filename)
        
        if not source1_path.exists():
            return [TextContent(type="text", text=f"Error: Source file '{source1_filename}' not found")]
        if not source2_path.exists():
            return [TextContent(type="text", text=f"Error: Source file '{source2_filename}' not found")]
        
        try:
            model1 = read_vox_file(source1_path)
            model2 = read_vox_file(source2_path)
            
            # Create new model with combined dimensions
            max_x = max(model1.size_x, model2.size_x + offset_x)
            max_y = max(model1.size_y, model2.size_y + offset_y)
            max_z = max(model1.size_z, model2.size_z + offset_z)
            
            merged = VoxelModel(max_x, max_y, max_z)
            merged.palette = model1.palette.copy()  # Use first model's palette
            
            # Copy model1 voxels
            for (x, y, z), color in model1.voxels.items():
                merged.set_voxel(x, y, z, color)
            
            # Copy model2 voxels with offset
            for (x, y, z), color in model2.voxels.items():
                new_x = x + offset_x
                new_y = y + offset_y
                new_z = z + offset_z
                if overwrite or (new_x, new_y, new_z) not in merged.voxels:
                    merged.set_voxel(new_x, new_y, new_z, color)
            
            write_vox_file(target_path, merged)
            if intelligence:
                intelligence.track_operation("merge_models", target_filename, {
                    "source1": source1_filename,
                    "source2": source2_filename,
                    "offset": [offset_x, offset_y, offset_z]
                })
            return [TextContent(type="text", text=f"Merged '{source1_filename}' and '{source2_filename}' into '{target_filename}'")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error merging models: {str(e)}")]
    
    elif name == "rotate_region":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        center_x = arguments["center_x"]
        center_y = arguments["center_y"]
        center_z = arguments["center_z"]
        axis = arguments["axis"]
        degrees = arguments["degrees"]
        
        if degrees not in [90, 180, 270]:
            return [TextContent(type="text", text=f"Error: Degrees must be 90, 180, or 270, got {degrees}")]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            model.rotate_region(x1, y1, z1, x2, y2, z2, center_x, center_y, center_z, axis, degrees)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Rotated region {degrees}° around {axis} axis at ({center_x}, {center_y}, {center_z})")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error rotating region: {str(e)}")]
    
    elif name == "mirror_region":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        plane = arguments["plane"]
        position = arguments["position"]
        
        if plane not in ['x', 'y', 'z']:
            return [TextContent(type="text", text=f"Error: Plane must be 'x', 'y', or 'z', got {plane}")]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            model.mirror_region(x1, y1, z1, x2, y2, z2, plane, position)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Mirrored region across {plane} plane at position {position}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error mirroring region: {str(e)}")]
    
    elif name == "move_region":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        target_x, target_y, target_z = arguments["target_x"], arguments["target_y"], arguments["target_z"]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            # Copy region
            model.copy_region(x1, y1, z1, x2, y2, z2, target_x, target_y, target_z, overwrite=True)
            # Clear original
            model.clear_region(x1, y1, z1, x2, y2, z2)
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Moved region from ({x1},{y1},{z1}) to ({x2},{y2},{z2}) to ({target_x},{target_y},{target_z})")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error moving region: {str(e)}")]
    
    elif name == "find_connected_components":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            suggest_fixes = arguments.get("suggest_fixes", False)
            model = read_vox_file(filepath)
            components = model.find_connected_components()
            if not components:
                return [TextContent(type="text", text="No connected components found (empty model)")]
            
            result_text = f"Found {len(components)} connected component(s):\n"
            for i, comp in enumerate(components, 1):
                b = comp['bounds']
                result_text += f"  Component {i}: {comp['voxel_count']} voxels at ({b['min_x']},{b['min_y']},{b['min_z']}) to ({b['max_x']},{b['max_y']},{b['max_z']})\n"
            
            # Add suggestions if multiple components and suggest_fixes is True
            if len(components) > 1 and suggest_fixes:
                result_text += "\nSuggestions to connect components:\n"
                for i in range(len(components) - 1):
                    comp1 = components[i]
                    comp2 = components[i + 1]
                    b1 = comp1['bounds']
                    b2 = comp2['bounds']
                    
                    # Find closest points between components
                    # Simple approach: use center points
                    c1_x = (b1['min_x'] + b1['max_x']) // 2
                    c1_y = (b1['min_y'] + b1['max_y']) // 2
                    c1_z = (b1['min_z'] + b1['max_z']) // 2
                    c2_x = (b2['min_x'] + b2['max_x']) // 2
                    c2_y = (b2['min_y'] + b2['max_y']) // 2
                    c2_z = (b2['min_z'] + b2['max_z']) // 2
                    
                    # Suggest connection point (midpoint)
                    mid_x = (c1_x + c2_x) // 2
                    mid_y = (c1_y + c2_y) // 2
                    mid_z = (c1_z + c2_z) // 2
                    
                    result_text += f"  To connect component {i+1} and {i+2}: Use fill_box or place_voxel at ({mid_x}, {mid_y}, {mid_z})\n"
            
            if len(components) > 1:
                result_text += f"\nNote: Model has {len(components)} disconnected pieces. Use suggest_fixes=True for connection suggestions."
            
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    elif name == "get_surface_voxels":
        filename = arguments["filename"]
        filepath = get_vox_path(filename)
        
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            surface = model.get_surface_voxels()
            return [TextContent(type="text", text=f"Found {len(surface)} surface voxels out of {model.get_voxel_count()} total voxels")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    elif name == "extrude_region":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        direction = arguments["direction"]
        distance = arguments["distance"]
        color_index = arguments.get("color_index")
        
        if direction not in ['x+', 'x-', 'y+', 'y-', 'z+', 'z-']:
            return [TextContent(type="text", text=f"Error: Direction must be 'x+', 'x-', 'y+', 'y-', 'z+', or 'z-', got {direction}")]
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            model.extrude_region(x1, y1, z1, x2, y2, z2, direction, distance, color_index)
            write_vox_file(filepath, model)
            color_text = f" with color {color_index}" if color_index is not None else ""
            return [TextContent(type="text", text=f"Extruded region {distance} units in {direction} direction{color_text}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error extruding region: {str(e)}")]
    
    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]


async def main():
    """Main entry point"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
