# MagicaVoxel MCP Server - Tool Expansion Implementation Plan

## Overview

This document outlines a comprehensive plan to expand the MagicaVoxel MCP server with 15 additional tools, organized into 4 phases based on implementation complexity and user value.

**Current State:** 19 tools  
**Target State:** 34 tools (after all phases)  
**Recommended Approach:** Implement incrementally, testing each phase before proceeding

---

## Phase 1: Quick Wins (High Value, Low Effort)

**Estimated Time:** 2-3 hours  
**Tools to Add:** 5  
**Complexity:** Low - Mostly exposing existing functionality or simple wrappers

### 1.1 remove_voxel

**Purpose:** Explicitly remove a voxel at specified coordinates (clearer than placing color 0)

**Implementation:**
- **VoxelModel Method:** Wrapper around existing `set_voxel(x, y, z, 0)`
- **Location:** `vox_utils.py` - Add new method
- **MCP Tool:** Add to `server.py` tool list and handler

**Code Changes:**

```python
# vox_utils.py - Add to VoxelModel class
def remove_voxel(self, x: int, y: int, z: int):
    """Remove a voxel at position (x, y, z)"""
    if (x, y, z) in self.voxels:
        del self.voxels[(x, y, z)]
```

**MCP Tool Schema:**
```python
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
)
```

**Handler Pattern:**
```python
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
```

**Testing:**
- Place voxel, then remove it, verify it's gone
- Try removing non-existent voxel (should not error)
- Test bounds checking

---

### 1.2 get_voxel

**Purpose:** Read the color index of a single voxel at specified coordinates

**Implementation:**
- **VoxelModel Method:** Already exists (`get_voxel()`), just expose it
- **Location:** `server.py` only

**MCP Tool Schema:**
```python
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
)
```

**Handler Pattern:**
```python
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
```

**Testing:**
- Get voxel that exists, verify correct color
- Get voxel that doesn't exist, should return 0
- Test with various coordinates

---

### 1.3 get_palette

**Purpose:** Retrieve all palette colors from a model

**Implementation:**
- **VoxelModel Method:** Expose existing `self.palette`
- **Location:** `server.py` only

**MCP Tool Schema:**
```python
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
)
```

**Handler Pattern:**
```python
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
```

**Testing:**
- Get palette from model with custom colors
- Verify all 256 colors are accessible
- Test with default palette

---

### 1.4 delete_model

**Purpose:** Delete a .vox file from disk

**Implementation:**
- **File Operation:** Use `os.remove()` or `Path.unlink()`
- **Location:** `server.py` only

**MCP Tool Schema:**
```python
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
)
```

**Handler Pattern:**
```python
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
```

**Testing:**
- Delete existing file, verify it's gone
- Try deleting non-existent file (should error gracefully)
- Test with intelligence tracking

---

### 1.5 copy_model

**Purpose:** Duplicate a .vox file to a new filename

**Implementation:**
- **File Operation:** Use `shutil.copy()` or read/write
- **Location:** `server.py` only

**MCP Tool Schema:**
```python
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
)
```

**Handler Pattern:**
```python
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
```

**Testing:**
- Copy existing file, verify both exist
- Try copying to existing file (should error)
- Verify copied file is identical

---

## Phase 2: Useful Shapes (Medium Effort)

**Estimated Time:** 4-6 hours  
**Tools to Add:** 3  
**Complexity:** Medium - New shape generation algorithms

### 2.1 create_torus

**Purpose:** Create a torus (donut) shape

**Implementation:**
- **VoxelModel Method:** New method in `vox_utils.py`
- **Algorithm:** Torus equation: (R - sqrt(x² + y²))² + z² ≤ r²

**Code Changes:**

