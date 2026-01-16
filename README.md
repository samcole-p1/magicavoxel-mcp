# MagicaVoxel MCP Server

An MCP (Model Context Protocol) server for interacting with MagicaVoxel .vox files programmatically. This allows you to create, modify, and manage voxel models through natural language prompts.

## Features

- Create new voxel models with custom dimensions
- Read and inspect existing .vox files
- Place individual voxels at specific coordinates
- Fill rectangular regions with voxels
- List available models
- Get detailed model information

## Installation

1. Install Python dependencies:
```bash
cd magicavoxel-mcp
pip install -r requirements.txt
```

2. Configure the MCP server in your Cursor settings. 

   In Cursor, go to Settings → Features → Model Context Protocol, and add a new server configuration. You can use the example in `mcp-config-example.json` as a template.

   Update the paths in the configuration to match your system:
   - `args`: Full path to `server.py`
   - `VOX_DIR`: Path to your MagicaVoxel `vox/` directory
   - `EXPORT_DIR`: Path to your MagicaVoxel `export/` directory

   Example configuration:
```json
{
  "mcpServers": {
    "magicavoxel": {
      "command": "python",
      "args": [
        "C:/Users/Ropbe/Desktop/MagicaVoxel-0.99.7.2-win64/magicavoxel-mcp/server.py"
      ],
      "env": {
        "VOX_DIR": "C:/Users/Ropbe/Desktop/MagicaVoxel-0.99.7.2-win64/vox",
        "EXPORT_DIR": "C:/Users/Ropbe/Desktop/MagicaVoxel-0.99.7.2-win64/export"
      }
    }
  }
}
```

## Usage

Once configured, you can use natural language prompts like:

**Basic Operations:**
- "Create a new voxel model called 'my_model' with dimensions 20x20x20"
- "Place a voxel at coordinates (10, 10, 10) with color index 1 in my_model"
- "Fill a box from (0,0,0) to (5,5,5) with color index 2 in my_model"
- "List all available voxel models"
- "Show me information about the castle.vox model"

**Shape Generation:**
- "Create a blue sphere at (15, 15, 15) with radius 8 in my_model"
- "Create a red cylinder at (10, 0, 10) with radius 5 and height 20 in my_model"
- "Create a yellow pyramid at (0, 0, 0) with base 10x10 and height 15 in my_model"

**Patterns:**
- "Create stairs starting at (0, 0, 0) with 10 steps, width 5, depth 3 in my_model"
- "Create a wall at (0, 0, 0) with length 20, height 10 in my_model"

**Advanced:**
- "Replace all color 1 voxels with color 4 in my_model"
- "Set palette color 5 to RGB(255, 128, 0) in my_model"
- "Count how many voxels of each color are in my_model"
- "Copy the region from (0,0,0) to (5,5,5) to (10,10,10) in my_model"

## Tools Available

### Basic Operations
- `create_voxel_model` - Create a new empty voxel model with specified dimensions
- `read_voxel_model` - Read and inspect a .vox file structure
- `place_voxel` - Place a single voxel at specific coordinates
- `remove_voxel` - Remove a voxel at specific coordinates
- `get_voxel` - Get the color index of a voxel at specific coordinates
- `fill_box` - Fill a rectangular region with voxels
- `clear_region` - Remove all voxels in a rectangular region
- `list_models` - List all .vox files in the vox directory
- `get_model_info` - Get detailed information about a model (dimensions, voxel count, etc.)
- `delete_model` - Delete a .vox file from the vox directory
- `copy_model` - Copy a .vox file to a new filename

### Shape Generation
- `create_sphere` - Create a sphere at specified center with given radius (solid or hollow)
- `create_cylinder` - Create a cylinder with specified radius, height, and axis direction
- `create_pyramid` - Create a pyramid with rectangular base (solid or hollow)
- `create_torus` - Create a torus (donut) shape
- `create_cone` - Create a cone shape

### Pattern Generation
- `create_stairs` - Create a staircase with specified number of steps
- `create_wall` - Create a wall structure in X or Z direction

### Transform Operations
- `copy_region` - Copy a region of voxels to another location in the same model
- `move_region` - Move a region to a new location (translates voxels)
- `rotate_region` - Rotate a region 90, 180, or 270 degrees around an axis
- `mirror_region` - Mirror a region across a plane
- `extrude_region` - Extrude a region in a direction

### Color & Palette Operations
- `replace_color` - Replace all voxels of one color with another color
- `set_palette_color` - Set a specific color in the model's palette (RGB values)
- `get_palette` - Get all palette colors from a model
- `count_colors` - Count voxels by color index in a model

### Model Management
- `merge_models` - Combine two models into one with optional offset

### Analysis Tools
- `find_connected_components` - Find all separate connected pieces in a model
- `get_surface_voxels` - Get all surface (exposed) voxels in a model

### Intelligence Features (Optional)
- `smart_create_model` - Intelligently create a voxel model with template support
- `get_suggestions` - Get intelligent suggestions for next operations
- `list_templates` - List available templates for model creation
- `get_operation_stats` - Get statistics about operations performed

## File Structure

The server works directly with .vox files in the configured `vox/` directory. Changes are saved immediately and can be opened in MagicaVoxel.

## Notes

- **Color indices**: Range from 0-255 and correspond to MagicaVoxel's palette. Index 0 is transparent.
- **Coordinates**: Use (X, Y, Z) format where:
  - X: Width (left-right)
  - Y: Height (vertical, up-down)
  - Z: Depth (front-back)
- **Model limits**: MagicaVoxel supports models up to 256×256×256 voxels
- **File format**: The server implements basic .vox file reading/writing. Complex features like materials and animations may require manual editing in MagicaVoxel.

## Troubleshooting

- If models don't appear in MagicaVoxel, make sure the `VOX_DIR` path is correct
- Ensure Python 3.8+ is installed and accessible via the `python` command
- Check that the MCP server is enabled in Cursor settings
- Models created programmatically will use a default palette; you can customize colors in MagicaVoxel
