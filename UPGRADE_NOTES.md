# MagicaVoxel MCP Server - Upgrade Notes

## Version 3.0 - Major Expansion (15 New Tools)

The MCP server has been significantly expanded with 15 new tools across 4 phases, bringing the total to 34 tools. This upgrade adds file management, additional shapes, transform operations, and analysis capabilities.

## Version 2.0 - Enhanced Features

The MCP server was upgraded with powerful new capabilities for voxel model creation and manipulation.

## New Features Added

### 🎨 Shape Generation Tools
1. **create_sphere** - Generate spheres (solid or hollow)
   - Parameters: center coordinates, radius, color, hollow option
   - Perfect for creating balls, orbs, and rounded objects

2. **create_cylinder** - Generate cylinders
   - Parameters: center, radius, height, axis direction (x/y/z), color, hollow option
   - Great for pillars, tubes, and cylindrical structures

3. **create_pyramid** - Generate pyramids
   - Parameters: base position, width, depth, height, color, hollow option
   - Useful for creating roofs, monuments, and angular structures

### 🏗️ Pattern Generation Tools
4. **create_stairs** - Generate staircases
   - Parameters: start position, width, depth, number of steps, step height, color
   - Automatically creates stepped structures

5. **create_wall** - Generate walls
   - Parameters: start position, length, height, direction (x/z), thickness, color
   - Perfect for building structures and boundaries

### 🎨 Color Management Tools
6. **replace_color** - Replace all voxels of one color with another
   - Quick way to recolor entire models or regions
   - Useful for theme changes and color adjustments

7. **set_palette_color** - Set custom RGB colors in the palette
   - Define exact colors for your models
   - Full control over color appearance

8. **count_colors** - Analyze color distribution
   - Count how many voxels use each color
   - Useful for model analysis and optimization

### 🔧 Advanced Operations
9. **copy_region** - Copy voxel regions within a model
   - Duplicate structures and patterns
   - Supports overwrite control

## Usage Examples

### Creating a Castle
```
1. Create base model: create_voxel_model("castle", 50, 30, 50)
2. Create walls: create_wall("castle", 0, 0, 0, 50, 20, "x", 2, 1)
3. Create towers: create_cylinder("castle", 10, 0, 10, 5, 25, "y", 1)
4. Create roof: create_pyramid("castle", 20, 20, 20, 10, 10, 8, 2)
5. Create entrance stairs: create_stairs("castle", 20, 0, 0, 10, 5, 5, 1, 1)
```

### Creating a Character
```
1. Create base: create_voxel_model("character", 10, 20, 10)
2. Create body: create_cylinder("character", 5, 5, 5, 3, 10, "y", 1)
3. Create head: create_sphere("character", 5, 15, 5, 3, 1)
4. Create arms: create_cylinder("character", 2, 8, 5, 1, 6, "x", 1)
5. Customize colors: set_palette_color("character", 1, 255, 200, 150) # Skin tone
```

## Technical Details

### New Methods in VoxelModel Class
- `create_sphere()` - Sphere generation algorithm
- `create_cylinder()` - Cylinder generation with axis support
- `create_pyramid()` - Pyramid generation with tapering
- `replace_color()` - Color replacement operation
- `set_palette_color()` - Palette customization
- `count_colors()` - Color analysis
- `copy_region()` - Region copying with offset calculation
- `create_stairs()` - Staircase generation
- `create_wall()` - Wall generation with direction support

### Performance
- All operations are optimized for real-time use
- Efficient algorithms for shape generation
- Minimal memory overhead

## Backward Compatibility

All existing tools and functionality remain unchanged. The upgrade is fully backward compatible with existing workflows.

## Next Steps

Try the new features:
1. Create a model with `create_voxel_model`
2. Add shapes using `create_sphere`, `create_cylinder`, or `create_pyramid`
3. Build structures with `create_stairs` and `create_wall`
4. Customize colors with `set_palette_color` and `replace_color`
5. Analyze your models with `count_colors`

Enjoy the enhanced MCP server!

---

## Version 3.0 - Major Expansion

### Phase 1: Quick Wins (5 New Tools)

1. **remove_voxel** - Explicitly remove a voxel at coordinates
   - Clearer than placing color 0
   - Simple and intuitive operation

2. **get_voxel** - Read the color index of a single voxel
   - Inspect individual voxels
   - Useful for validation and debugging

3. **get_palette** - Retrieve all palette colors from a model
   - See what colors are available
   - Inspect color definitions