```python
# vox_utils.py - Add to VoxelModel class
def create_torus(self, center_x: int, center_y: int, center_z: int, 
                 major_radius: int, minor_radius: int, 
                 axis: str = 'y', color_index: int = 1, hollow: bool = False):
    """Create a torus. Major radius is distance from center to tube center,
    minor radius is tube radius. Axis can be 'x', 'y', or 'z'."""
    major_r_sq = major_radius * major_radius
    minor_r_sq = minor_radius * minor_radius
    
    # Bounding box
    max_r = major_radius + minor_radius
    
    if axis == 'y':
        for x in range(center_x - max_r, center_x + max_r + 1):
            for y in range(center_y - minor_radius, center_y + minor_radius + 1):
                for z in range(center_z - max_r, center_z + max_r + 1):
                    dx = x - center_x
                    dz = z - center_z
                    dist_from_center = (dx*dx + dz*dz) ** 0.5
                    if dist_from_center == 0:
                        continue
                    
                    # Distance from torus center circle
                    dist_from_torus_center = abs(dist_from_center - major_radius)
                    dy = y - center_y
                    
                    dist_sq = dist_from_torus_center * dist_from_torus_center + dy * dy
                    
                    if hollow:
                        if abs(dist_sq - minor_r_sq) <= minor_radius:
                            self.set_voxel(x, y, z, color_index)
                    else:
                        if dist_sq <= minor_r_sq:
                            self.set_voxel(x, y, z, color_index)
    # Similar for 'x' and 'z' axes...
```

**MCP Tool Schema:**
```python
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
)
```

**Testing:**
- Create solid torus, verify shape
- Create hollow torus, verify surface only
- Test different axis orientations
- Test with various radius combinations

---

### 2.2 create_cone

**Purpose:** Create a cone shape

**Implementation:**
- **VoxelModel Method:** New method in `vox_utils.py`
- **Algorithm:** Similar to pyramid but with circular base

**Code Changes:**

```python
# vox_utils.py - Add to VoxelModel class
def create_cone(self, base_x: int, base_y: int, base_z: int,
                base_radius: int, height: int,
                axis: str = 'y', color_index: int = 1, hollow: bool = False):
    """Create a cone. Axis can be 'x', 'y', or 'z'."""
    if axis == 'y':
        for y in range(height):
            current_radius = int(base_radius * (1 - y / height))
            if current_radius < 1:
                current_radius = 1
            
            radius_sq = current_radius * current_radius
            
            for x in range(base_x - base_radius, base_x + base_radius + 1):
                for z in range(base_z - base_radius, base_z + base_radius + 1):
                    dx = x - base_x
                    dz = z - base_z
                    dist_sq = dx*dx + dz*dz
                    
                    if hollow and y < height - 1:
                        # Only surface
                        if abs(dist_sq - radius_sq) <= current_radius:
                            self.set_voxel(x, base_y + y, z, color_index)
                    else:
                        if dist_sq <= radius_sq:
                            self.set_voxel(x, base_y + y, z, color_index)
    # Similar for 'x' and 'z' axes...
```

**MCP Tool Schema:**
```python
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
)
```

**Testing:**
- Create solid cone, verify shape
- Create hollow cone, verify surface
- Test different axis orientations
- Test with various dimensions

---

### 2.3 clear_region

**Purpose:** Delete all voxels in a rectangular region

**Implementation:**
- **VoxelModel Method:** New method in `vox_utils.py`
- **Algorithm:** Loop through region and remove voxels

**Code Changes:**

```python
# vox_utils.py - Add to VoxelModel class
def clear_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int):
    """Remove all voxels in a box region"""
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for z in range(min(z1, z2), max(z1, z2) + 1):
                if (x, y, z) in self.voxels:
                    del self.voxels[(x, y, z)]
```

**MCP Tool Schema:**
```python
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
)
```

**Testing:**
- Clear region with voxels, verify they're removed
- Clear empty region (should not error)
- Clear entire model, verify it's empty
- Test bounds checking

---

## Phase 3: Advanced Operations (Higher Effort)

**Estimated Time:** 8-12 hours  
**Tools to Add:** 4  
**Complexity:** High - Complex transform algorithms

### 3.1 merge_models

**Purpose:** Combine two models into one

**Implementation:**
- **File Operation:** Read both models, combine voxels
- **Location:** `server.py` with helper in `vox_utils.py` if needed

**Code Changes:**

```python
# server.py - Handler only (or add helper to vox_utils.py)
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
        return [TextContent(type="text", text=f"Merged '{source1_filename}' and '{source2_filename}' into '{target_filename}'")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error merging models: {str(e)}")]
```

**MCP Tool Schema:**
```python
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
)
```

**Testing:**
- Merge two models, verify both are present
- Test with offsets
- Test overwrite vs no-overwrite
- Test with overlapping regions

---

### 3.2 rotate_region

**Purpose:** Rotate a region 90/180/270 degrees around an axis

**Implementation:**
- **VoxelModel Method:** New method in `vox_utils.py`
- **Algorithm:** 3D rotation matrix or coordinate transformation

