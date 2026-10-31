"""
Utility functions for working with .vox files
Handles reading, writing, and manipulating MagicaVoxel .vox format
"""

import os
import struct
import tempfile
from collections import deque
from typing import List, Tuple, Optional, Dict
from pathlib import Path

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# A .vox model is at most 256 voxels along each axis; coordinates are 0-255.
GRID = 256
NEIGHBORS = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
# Most voxels one model or one fill may hold (e.g. 256x128x128); a full 256^3 grid would need ~2 GB
MAX_VOXELS = 1 << 22


def _span(a: int, b: int) -> range:
    """Inclusive range between a and b, clamped to the grid"""
    return range(max(0, min(a, b)), min(GRID - 1, max(a, b)) + 1)


def _check_volume(*spans: range):
    volume = len(spans[0]) * len(spans[1]) * len(spans[2])
    if volume > MAX_VOXELS:
        raise ValueError(f"Region of {volume} voxels is larger than the {MAX_VOXELS} allowed in one operation")


def _check_color(color_index: int):
    if not 0 <= color_index <= 255:
        raise ValueError(f"Color index {color_index} is outside 0-255")


class VoxelModel:
    """Represents a voxel model. Z is up, matching MagicaVoxel."""

    def __init__(self, size_x: int = 0, size_y: int = 0, size_z: int = 0):
        for size in (size_x, size_y, size_z):
            if not 0 <= size <= GRID:
                raise ValueError(f"Model size {size} is outside 0-{GRID}")
        self.size_x = size_x
        self.size_y = size_y
        self.size_z = size_z
        self.voxels: dict[Tuple[int, int, int], int] = {}  # (x, y, z) -> color_index
        # palette[i] is the colour of index i; palette[0] is unused (empty)
        self.palette = self._default_palette()
        # Non-zero when edits since loading dropped voxels outside the grid (a count where known)
        self.clipped = 0
        # Chunk layout from the file this model was read from (see read_vox_file)
        self.version = 150
        self.layout: list = ["MODEL", "RGBA"]
        self.model_count = 1
        # The RGBA chunk's 256th entry maps to no colour index; kept so files round-trip exactly
        self.spare_rgba = bytes(4)
        # SIZE as read from the file, and how far edits have moved the voxels since
        # (new = old + shift); used to keep a scene's placement when the size changes
        self.loaded_size: Optional[Tuple[int, int, int]] = None
        self.loaded_count = 0
        self.shift = (0, 0, 0)

    def file_size(self) -> Tuple[int, int, int]:
        """The SIZE written to the file: the declared size grown to fit the voxels, at least 1"""
        bounds = self.get_bounds()
        declared = (self.size_x, self.size_y, self.size_z)
        return tuple(max(1, min(GRID, max(declared[i], bounds[i]))) for i in range(3))

    def _default_palette(self) -> List[Tuple[int, int, int, int]]:
        """Default palette (RGBA)"""
        # Index 0 is empty
        palette = [(0, 0, 0, 0)]
        # Add some basic colors
        basic_colors = [
            (255, 255, 255, 255),  # White
            (255, 0, 0, 255),      # Red
            (0, 255, 0, 255),      # Green
            (0, 0, 255, 255),      # Blue
            (255, 255, 0, 255),    # Yellow
            (255, 0, 255, 255),    # Magenta
            (0, 255, 255, 255),    # Cyan
        ]
        palette.extend(basic_colors)
        # Fill rest with grayscale
        for i in range(8, 256):
            gray = i % 256
            palette.append((gray, gray, gray, 255))
        return palette
    
    def set_voxel(self, x: int, y: int, z: int, color_index: int):
        """Set a voxel at position (x, y, z) with color index; 0 removes it.
        Positions outside the 0-255 grid are dropped and counted in self.clipped."""
        _check_color(color_index)
        if 0 <= x < GRID and 0 <= y < GRID and 0 <= z < GRID:
            if color_index > 0:
                if len(self.voxels) >= MAX_VOXELS and (x, y, z) not in self.voxels:
                    raise ValueError(f"Model would exceed {MAX_VOXELS} voxels")
                self.voxels[(x, y, z)] = color_index
            elif (x, y, z) in self.voxels:
                del self.voxels[(x, y, z)]
        elif color_index > 0:
            self.clipped += 1
    
    def get_voxel(self, x: int, y: int, z: int) -> int:
        """Get color index at position (x, y, z), returns 0 if empty"""
        return self.voxels.get((x, y, z), 0)
    
    def remove_voxel(self, x: int, y: int, z: int):
        """Remove a voxel at position (x, y, z)"""
        if (x, y, z) in self.voxels:
            del self.voxels[(x, y, z)]
    
    def fill_box(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, color_index: int):
        """Fill a box region with voxels"""
        xs, ys, zs = self._clamp_box((x1, y1, z1), (x2, y2, z2), color_index)
        for x in xs:
            for y in ys:
                for z in zs:
                    self.set_voxel(x, y, z, color_index)

    def _clamp_box(self, lo, hi, color_index: int = 1) -> Tuple[range, range, range]:
        """Clamp an inclusive box to the grid, noting in self.clipped when it is cut"""
        spans = tuple(_span(lo[i], hi[i]) for i in range(3))
        _check_volume(*spans)
        full = 1
        for i in range(3):
            full *= abs(hi[i] - lo[i]) + 1
        if color_index > 0 and full > len(spans[0]) * len(spans[1]) * len(spans[2]):
            self.clipped += full - len(spans[0]) * len(spans[1]) * len(spans[2])
        return spans

    def _region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int) -> Dict[Tuple[int, int, int], int]:
        """Voxels inside an inclusive box"""
        lo = (min(x1, x2), min(y1, y2), min(z1, z2))
        hi = (max(x1, x2), max(y1, y2), max(z1, z2))
        return {pos: c for pos, c in self.voxels.items()
                if all(lo[i] <= pos[i] <= hi[i] for i in range(3))}
    
    def get_voxel_count(self) -> int:
        """Get total number of voxels"""
        return len(self.voxels)
    
    def get_bounds(self) -> Tuple[int, int, int]:
        """Get actual bounds of the model"""
        if not self.voxels:
            return (0, 0, 0)
        xs = [x for x, y, z in self.voxels.keys()]
        ys = [y for x, y, z in self.voxels.keys()]
        zs = [z for x, y, z in self.voxels.keys()]
        return (max(xs) + 1, max(ys) + 1, max(zs) + 1)

    def get_extent(self) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """Inclusive (min, max) corners of the occupied voxels"""
        keys = self.voxels.keys()
        lo = tuple(min(p[i] for p in keys) for i in range(3))
        hi = tuple(max(p[i] for p in keys) for i in range(3))
        return lo, hi

    def _fill_shape(self, lo, hi, inside, color_index: int, hollow: bool):
        """Set every voxel in the inclusive box lo..hi for which inside(x, y, z) holds.
        Hollow keeps only those with a face-neighbour outside the shape. If the box is
        cut by the grid edge, self.clipped notes it (each shape reaches its box's edges)."""
        # The grid bounds the loop; set_voxel enforces MAX_VOXELS on what is kept
        spans = tuple(_span(lo[i], hi[i]) for i in range(3))
        if any(len(spans[i]) < hi[i] - lo[i] + 1 for i in range(3)):
            self.clipped += 1
        for x in spans[0]:
            for y in spans[1]:
                for z in spans[2]:
                    if not inside(x, y, z):
                        continue
                    if hollow and all(inside(x + dx, y + dy, z + dz) for dx, dy, dz in NEIGHBORS):
                        continue
                    self.set_voxel(x, y, z, color_index)
    
    def create_sphere(self, center_x: int, center_y: int, center_z: int, radius: int, color_index: int, hollow: bool = False):
        """Create a sphere at the specified center with given radius"""
        radius_sq = radius * radius
        def inside(x, y, z):
            return (x - center_x) ** 2 + (y - center_y) ** 2 + (z - center_z) ** 2 <= radius_sq
        self._fill_shape((center_x - radius, center_y - radius, center_z - radius),
                         (center_x + radius, center_y + radius, center_z + radius),
                         inside, color_index, hollow)
    
    def _fill_along_axis(self, origin: Tuple[int, int, int], axis: str, length: int, reach: int,
                         inside_local, color_index: int, hollow: bool):
        """Fill a shape described in local (along, u, v) coordinates, where along runs
        0..length-1 from origin on the axis and u, v run -reach..reach across it."""
        if axis not in ('x', 'y', 'z'):
            raise ValueError(f"Axis must be 'x', 'y' or 'z', not {axis!r}")
        ox, oy, oz = origin
        along = {'x': 0, 'y': 1, 'z': 2}[axis]
        across = [i for i in range(3) if i != along]
        lo, hi = [0, 0, 0], [0, 0, 0]
        lo[along], hi[along] = origin[along], origin[along] + length - 1
        for i in across:
            lo[i], hi[i] = origin[i] - reach, origin[i] + reach
        def inside(x, y, z):
            d = (x - ox, y - oy, z - oz)
            return inside_local(d[along], d[across[0]], d[across[1]])
        self._fill_shape(lo, hi, inside, color_index, hollow)

    def create_cylinder(self, center_x: int, center_y: int, center_z: int, radius: int, height: int,
                       axis: str = 'z', color_index: int = 1, hollow: bool = False):
        """Create a cylinder rising from its base centre along the axis ('x', 'y' or 'z')"""
        radius_sq = radius * radius
        def inside(a, u, v):
            return 0 <= a < height and u * u + v * v <= radius_sq
        self._fill_along_axis((center_x, center_y, center_z), axis, height, radius,
                              inside, color_index, hollow)

    def create_pyramid(self, base_x: int, base_y: int, base_z: int, base_width: int, base_depth: int,
                     height: int, color_index: int = 1, hollow: bool = False):
        """Create a pyramid rising along +Z from a base corner; width runs along X, depth along Y.
        Each layer is a rectangle centred on the base, shrinking linearly towards the tip."""
        def inside(x, y, z):
            layer = z - base_z
            if not 0 <= layer < height:
                return False
            current_width = max(1, int(base_width * (1 - layer / height)))
            current_depth = max(1, int(base_depth * (1 - layer / height)))
            x0 = base_x + (base_width - current_width) // 2
            y0 = base_y + (base_depth - current_depth) // 2
            return x0 <= x < x0 + current_width and y0 <= y < y0 + current_depth
        self._fill_shape((base_x, base_y, base_z),
                         (base_x + base_width - 1, base_y + base_depth - 1, base_z + height - 1),
                         inside, color_index, hollow)

    def replace_color(self, old_color: int, new_color: int):
        """Replace all voxels of one color with another (0 removes them). Returns the count."""
        _check_color(new_color)
        matches = [p for p, c in self.voxels.items() if c == old_color]
        for pos in matches:
            self.set_voxel(*pos, new_color)
        return len(matches)

    def set_palette_color(self, color_index: int, r: int, g: int, b: int, a: int = 255):
        """Set a specific palette color"""
        if not 1 <= color_index <= 255:
            raise ValueError(f"Palette index {color_index} is outside 1-255")
        for component in (r, g, b, a):
            if not 0 <= component <= 255:
                raise ValueError(f"Colour component {component} is outside 0-255")
        self.palette[color_index] = (r, g, b, a)
    
    def count_colors(self) -> dict:
        """Count voxels by color index"""
        color_counts = {}
        for color_idx in self.voxels.values():
            color_counts[color_idx] = color_counts.get(color_idx, 0) + 1
        return color_counts
    
    def copy_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, 
                   target_x: int, target_y: int, target_z: int, overwrite: bool = True):
        """Copy a region to another location"""
        source_voxels = self._region(x1, y1, z1, x2, y2, z2)

        # Calculate offset
        offset_x = target_x - min(x1, x2)
        offset_y = target_y - min(y1, y2)
        offset_z = target_z - min(z1, z2)
        
        # Copy voxels
        for (x, y, z), color_idx in source_voxels.items():
            new_x = x + offset_x
            new_y = y + offset_y
            new_z = z + offset_z
            if overwrite or (new_x, new_y, new_z) not in self.voxels:
                self.set_voxel(new_x, new_y, new_z, color_idx)
    
    def create_stairs(self, start_x: int, start_y: int, start_z: int, width: int, depth: int, 
                     num_steps: int, step_height: int = 1, color_index: int = 1):
        """Create a staircase"""
        for step in range(num_steps):
            step_y = start_y + (step * step_height)
            step_z = start_z + (step * depth)
            self.fill_box(start_x, step_y, step_z, 
                         start_x + width - 1, step_y + step_height - 1, step_z + depth - 1, 
                         color_index)
    
    def create_wall(self, start_x: int, start_y: int, start_z: int, length: int, height: int, 
                   direction: str = 'x', thickness: int = 1, color_index: int = 1):
        """Create a wall. Direction can be 'x' or 'z'"""
        if direction == 'x':
            self.fill_box(start_x, start_y, start_z, 
                         start_x + length - 1, start_y + height - 1, start_z + thickness - 1, 
                         color_index)
        else:  # direction == 'z'
            self.fill_box(start_x, start_y, start_z, 
                         start_x + thickness - 1, start_y + height - 1, start_z + length - 1, 
                         color_index)
    
    def clear_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int):
        """Remove all voxels in a box region"""
        for pos in self._region(x1, y1, z1, x2, y2, z2):
            del self.voxels[pos]

    def create_torus(self, center_x: int, center_y: int, center_z: int,
                     major_radius: int, minor_radius: int,
                     axis: str = 'z', color_index: int = 1, hollow: bool = False):
        """Create a torus (donut). Major radius is distance from center to tube center,
        minor radius is tube radius. The ring lies across the axis ('x', 'y' or 'z')."""
        minor_r_sq = minor_radius * minor_radius
        max_r = major_radius + minor_radius
        def inside(a, u, v):
            ring = (u * u + v * v) ** 0.5 - major_radius
            return ring * ring + (a - minor_radius) ** 2 <= minor_r_sq
        # The fill runs along the axis from its origin, so start one tube radius below the centre
        origin = [center_x, center_y, center_z]
        origin[{'x': 0, 'y': 1, 'z': 2}.get(axis, 2)] -= minor_radius
        self._fill_along_axis(tuple(origin), axis, 2 * minor_radius + 1, max_r,
                              inside, color_index, hollow)

    def create_cone(self, base_x: int, base_y: int, base_z: int,
                    base_radius: int, height: int,
                    axis: str = 'z', color_index: int = 1, hollow: bool = False):
        """Create a cone rising from its base centre along the axis ('x', 'y' or 'z')"""
        def inside(a, u, v):
            if not 0 <= a < height:
                return False
            radius = max(1, int(base_radius * (1 - a / height)))
            return u * u + v * v <= radius * radius
        self._fill_along_axis((base_x, base_y, base_z), axis, height, base_radius,
                              inside, color_index, hollow)

    def rotate_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                      center_x: int, center_y: int, center_z: int,
                      axis: str, degrees: int):
        """Rotate a region around a center point. Degrees: 90, 180, or 270."""
        if axis not in ('x', 'y', 'z') or degrees not in (90, 180, 270):
            raise ValueError("Rotation needs axis 'x', 'y' or 'z' and degrees 90, 180 or 270")
        region_voxels = self._region(x1, y1, z1, x2, y2, z2)

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
                else:
                    continue
            elif axis == 'y':
                if degrees == 90:
                    new_x, new_y, new_z = dz, dy, -dx
                elif degrees == 180:
                    new_x, new_y, new_z = -dx, dy, -dz
                elif degrees == 270:
                    new_x, new_y, new_z = -dz, dy, dx
                else:
                    continue
            else:  # axis == 'z'
                if degrees == 90:
                    new_x, new_y, new_z = -dy, dx, dz
                elif degrees == 180:
                    new_x, new_y, new_z = -dx, -dy, dz
                elif degrees == 270:
                    new_x, new_y, new_z = dy, -dx, dz
                else:
                    continue
            
            # Translate back
            new_x += center_x
            new_y += center_y
            new_z += center_z
            
            self.set_voxel(new_x, new_y, new_z, color)
    
    def mirror_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                     plane: str, position: float):
        """Mirror a region across a plane. Plane: 'x', 'y', or 'z'. Position is the plane
        coordinate; use a .5 position (e.g. 4.5) to mirror between two voxel layers."""
        if plane not in ('x', 'y', 'z'):
            raise ValueError(f"Plane must be 'x', 'y' or 'z', not {plane!r}")
        if (2 * position) % 1:
            raise ValueError("Mirror position must be a whole or half voxel coordinate")
        region_voxels = self._region(x1, y1, z1, x2, y2, z2)

        for (x, y, z), color in region_voxels.items():
            if plane == 'x':
                new_x = int(2 * position - x)
                new_y, new_z = y, z
            elif plane == 'y':
                new_y = int(2 * position - y)
                new_x, new_z = x, z
            else:  # plane == 'z'
                new_z = int(2 * position - z)
                new_x, new_y = x, y

            self.set_voxel(new_x, new_y, new_z, color)
    
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
    
    def subtract_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int):
        """Remove all voxels in a region (boolean subtract)"""
        self.clear_region(x1, y1, z1, x2, y2, z2)
    
    def union_with_model(self, other_model: 'VoxelModel', offset_x: int = 0, offset_y: int = 0, offset_z: int = 0):
        """Combine this model with another model (boolean union)"""
        for (x, y, z), color in other_model.voxels.items():
            self.set_voxel(x + offset_x, y + offset_y, z + offset_z, color)
    
    def intersect_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int):
        """Keep only voxels within the specified region (boolean intersect)"""
        to_remove = []
        for (x, y, z) in self.voxels.keys():
            if not (min(x1, x2) <= x <= max(x1, x2) and
                    min(y1, y2) <= y <= max(y1, y2) and
                    min(z1, z2) <= z <= max(z1, z2)):
                to_remove.append((x, y, z))
        for pos in to_remove:
            del self.voxels[pos]
    
    def scale_model(self, factor_x: float = 1.0, factor_y: float = 1.0, factor_z: float = 1.0):
        """Scale the model by factors (can be non-uniform). Each voxel becomes the block of
        target voxels it covers, so scaling up leaves no gaps."""
        if factor_x <= 0 or factor_y <= 0 or factor_z <= 0:
            raise ValueError("Scale factors must be greater than 0")
        if factor_x == 1.0 and factor_y == 1.0 and factor_z == 1.0:
            return

        def block(c: int, f: float) -> range:
            start = int(c * f)
            return range(start, max(start + 1, int((c + 1) * f)))

        old_voxels = self.voxels
        self.voxels = {}
        for (x, y, z), color in old_voxels.items():
            for nx in block(x, factor_x):
                for ny in block(y, factor_y):
                    for nz in block(z, factor_z):
                        self.set_voxel(nx, ny, nz, color)

        self.size_x = min(GRID, int(self.size_x * factor_x))
        self.size_y = min(GRID, int(self.size_y * factor_y))
        self.size_z = min(GRID, int(self.size_z * factor_z))

    def dilate(self, iterations: int = 1):
        """Dilate: expand surface voxels outward (adds layers)"""
        for _ in range(iterations):
            additions = {}
            for (x, y, z), color in self.voxels.items():
                for dx, dy, dz in NEIGHBORS:
                    neighbor = (x + dx, y + dy, z + dz)
                    if neighbor not in self.voxels:
                        additions[neighbor] = color
            for pos, color in additions.items():
                self.set_voxel(*pos, color)

    def erode(self, iterations: int = 1):
        """Erode: remove surface voxels (shrinks model)"""
        for _ in range(iterations):
            for pos in self.get_surface_voxels():
                del self.voxels[pos]

    def flood_fill(self, color_index: int = 1):
        """Fill all enclosed hollow spaces with a color"""
        if not 1 <= color_index <= 255:
            raise ValueError("flood_fill needs a color index from 1 to 255")
        if not self.voxels:
            return

        # Flood the empty space outside the model from a box one voxel larger than it;
        # every empty cell the flood can't reach is enclosed.
        lo, hi = self.get_extent()
        lo = tuple(c - 1 for c in lo)
        hi = tuple(c + 1 for c in hi)
        _check_volume(*(range(lo[i], hi[i] + 1) for i in range(3)))
        outside = {lo}
        queue = deque([lo])
        while queue:
            x, y, z = queue.popleft()
            for dx, dy, dz in NEIGHBORS:
                n = (x + dx, y + dy, z + dz)
                if (n not in outside and n not in self.voxels
                        and all(lo[i] <= n[i] <= hi[i] for i in range(3))):
                    outside.add(n)
                    queue.append(n)

        for x in range(lo[0] + 1, hi[0]):
            for y in range(lo[1] + 1, hi[1]):
                for z in range(lo[2] + 1, hi[2]):
                    if (x, y, z) not in self.voxels and (x, y, z) not in outside:
                        self.set_voxel(x, y, z, color_index)

    def shell(self):
        """Remove all interior voxels, keep only surface (hull)"""
        surface = self.get_surface_voxels()
        surface_set = set(surface)
        to_remove = [pos for pos in self.voxels.keys() if pos not in surface_set]
        for pos in to_remove:
            del self.voxels[pos]
    
    def invert(self):
        """Invert: swap solid and empty space within the occupied bounding box"""
        if not self.voxels:
            return
        lo, hi = self.get_extent()
        _check_volume(*(range(lo[i], hi[i] + 1) for i in range(3)))
        new_voxels = {}
        for x in range(lo[0], hi[0] + 1):
            for y in range(lo[1], hi[1] + 1):
                for z in range(lo[2], hi[2] + 1):
                    if (x, y, z) not in self.voxels:
                        # Was empty, make solid (use color 1)
                        new_voxels[(x, y, z)] = 1
                    # Was solid, becomes empty (don't add)
        self.voxels = new_voxels
    
    def shrink(self):
        """Resize the model to fit its voxels: move them to the origin and trim empty space"""
        if not self.voxels:
            self.size_x = self.size_y = self.size_z = 0
            return

        lo, hi = self.get_extent()
        self.voxels = {(x - lo[0], y - lo[1], z - lo[2]): c for (x, y, z), c in self.voxels.items()}
        self.shift = tuple(self.shift[i] - lo[i] for i in range(3))
        self.size_x, self.size_y, self.size_z = (hi[i] - lo[i] + 1 for i in range(3))
    
    def repeat_pattern(self, count_x: int = 1, count_y: int = 1, count_z: int = 1, mirror: bool = False):
        """Repeat/tile the model pattern across axes"""
        if count_x == 1 and count_y == 1 and count_z == 1:
            return
        if not self.voxels:
            return

        lo, hi = self.get_extent()
        tile = tuple(hi[i] - lo[i] + 1 for i in range(3))
        original_voxels = dict(self.voxels)
        # Tiles that start past the grid edge can't place anything
        fits = [-(-(GRID - lo[i]) // tile[i]) for i in range(3)]

        for tx in range(min(count_x, fits[0])):
            for ty in range(min(count_y, fits[1])):
                for tz in range(min(count_z, fits[2])):
                    if tx == 0 and ty == 0 and tz == 0:
                        continue  # Skip original

                    for (x, y, z), color in original_voxels.items():
                        pos = [x, y, z]
                        for i, t in enumerate((tx, ty, tz)):
                            if mirror and t % 2 == 1:
                                # Mirror on odd repetitions
                                pos[i] = lo[i] + hi[i] - pos[i]
                            pos[i] += t * tile[i]
                        self.set_voxel(*pos, color)

        bounds = self.get_bounds()
        self.size_x, self.size_y, self.size_z = bounds
    
    def apply_noise(self, seed: int = 0, min_val: float = 0.0, max_val: float = 1.0) -> int:
        """Nudge voxel colour indices at random: each voxel draws a value in
        [min_val, max_val], and values above 0.5 raise its index by (value - 0.5) * 10.
        Returns how many voxels changed colour."""
        import random
        random.seed(seed)

        changed = 0
        for (x, y, z) in list(self.voxels.keys()):
            noise_val = random.uniform(min_val, max_val)
            if noise_val > 0.5:  # Threshold for applying noise
                current_color = self.voxels[(x, y, z)]
                new_color = max(1, min(255, int(current_color + (noise_val - 0.5) * 10)))
                if new_color != current_color:
                    self.voxels[(x, y, z)] = new_color
                    changed += 1
        return changed
    
    def randomize_colors(self, min_index: int = 1, max_index: int = 255):
        """Randomize voxel colors within palette range"""
        import random
        if not 1 <= min_index <= max_index <= 255:
            raise ValueError("Need 1 <= min_index <= max_index <= 255")
        for (x, y, z) in self.voxels.keys():
            self.voxels[(x, y, z)] = random.randint(min_index, max_index)
    
    def optimize_palette(self) -> int:
        """Move the colours the model uses to indices 1..N, in their current order, and the
        unused ones after them. Voxels, palette and MagicaVoxel materials (MATL, keyed by
        index) are renumbered together, so nothing changes appearance. Refused for files with
        several models, which share the palette. Returns N."""
        if self.model_count > 1:
            raise ValueError("optimize_palette would recolour the file's other models, which share its palette")
        used = sorted(set(self.voxels.values()))
        order = used + [i for i in range(1, 256) if i not in set(used)]
        new_index = {old: new for new, old in enumerate(order, start=1)}

        self.voxels = {pos: new_index[c] for pos, c in self.voxels.items()}
        self.palette = [self.palette[0]] + [self.palette[old] for old in order]
        layout = []
        for item in self.layout:
            if isinstance(item, bytes) and item[:4] == b'MATL':
                material = struct.unpack_from('<i', item, 12)[0]
                if material in new_index:
                    item = item[:12] + struct.pack('<i', new_index[material]) + item[16:]
            layout.append(item)
        self.layout = layout
        return len(used)
    
    def extrude_region(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                       direction: str, distance: int, color_index: Optional[int] = None):
        """Extrude a region in a direction. Direction: 'x+', 'x-', 'y+', 'y-', 'z+', 'z-'"""
        offsets = {'x+': (1, 0, 0), 'x-': (-1, 0, 0), 'y+': (0, 1, 0),
                   'y-': (0, -1, 0), 'z+': (0, 0, 1), 'z-': (0, 0, -1)}
        if direction not in offsets:
            raise ValueError(f"Direction must be one of {', '.join(offsets)}, not {direction!r}")
        offset = offsets[direction]
        original_voxels = self._region(x1, y1, z1, x2, y2, z2)

        # Extrude; nothing past the grid edge can land, so stop there
        for step in range(min(distance, GRID)):
            for (x, y, z), color in list(original_voxels.items()):
                new_x = x + offset[0] * (step + 1)
                new_y = y + offset[1] * (step + 1)
                new_z = z + offset[2] * (step + 1)
                use_color = color_index if color_index is not None else color
                self.set_voxel(new_x, new_y, new_z, use_color)


def _chunk(chunk_id: bytes, content: bytes, children: bytes = b"") -> bytes:
    """Encode one .vox chunk: id, content size, children size, content, children"""
    return chunk_id + struct.pack('<II', len(content), len(children)) + content + children


def read_vox_file(filepath: Path) -> VoxelModel:
    """Read a .vox file and return a VoxelModel.

    Only the first model in the file is loaded for editing. Every other chunk (further
    models, the scene graph, layers, materials, cameras) is kept as raw bytes in
    model.layout, and write_vox_file puts it back unchanged. A file without an RGBA
    chunk gets this module's default palette, not MagicaVoxel's."""
    data = Path(filepath).read_bytes()
    if data[:4] != b'VOX ':
        raise ValueError("Invalid .vox file format")
    version = struct.unpack_from('<I', data, 4)[0]
    if data[8:12] != b'MAIN':
        raise ValueError("Expected MAIN chunk")
    main_content = struct.unpack_from('<I', data, 12)[0]

    # MAIN's children run to the end of the file. Older versions of this server wrote
    # a wrong children size, so it isn't trusted.
    chunks = []
    pos = 20 + main_content
    while pos + 12 <= len(data):
        chunk_id = data[pos:pos + 4]
        n_content, n_children = struct.unpack_from('<II', data, pos + 4)
        end = pos + 12 + n_content + n_children
        if end > len(data):
            raise ValueError(f"Chunk {chunk_id!r} at byte {pos} runs past the end of the file")
        chunks.append((chunk_id, data[pos + 12:pos + 12 + n_content], data[pos:end]))
        pos = end

    model = None
    palette = None
    spare_rgba = bytes(4)
    layout = []
    model_count = 0
    i = 0
    while i < len(chunks):
        chunk_id, content, raw = chunks[i]
        if chunk_id == b'SIZE':
            model_count += 1
        if chunk_id == b'SIZE' and model is None:
            if i + 1 >= len(chunks) or chunks[i + 1][0] != b'XYZI':
                raise ValueError("SIZE chunk is not followed by XYZI")
            size_x, size_y, size_z = struct.unpack_from('<III', content)
            model = VoxelModel(min(size_x, GRID), min(size_y, GRID), min(size_z, GRID))
            xyzi = chunks[i + 1][1]
            num_voxels = struct.unpack_from('<I', xyzi)[0]
            for j in range(num_voxels):
                x, y, z, color_index = xyzi[4 + 4 * j:8 + 4 * j]
                if color_index:
                    model.voxels[(x, y, z)] = color_index
            layout.append("MODEL")
            i += 2
            continue
        if chunk_id == b'RGBA':
            # RGBA entry i holds the colour of index i + 1
            entries = [tuple(content[4 * k:4 * k + 4]) for k in range(256)]
            palette = [(0, 0, 0, 0)] + entries[:255]
            spare_rgba = content[1020:1024]
            layout.append("RGBA")
        else:
            layout.append(raw)
        i += 1

    if model is None:
        raise ValueError("No model (SIZE and XYZI chunks) in file")
    if palette is not None:
        model.palette = palette
    model.spare_rgba = spare_rgba
    model.loaded_size = (model.size_x, model.size_y, model.size_z)
    model.loaded_count = len(model.voxels)
    model.version = version
    model.layout = layout
    model.model_count = model_count
    return model


def check_connection(model: VoxelModel, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int) -> tuple[bool, Optional[tuple[int, int, int]]]:
    """Check if a box region connects to existing voxels.
    Returns (connects, nearest_point) where nearest_point is the closest existing voxel if not connected."""
    connects = False
    nearest_point = None
    min_distance = float('inf')
    
    # Check all positions in the box
    for x in range(min(x1, x2), max(x1, x2) + 1):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for z in range(min(z1, z2), max(z1, z2) + 1):
                # Check 6 neighbors
                for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                    neighbor = (x+dx, y+dy, z+dz)
                    if neighbor in model.voxels:
                        connects = True
                        return (True, None)
                    # Track nearest existing voxel
                    for existing_pos in model.voxels:
                        dist = abs(x - existing_pos[0]) + abs(y - existing_pos[1]) + abs(z - existing_pos[2])
                        if dist < min_distance:
                            min_distance = dist
                            nearest_point = existing_pos
    
    return (connects, nearest_point)


def detect_gaps(model: VoxelModel, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int) -> list[int]:
    """Detect gaps in Y direction between the box and existing parts.
    Returns list of Y coordinates where gaps exist."""
    gaps = []
    
    # Get Y range of the box
    box_y_min = min(y1, y2)
    box_y_max = max(y1, y2)
    
    # Check for gaps above the box
    if model.voxels:
        existing_y_max = max(y for (x, y, z) in model.voxels if x1 <= x <= x2 and z1 <= z <= z2)
        if existing_y_max < box_y_min - 1:
            # Gap detected
            for gap_y in range(existing_y_max + 1, box_y_min):
                gaps.append(gap_y)
    
    # Check for gaps below the box
    if model.voxels:
        existing_y_min = min(y for (x, y, z) in model.voxels if x1 <= x <= x2 and z1 <= z <= z2)
        if existing_y_min > box_y_max + 1:
            # Gap detected
            for gap_y in range(box_y_max + 1, existing_y_min):
                gaps.append(gap_y)
    
    return gaps


def calculate_human_proportions(total_height: int, style: str = "standard") -> Dict[str, int]:
    """Calculate proper human body proportions based on the 8-heads-tall rule.
    
    Args:
        total_height: Total height of the character in voxels
        style: "standard" (8 heads), "minecraft" (Minecraft player), "heroic" (9 heads), "chibi" (4-5 heads)
    
    Returns:
        Dictionary with body part dimensions in voxels
    """
    if style == "minecraft":
        # Minecraft player: ~1.875 blocks tall, but model is 32 voxels
        # Head: 8 voxels, Torso: 12, Legs: 12
        head_height = max(1, total_height // 4)  # Head is 1/4 of height in Minecraft
        neck_height = max(1, total_height // 32)
        torso_height = max(1, total_height * 3 // 8)
        leg_height = max(1, total_height * 3 // 8)
        arm_length = max(1, total_height * 3 // 8)
    elif style == "heroic":
        # Heroic proportions: 9 heads tall
        head_height = max(1, total_height // 9)
        neck_height = max(1, total_height // 36)
        torso_height = max(1, total_height * 3 // 9)
        leg_height = max(1, total_height * 4 // 9)
        arm_length = max(1, total_height * 3 // 9)
    elif style == "chibi":
        # Chibi/cute style: 4-5 heads tall
        head_height = max(1, total_height // 4)
        neck_height = max(1, total_height // 20)
        torso_height = max(1, total_height // 4)
        leg_height = max(1, total_height // 4)
        arm_length = max(1, total_height // 4)
    else:  # standard
        # Standard human: 8 heads tall
        head_height = max(1, total_height // 8)
        neck_height = max(1, total_height // 32)
        torso_height = max(1, total_height * 3 // 8)  # 3 heads
        leg_height = max(1, total_height // 2)  # 4 heads
        arm_length = max(1, total_height * 3 // 8)  # 3 heads
    
    return {
        'head': head_height,
        'neck': neck_height,
        'torso': torso_height,
        'legs': leg_height,
        'arms': arm_length,
        'total': total_height
    }


def calculate_minecraft_proportions() -> Dict[str, float]:
    """Calculate Minecraft-specific proportions based on official measurements.
    
    Returns:
        Dictionary with Minecraft measurements in blocks/meters
    """
    return {
        'player_height_standing': 1.8,  # blocks (1.8 meters)
        'player_height_sneaking': 1.5,  # blocks
        'player_height_swimming': 0.6,  # blocks
        'player_width': 0.6,  # blocks
        'eye_height_standing': 1.62,  # meters above base
        'eye_height_sneaking': 1.27,  # meters above base
        'block_size': 1.0,  # 1 block = 1 meter
        'pixels_per_block': 16,  # texture resolution
        'meters_per_pixel': 0.0625,  # 1/16 meter per pixel
        'player_model_height_voxels': 32,  # standard Minecraft skin height
        'head_voxels': 8,
        'torso_voxels': 12,
        'legs_voxels': 12
    }


def check_proportions(model: VoxelModel, part_name: str, dimensions: Tuple[int, int, int], 
                     model_height: Optional[int] = None, style: str = "standard") -> Optional[str]:
    """Check if body part dimensions are proportional to the overall model.
    
    Args:
        model: The voxel model
        part_name: Name of the body part ("head", "torso", "legs", "arms", etc.)
        dimensions: (width, height, depth) of the part
        model_height: Total model height in voxels (if None, calculated from model)
        style: Proportion style ("standard", "minecraft", "heroic", "chibi")
    
    Returns:
        Warning string if disproportionate, None if OK
    """
    # Calculate model height if not provided
    if model_height is None:
        if not model.voxels:
            return None  # Can't check proportions of empty model
        all_y = [y for (x, y, z) in model.voxels.keys()]
        if not all_y:
            return None
        model_height = max(all_y) - min(all_y) + 1
    
    if model_height < 4:
        return None  # Too small to check proportions
    
    # Get expected proportions
    proportions = calculate_human_proportions(model_height, style)
    
    part_width, part_height, part_depth = dimensions
    
    # Check specific body parts
    if part_name.lower() == "head":
        expected_height = proportions['head']
        if part_height > expected_height * 1.5:
            return (f"Warning: {part_name} height ({part_height} voxels) is too large. "
                   f"Expected ~{expected_height} voxels for {model_height}-voxel {style} character "
                   f"({part_height/expected_height:.1f}x expected size).")
        elif part_height < expected_height * 0.5:
            return (f"Warning: {part_name} height ({part_height} voxels) is too small. "
                   f"Expected ~{expected_height} voxels for {model_height}-voxel {style} character.")
    
    elif part_name.lower() == "torso":
        expected_height = proportions['torso']
        if part_height > expected_height * 1.5:
            return (f"Warning: {part_name} height ({part_height} voxels) is too large. "
                   f"Expected ~{expected_height} voxels for {model_height}-voxel {style} character.")
        elif part_height < expected_height * 0.5:
            return (f"Warning: {part_name} height ({part_height} voxels) is too small. "
                   f"Expected ~{expected_height} voxels for {model_height}-voxel {style} character.")
    
    elif part_name.lower() in ["legs", "leg"]:
        expected_height = proportions['legs']
        if part_height > expected_height * 1.5:
            return (f"Warning: {part_name} height ({part_height} voxels) is too large. "
                   f"Expected ~{expected_height} voxels for {model_height}-voxel {style} character.")
        elif part_height < expected_height * 0.5:
            return (f"Warning: {part_name} height ({part_height} voxels) is too small. "
                   f"Expected ~{expected_height} voxels for {model_height}-voxel {style} character.")
    
    elif part_name.lower() in ["arms", "arm"]:
        expected_length = proportions['arms']
        # For arms, check the longest dimension (could be width, height, or depth)
        max_dim = max(part_width, part_height, part_depth)
        if max_dim > expected_length * 1.5:
            return (f"Warning: {part_name} length ({max_dim} voxels) is too long. "
                   f"Expected ~{expected_length} voxels for {model_height}-voxel {style} character.")
        elif max_dim < expected_length * 0.5:
            return (f"Warning: {part_name} length ({max_dim} voxels) is too short. "
                   f"Expected ~{expected_length} voxels for {model_height}-voxel {style} character.")
    
    return None  # Proportions are OK


def suggest_proportions(model_height: int, style: str = "standard") -> Dict[str, Dict[str, int]]:
    """Suggest proper proportions for a character model.
    
    Args:
        model_height: Total height of the character in voxels
        style: Proportion style ("standard", "minecraft", "heroic", "chibi")
    
    Returns:
        Dictionary with suggested dimensions for each body part
    """
    proportions = calculate_human_proportions(model_height, style)
    
    return {
        'head': {
            'height': proportions['head'],
            'width': proportions['head'],
            'depth': proportions['head'],
            'radius': proportions['head'] // 2
        },
        'neck': {
            'height': proportions['neck'],
            'width': max(1, proportions['head'] * 2 // 3),
            'depth': max(1, proportions['head'] * 2 // 3)
        },
        'torso': {
            'height': proportions['torso'],
            'width': max(1, proportions['head'] * 2),
            'depth': max(1, proportions['head'] * 1.5)
        },
        'legs': {
            'height': proportions['legs'],
            'width': max(1, proportions['head'] * 1.5),
            'depth': max(1, proportions['head'] * 1.5)
        },
        'arms': {
            'length': proportions['arms'],
            'width': max(1, proportions['head'] * 3 // 4),
            'depth': max(1, proportions['head'] * 3 // 4)
        }
    }


def suggest_connection_fix(model: VoxelModel, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int) -> Optional[str]:
    """Suggest how to fix a connection issue.
    Returns a suggestion string or None if no fix needed."""
    connects, nearest = check_connection(model, x1, y1, z1, x2, y2, z2)
    
    if connects:
        return None
    
    if nearest:
        nx, ny, nz = nearest
        # Suggest adjusting coordinates to connect
        if abs(nx - x1) < abs(nx - x2):
            if x1 < nx:
                return f"Adjust x1 to {nx} to connect to nearest part at ({nx},{ny},{nz})"
            else:
                return f"Adjust x2 to {nx} to connect to nearest part at ({nx},{ny},{nz})"
        else:
            if x2 < nx:
                return f"Adjust x1 to {nx} to connect to nearest part at ({nx},{ny},{nz})"
            else:
                return f"Adjust x2 to {nx} to connect to nearest part at ({nx},{ny},{nz})"
    
    return "No existing parts found to connect to"


def validate_item_size(model: VoxelModel, item_type: str = "item") -> List[str]:
    """Validate item dimensions against Minecraft scale.
    
    Args:
        model: The voxel model to validate
        item_type: Type of item ("item", "weapon", "tool", "container", etc.)
    
    Returns:
        List of warning strings (empty if no issues)
    """
    warnings = []
    
    if not model.voxels:
        return warnings
    
    bounds = model.get_bounds()
    width, height, depth = bounds[0], bounds[1], bounds[2]
    mc = calculate_minecraft_proportions()
    player_height = mc['player_height_standing']
    
    # Check height relative to player
    if height > player_height * 2:
        warnings.append(f"Item is very tall ({height} voxels = {height/player_height:.1f}x player height). "
                       f"Most items should be 1-2 blocks tall.")
    elif height < 2:
        warnings.append(f"Item is very short ({height} voxels). Consider if this is intentional.")
    
    # Check for thin items (likely 2D sprites, but might be unintentional)
    if width < 3 and depth < 3:
        warnings.append(f"Item is very thin ({width}x{depth} cross-section). "
                       f"This might be intended for a 2D sprite, but consider adding depth.")
    
    # Check aspect ratio
    max_dim = max(width, height, depth)
    min_dim = min(width, height, depth)
    if max_dim > 0 and min_dim > 0:
        aspect_ratio = max_dim / min_dim
        if aspect_ratio > 10:
            warnings.append(f"Item has extreme aspect ratio ({aspect_ratio:.1f}:1). "
                           f"Consider if this is intentional for the item type.")
    
    return warnings


def validate_item_connectivity(model: VoxelModel) -> List[str]:
    """Check if all parts of an item are connected.
    
    Returns:
        List of warning strings about disconnected components
    """
    warnings = []
    
    if not model.voxels:
        return warnings
    
    components = model.find_connected_components()
    
    if len(components) > 1:
        warnings.append(f"Item has {len(components)} disconnected pieces (should be 1).")
        
        # Find the main component (largest)
        main_component = max(components, key=lambda c: c['voxel_count'])
        main_size = main_component['voxel_count']
        
        # Report small disconnected pieces
        small_pieces = [c for c in components if c['voxel_count'] < main_size * 0.1 and c['voxel_count'] < 5]
        if small_pieces:
            warnings.append(f"Found {len(small_pieces)} small disconnected pieces that might be accidental.")
            for i, piece in enumerate(small_pieces, 1):
                b = piece['bounds']
                warnings.append(f"  Small piece {i}: {piece['voxel_count']} voxels at "
                              f"({b['min_x']},{b['min_y']},{b['min_z']})")
    
    return warnings


def validate_item_density(model: VoxelModel) -> List[str]:
    """Check voxel density and suggest improvements.
    
    Returns:
        List of suggestion strings
    """
    suggestions = []
    
    if not model.voxels:
        return suggestions
    
    bounds = model.get_bounds()
    width, height, depth = bounds[0], bounds[1], bounds[2]
    total_volume = width * height * depth
    voxel_count = len(model.voxels)
    
    if total_volume == 0:
        return suggestions
    
    density = voxel_count / total_volume
    
    # For items, very low density might indicate missing details
    if density < 0.1 and voxel_count > 10:
        suggestions.append(f"Low voxel density ({density:.1%}). "
                          f"Consider adding more detail or filling hollow spaces.")
    elif density > 0.9:
        suggestions.append(f"Very high density ({density:.1%}). "
                          f"Item might be too solid - consider hollowing for efficiency.")
    
    return suggestions


def write_vox_file(filepath: Path, model: VoxelModel):
    """Write a VoxelModel to a .vox file.

    The file is validated and built in memory, written to a temporary file next to the
    target and then moved over it, so a failure never leaves a half-written model.
    Returns a note for the user when the model may appear moved in its scene, else None."""
    for (x, y, z), color_index in model.voxels.items():
        if not (0 <= x < GRID and 0 <= y < GRID and 0 <= z < GRID):
            raise ValueError(f"Voxel ({x}, {y}, {z}) is outside the 0-255 grid")
        if not 1 <= color_index <= 255:
            raise ValueError(f"Voxel ({x}, {y}, {z}) has color index {color_index}, outside 1-255")
    if len(model.palette) != 256:
        raise ValueError(f"Palette has {len(model.palette)} entries, expected 256")

    size = model.file_size()
    layout, note = _keep_scene_placement(model, size)

    model_chunks = (
        _chunk(b'SIZE', struct.pack('<III', *size))
        + _chunk(b'XYZI', struct.pack('<I', len(model.voxels)) + b''.join(
            struct.pack('<4B', x, y, z, c) for (x, y, z), c in model.voxels.items()))
    )
    # RGBA entry i holds the colour of index i + 1; the 256th entry maps to no index
    rgba_chunk = _chunk(b'RGBA', b''.join(
        struct.pack('<4B', *model.palette[i]) for i in range(1, 256)) + model.spare_rgba)

    children = []
    for item in layout:
        if item == "MODEL":
            children.append(model_chunks)
        elif item == "RGBA":
            children.append(rgba_chunk)
        else:
            children.append(item)
    if "RGBA" not in layout:
        children.append(rgba_chunk)
    data = b'VOX ' + struct.pack('<I', model.version) + _chunk(b'MAIN', b'', b''.join(children))

    filepath = Path(filepath)
    fd, tmp_path = tempfile.mkstemp(dir=filepath.parent, prefix=f".{filepath.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.replace(tmp_path, filepath)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return note


def _read_string(buf: bytes, pos: int) -> Tuple[str, int]:
    length = struct.unpack_from('<i', buf, pos)[0]
    # latin-1 maps every byte, so unknown text round-trips exactly
    return buf[pos + 4:pos + 4 + length].decode('latin-1'), pos + 4 + length


def _read_dict(buf: bytes, pos: int) -> Tuple[Dict[str, str], int]:
    count = struct.unpack_from('<i', buf, pos)[0]
    pos += 4
    result = {}
    for _ in range(count):
        key, pos = _read_string(buf, pos)
        result[key], pos = _read_string(buf, pos)
    return result, pos


def _pack_dict(values: Dict[str, str]) -> bytes:
    out = struct.pack('<i', len(values))
    for key, value in values.items():
        for text in (key, value):
            encoded = text.encode('latin-1')
            out += struct.pack('<i', len(encoded)) + encoded
    return out


def _rotate(packed: int, v: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Apply a .vox packed rotation (an nTRN frame's _r) to a vector. Bits 0-1 and 2-3 give
    the column of the non-zero entry in rows 0 and 1; bits 4-6 make rows 0-2 negative."""
    columns = (packed & 3, (packed >> 2) & 3)
    columns += (3 - columns[0] - columns[1],)
    signs = [-1 if packed >> bit & 1 else 1 for bit in (4, 5, 6)]
    return tuple(signs[row] * v[columns[row]] for row in range(3))


def _keep_scene_placement(model: VoxelModel, size: Tuple[int, int, int]) -> Tuple[list, Optional[str]]:
    """MagicaVoxel places a model in its scene by the model's centre, size // 2. When the
    first model's size changed, or its voxels were moved (model.shift), move the transforms
    that place it by the same amount, so its voxels stay where they were in the scene.
    Returns the layout to write and a note for the user, if any."""
    if model.loaded_size is None:
        return model.layout, None
    delta = tuple(size[i] // 2 - model.loaded_size[i] // 2 - model.shift[i] for i in range(3))
    if delta == (0, 0, 0):
        return model.layout, None

    try:
        # Shape nodes that show model 0, and whether model 0 is one frame of an animation
        shapes, animated = set(), False
        for item in model.layout:
            if isinstance(item, bytes) and item[:4] == b'nSHP':
                node_id = struct.unpack_from('<i', item, 12)[0]
                _, pos = _read_dict(item, 16)
                count = struct.unpack_from('<i', item, pos)[0]
                pos += 4
                model_ids = []
                for _ in range(count):
                    model_ids.append(struct.unpack_from('<i', item, pos)[0])
                    _, pos = _read_dict(item, pos + 4)
                if 0 in model_ids:
                    shapes.add(node_id)
                    animated |= count > 1
        if animated:
            return model.layout, ("The first model is one frame of an animation; its size changed, "
                                  "so this frame may appear shifted against the others in MagicaVoxel")
        if not shapes:
            return model.layout, None

        layout = []
        for item in model.layout:
            if isinstance(item, bytes) and item[:4] == b'nTRN':
                n_content = struct.unpack_from('<I', item, 4)[0]
                node_id = struct.unpack_from('<i', item, 12)[0]
                attributes, pos = _read_dict(item, 16)
                child, reserved, layer, num_frames = struct.unpack_from('<iiii', item, pos)
                if child in shapes:
                    pos += 16
                    frames = []
                    for _ in range(num_frames):
                        frame, pos = _read_dict(item, pos)
                        offset = _rotate(int(frame.get('_r', '4')), delta)
                        t = [int(c) for c in frame.get('_t', '0 0 0').split()]
                        frame['_t'] = ' '.join(str(t[i] + offset[i]) for i in range(3))
                        frames.append(frame)
                    content = (struct.pack('<i', node_id) + _pack_dict(attributes)
                               + struct.pack('<iiii', child, reserved, layer, num_frames)
                               + b''.join(_pack_dict(frame) for frame in frames))
                    item = _chunk(b'nTRN', content, item[12 + n_content:])
            layout.append(item)
        return layout, None
    except (struct.error, ValueError):
        return model.layout, ("Couldn't read the file's scene graph to keep the model in place; "
                              "it may appear shifted in MagicaVoxel")


def render_model_to_image(model: VoxelModel, angle: str, output_path: Path) -> bool:
    """
    Render an orthographic view of a voxel model, Z up.

    Args:
        model: The VoxelModel to render
        angle: One of 'front' (from -Y), 'back' (+Y), 'left' (-X), 'right' (+X),
               'top' (+Z) or 'bottom' (-Z)
        output_path: Path to save the image

    Returns:
        True if successful, False otherwise
    """
    if not PIL_AVAILABLE:
        return False

    if not model.voxels:
        return False

    (x0, y0, z0), (x1, y1, z1) = model.get_extent()

    # Each view maps a voxel to (column, row, depth); the smallest depth is nearest the camera
    views = {
        "front": (x1 - x0 + 1, z1 - z0 + 1, lambda x, y, z: (x - x0, z1 - z, y)),
        "back": (x1 - x0 + 1, z1 - z0 + 1, lambda x, y, z: (x1 - x, z1 - z, -y)),
        "left": (y1 - y0 + 1, z1 - z0 + 1, lambda x, y, z: (y1 - y, z1 - z, x)),
        "right": (y1 - y0 + 1, z1 - z0 + 1, lambda x, y, z: (y - y0, z1 - z, -x)),
        "top": (x1 - x0 + 1, y1 - y0 + 1, lambda x, y, z: (x - x0, y1 - y, -z)),
        "bottom": (x1 - x0 + 1, y1 - y0 + 1, lambda x, y, z: (x1 - x, y1 - y, z)),
    }
    if angle not in views:
        return False
    width, height, project = views[angle]

    nearest = {}  # (column, row) -> (depth, color_index)
    for (x, y, z), color_index in model.voxels.items():
        column, row, depth = project(x, y, z)
        key = (column, row)
        if key not in nearest or depth < nearest[key][0]:
            nearest[key] = (depth, color_index)

    # Shade by depth so holes and recesses show: the farthest surface is drawn at 45% brightness
    depths = [d for d, _ in nearest.values()]
    near, span = min(depths), (max(depths) - min(depths)) or 1

    # Draw one pixel per voxel, then scale up so small models are visible
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    pixels = img.load()
    for (column, row), (depth, color_index) in nearest.items():
        r, g, b, a = model.palette[color_index]
        light = 1 - 0.55 * (depth - near) / span
        pixels[column, row] = (int(r * light), int(g * light), int(b * light), a)
    scale = max(1, 256 // max(width, height))
    img = img.resize((width * scale, height * scale), Image.NEAREST)

    try:
        img.save(output_path, 'PNG')
        return True
    except Exception:
        return False


def render_model_all_angles(model: VoxelModel, base_output_path: Path) -> Dict[str, Path]:
    """
    Render a voxel model to images from all 6 angles.
    
    Args:
        model: The VoxelModel to render
        base_output_path: Base path (without extension) for output images
    
    Returns:
        Dictionary mapping angle names to output file paths
    """
    angles = ["front", "back", "left", "right", "top", "bottom"]
    results = {}
    
    for angle in angles:
        output_path = base_output_path.parent / f"{base_output_path.stem}_{angle}.png"
        if render_model_to_image(model, angle, output_path):
            results[angle] = output_path
    
    return results