4. **delete_model** - Delete a .vox file from disk
   - File management operation
   - Clean up unused models

5. **copy_model** - Duplicate a .vox file to a new filename
   - Create backups
   - Duplicate models for variations

### Phase 2: Useful Shapes (3 New Tools)

6. **create_torus** - Create a torus (donut) shape
   - Parameters: center, major radius, minor radius, axis, color, hollow option
   - Perfect for rings, wheels, and toroidal structures

7. **create_cone** - Create a cone shape
   - Parameters: base position, base radius, height, axis, color, hollow option
   - Great for roofs, trees, and pointed structures

8. **clear_region** - Delete all voxels in a box region
   - Remove sections of models
   - Clean up regions efficiently

### Phase 3: Advanced Operations (4 New Tools)

9. **merge_models** - Combine two models into one
   - Parameters: two source files, target file, optional offsets
   - Perfect for building complex scenes from components
   - Supports overwrite control

10. **rotate_region** - Rotate a region 90/180/270 degrees
    - Parameters: region bounds, rotation center, axis, degrees
    - Transform existing structures
    - Supports all three axes

11. **mirror_region** - Mirror/flip a region across a plane
    - Parameters: region bounds, plane (x/y/z), position
    - Create symmetrical structures
    - Useful for character modeling

12. **move_region** - Translate a region to a new location
    - Parameters: source region, target position
    - Reposition structures within models
    - Combines copy and clear operations

### Phase 4: Analysis Tools (3 New Tools)

13. **find_connected_components** - Find separate pieces in a model
    - Identifies disconnected parts
    - Returns voxel count and bounding box for each component
    - Useful for model analysis and validation

14. **get_surface_voxels** - Find all exposed voxels
    - Identifies outer surface of models
    - Useful for rendering optimization
    - Returns count of surface vs total voxels

15. **extrude_region** - Extend a region in a direction
    - Parameters: region bounds, direction (x+/x-/y+/y-/z+/z-), distance
    - Extend shapes in any direction
    - Optional color override

## Usage Examples

### File Management
```
1. Copy a model: copy_model("warrior", "warrior_backup")
2. Get palette: get_palette("warrior")
3. Delete old version: delete_model("warrior_old")
```

### Advanced Shapes
```
1. Create torus: create_torus("model", 10, 10, 10, 8, 3, "y", 1)
2. Create cone: create_cone("model", 5, 0, 5, 4, 10, "y", 1)
3. Clear region: clear_region("model", 0, 0, 0, 5, 5, 5)
```

### Transform Operations
```
1. Rotate region: rotate_region("model", 0,0,0, 5,5,5, 2,2,2, "y", 90)
2. Mirror region: mirror_region("model", 0,0,0, 5,5,5, "x", 5)
3. Move region: move_region("model", 0,0,0, 3,3,3, 10,10,10)
4. Extrude region: extrude_region("model", 0,0,0, 3,3,3, "y+", 5)
```

### Model Combination
```
1. Merge models: merge_models("head", "body", "character", 0, 10, 0)
2. Combine scenes: merge_models("building1", "building2", "city", 20, 0, 0)
```

### Analysis
```
1. Find components: find_connected_components("model")
2. Get surface: get_surface_voxels("model")
```

## Technical Details

### New Methods in VoxelModel Class
- `remove_voxel()` - Voxel removal
- `clear_region()` - Region clearing
- `create_torus()` - Torus generation with axis support
- `create_cone()` - Cone generation with axis support
- `rotate_region()` - 3D rotation transformation
- `mirror_region()` - Reflection transformation
- `find_connected_components()` - Graph traversal algorithm
- `get_surface_voxels()` - Surface detection
- `extrude_region()` - Extrusion operation

### Performance
- All new operations are optimized for real-time use
- Transform operations use efficient coordinate calculations
- Analysis tools use BFS for connected components
- Minimal memory overhead for all operations

## Backward Compatibility

All existing tools and functionality remain unchanged. The upgrade is fully backward compatible with existing workflows. All 19 original tools continue to work exactly as before.

## Total Tool Count

- **Version 1.0:** 9 tools
- **Version 2.0:** 19 tools
- **Version 3.0:** 34 tools

## Next Steps

Try the new features:
1. Use file management tools to organize your models
2. Create torus and cone shapes for new structures
3. Experiment with transform operations (rotate, mirror, move)
4. Merge multiple models to build complex scenes
5. Analyze your models with the new analysis tools

Enjoy the expanded MCP server!