**Code Changes:**

```python
# vox_utils.py - Add to VoxelModel class
def rotate_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                  center_x: int, center_y: int, center_z: int,
                  axis: str, degrees: int):
    """Rotate a region around a center point. Degrees: 90, 180, or 270."""
    # Extract region voxels
    region_voxels = {}
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for z in range(min(z1, z2), max(z1, z2) + 1):
                if (x, y, z) in self.voxels:
                    region_voxels[(x, y, z)] = self.voxels[(x, y, z)]
    
    # Clear original region
    for pos in region_voxels:
        del self.voxels[pos]
    
    # Rotate and place
    for (x, y, z), color in region_voxels.items():
        # Translate to origin
        dx = x - center_x
        dy = y - center_y
        dz = z - center_z
        
        # Rotate based on axis and degrees
        if axis == 'x':
            if degrees == 90:
                new_x, new_y, new_z = dx, -dz, dy
            elif degrees == 180:
                new_x, new_y, new_z = dx, -dy, -dz
            elif degrees == 270:
                new_x, new_y, new_z = dx, dz, -dy
        elif axis == 'y':
            if degrees == 90:
                new_x, new_y, new_z = dz, dy, -dx
            elif degrees == 180:
                new_x, new_y, new_z = -dx, dy, -dz
            elif degrees == 270:
                new_x, new_y, new_z = -dz, dy, dx
        else:  # axis == 'z'
            if degrees == 90:
                new_x, new_y, new_z = -dy, dx, dz
            elif degrees == 180:
                new_x, new_y, new_z = -dx, -dy, dz
            elif degrees == 270:
                new_x, new_y, new_z = dy, -dx, dz
        
        # Translate back
        new_x += center_x
        new_y += center_y
        new_z += center_z
        
        self.set_voxel(new_x, new_y, new_z, color)
```

**MCP Tool Schema:**
```python
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
)
```

**Testing:**
- Rotate simple shape, verify orientation
- Test all three axes
- Test all three angles
- Test with complex shapes

---

### 3.3 mirror_region

**Purpose:** Mirror/flip a region across a plane

**Implementation:**
- **VoxelModel Method:** New method in `vox_utils.py`
- **Algorithm:** Coordinate reflection

**Code Changes:**

```python
# vox_utils.py - Add to VoxelModel class
def mirror_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                  plane: str, position: int):
    """Mirror a region across a plane. Plane: 'x', 'y', or 'z'. Position is the plane coordinate."""
    # Extract region voxels
    region_voxels = {}
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for z in range(min(z1, z2), max(z1, z2) + 1):
                if (x, y, z) in self.voxels:
                    region_voxels[(x, y, z)] = self.voxels[(x, y, z)]
    
    # Mirror and place
    for (x, y, z), color in region_voxels.items():
        if plane == 'x':
            new_x = 2 * position - x
            new_y, new_z = y, z
        elif plane == 'y':
            new_y = 2 * position - y
            new_x, new_z = x, z
        else:  # plane == 'z'
            new_z = 2 * position - z
            new_x, new_y = x, y
        
        self.set_voxel(new_x, new_y, new_z, color)
```

**MCP Tool Schema:**
```python
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
)
```

**Testing:**
- Mirror simple shape, verify symmetry
- Test all three planes
- Test with complex shapes
- Verify original region is preserved

---

### 3.4 move_region

**Purpose:** Translate a region to a new location (copy + clear original)

**Implementation:**
- **VoxelModel Method:** Can use existing `copy_region` + `clear_region`
- **Location:** `server.py` handler that combines operations

**Code Changes:**

```python
# server.py - Handler only
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
```

**MCP Tool Schema:**
```python
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
)
```

**Testing:**
- Move region, verify it's in new location
- Verify original location is cleared
- Test with overlapping source/target
- Test bounds checking

---

## Phase 4: Analysis Tools (Complex)

**Estimated Time:** 10-15 hours  
**Tools to Add:** 3  
**Complexity:** Very High - Complex algorithms

### 4.1 find_connected_components

**Purpose:** Find separate pieces/components in a model

**Implementation:**
- **VoxelModel Method:** Graph traversal algorithm (BFS/DFS)
- **Algorithm:** Flood fill to find connected voxel groups

**Code Changes:**

```python
# vox_utils.py - Add to VoxelModel class
def find_connected_components(self) -> List[Dict]:
    """Find all connected components (separate pieces) in the model.
    Returns list of components, each with voxel count and bounding box."""
    visited = set()
    components = []
    
    for pos in self.voxels.keys():
        if pos in visited:
            continue
        
        # BFS to find connected component
        component_voxels = []
        queue = [pos]
        visited.add(pos)
        
        while queue:
            x, y, z = queue.pop(0)
            component_voxels.append((x, y, z))
            
            # Check 6 neighbors
            for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                neighbor = (x+dx, y+dy, z+dz)
                if neighbor in self.voxels and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        # Calculate bounding box
        xs = [x for x, y, z in component_voxels]
        ys = [y for x, y, z in component_voxels]
        zs = [z for x, y, z in component_voxels]
        
        components.append({
            "voxel_count": len(component_voxels),
            "bounds": {
                "min_x": min(xs), "max_x": max(xs),
                "min_y": min(ys), "max_y": max(ys),
                "min_z": min(zs), "max_z": max(zs)
            }
        })
    
    return components
```

**MCP Tool Schema:**
```python
Tool(
    name="find_connected_components",
    description="Find all separate connected pieces in a model",
    inputSchema={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "Name of the .vox file"}
        },
        "required": ["filename"]
    }
)
```

**Testing:**
- Model with one piece, should return 1 component
- Model with multiple separate pieces
- Complex model with many components
- Empty model (should return empty list)

---

### 4.2 get_surface_voxels

**Purpose:** Find all surface (exposed) voxels

**Implementation:**
- **VoxelModel Method:** Check 6-neighbor connectivity
- **Algorithm:** Voxel is surface if it has at least one empty neighbor

**Code Changes:**

```python
# vox_utils.py - Add to VoxelModel class
def get_surface_voxels(self) -> List[Tuple[int, int, int]]:
    """Get all surface voxels (voxels with at least one exposed face)"""
    surface = []
    for (x, y, z) in self.voxels.keys():
        # Check 6 neighbors
        is_surface = False
        for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
            neighbor = (x+dx, y+dy, z+dz)
            if neighbor not in self.voxels:
                is_surface = True
                break
        if is_surface:
            surface.append((x, y, z))
    return surface
```

**MCP Tool Schema:**
```python
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
)
```

**Testing:**
- Solid cube, all voxels should be surface
- Hollow cube, only outer voxels should be surface
- Complex shape, verify surface detection

---

### 4.3 extrude_region

**Purpose:** Extend a region in a direction

**Implementation:**
- **VoxelModel Method:** Copy region multiple times along direction
- **Algorithm:** Iterative copy with offset

**Code Changes:**

```python
# vox_utils.py - Add to VoxelModel class
def extrude_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                   direction: str, distance: int, color_index: Optional[int] = None):
    """Extrude a region in a direction. Direction: 'x+', 'x-', 'y+', 'y-', 'z+', 'z-'"""
    # Get original region
    original_voxels = {}
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for z in range(min(z1, z2), max(z1, z2) + 1):
                if (x, y, z) in self.voxels:
                    original_voxels[(x, y, z)] = self.voxels[(x, y, z)]
    
    # Determine offset direction
    if direction == 'x+':
        offset = (1, 0, 0)
    elif direction == 'x-':
        offset = (-1, 0, 0)
    elif direction == 'y+':
        offset = (0, 1, 0)
    elif direction == 'y-':
        offset = (0, -1, 0)
    elif direction == 'z+':
        offset = (0, 0, 1)
    else:  # 'z-'
        offset = (0, 0, -1)
    
    # Extrude
    for step in range(distance):
        for (x, y, z), color in list(original_voxels.items()):
            new_x = x + offset[0] * (step + 1)
            new_y = y + offset[1] * (step + 1)
            new_z = z + offset[2] * (step + 1)
            use_color = color_index if color_index is not None else color
            self.set_voxel(new_x, new_y, new_z, use_color)
```

**MCP Tool Schema:**
```python
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
            "color_index": {"type": "integer", "description": "Optional color override", "default": None}
        },
        "required": ["filename", "x1", "y1", "z1", "x2", "y2", "z2", "direction", "distance"]
    }
)
```

**Testing:**
- Extrude simple shape, verify extension
- Test all six directions
- Test with various distances
- Test with color override

---

## Implementation Checklist

### Phase 1: Quick Wins
- [ ] Implement `remove_voxel` in `vox_utils.py`
- [ ] Add `remove_voxel` tool to `server.py`
- [ ] Add `get_voxel` tool to `server.py`
- [ ] Add `get_palette` tool to `server.py`
- [ ] Add `delete_model` tool to `server.py`
- [ ] Add `copy_model` tool to `server.py`
- [ ] Test all Phase 1 tools
- [ ] Update documentation

### Phase 2: Useful Shapes
- [ ] Implement `create_torus` in `vox_utils.py`
- [ ] Add `create_torus` tool to `server.py`
- [ ] Implement `create_cone` in `vox_utils.py`
- [ ] Add `create_cone` tool to `server.py`
- [ ] Implement `clear_region` in `vox_utils.py`
- [ ] Add `clear_region` tool to `server.py`
- [ ] Test all Phase 2 tools
- [ ] Update documentation

### Phase 3: Advanced Operations
- [ ] Implement `merge_models` in `server.py`
- [ ] Implement `rotate_region` in `vox_utils.py`
- [ ] Add `rotate_region` tool to `server.py`
- [ ] Implement `mirror_region` in `vox_utils.py`
- [ ] Add `mirror_region` tool to `server.py`
- [ ] Implement `move_region` in `server.py`
- [ ] Test all Phase 3 tools
- [ ] Update documentation

### Phase 4: Analysis Tools
- [ ] Implement `find_connected_components` in `vox_utils.py`
- [ ] Add `find_connected_components` tool to `server.py`
- [ ] Implement `get_surface_voxels` in `vox_utils.py`
- [ ] Add `get_surface_voxels` tool to `server.py`
- [ ] Implement `extrude_region` in `vox_utils.py`
- [ ] Add `extrude_region` tool to `server.py`
- [ ] Test all Phase 4 tools
- [ ] Update documentation

---

## Testing Strategy

### Unit Testing
- Test each VoxelModel method independently
- Test edge cases (empty models, bounds, etc.)
- Test with various parameter combinations

### Integration Testing
- Test MCP tool handlers with real .vox files
- Test error handling (missing files, invalid parameters)
- Test intelligence layer integration (if available)

### Validation Testing
- Verify operations work correctly in MagicaVoxel
- Test with existing .vox files
- Test with models of various sizes

---

## Documentation Updates

### Files to Update
1. **README.md** - Add new tools to "Tools Available" section
2. **UPGRADE_NOTES.md** - Document new features by phase
3. **INTELLIGENCE_FEATURES.md** - Update if intelligence integration needed

### Documentation Format
For each new tool, document:
- Purpose and use case
- Parameters and defaults
- Example usage
- Related tools

---

## Best Practices

### Code Quality
- Follow existing patterns in `server.py` and `vox_utils.py`
- Use type hints for all functions
- Add docstrings to all new methods
- Keep tool descriptions concise (for context management)

### Error Handling
- Always check file existence
- Validate parameters before operations
- Return user-friendly error messages
- Use try/except blocks appropriately

### Performance
- Consider performance for large models
- Optimize algorithms where possible
- Cache model reads when multiple operations

### Context Management
- Keep tool descriptions under 200 characters when possible
- Group related tools together
- Monitor total tool count (aim for <35 tools)

---

## Timeline Estimate

- **Phase 1:** 2-3 hours (Quick wins)
- **Phase 2:** 4-6 hours (Shapes)
- **Phase 3:** 8-12 hours (Advanced)
- **Phase 4:** 10-15 hours (Analysis)

**Total:** 24-36 hours of development time

**Recommended Approach:** Implement one phase at a time, test thoroughly, then proceed to next phase.

---

## Notes

- All new tools should follow the existing async handler pattern
- Intelligence layer integration is optional but recommended
- Consider backward compatibility with existing workflows
- Test with real MagicaVoxel .vox files to ensure compatibility
- Monitor context size as tools are added

---

## Future Considerations

Potential additional tools for future phases:
- `scale_region` - Resize a region
- `create_ellipsoid` - Stretched sphere
- `smooth_surface` - Apply smoothing algorithm
- `add_noise` - Randomize voxels
- `create_pattern` - Tile pattern across region
- `colorize_region` - Apply color gradient
- `optimize_model` - Remove redundant data

These can be considered after completing the current 4 phases.
