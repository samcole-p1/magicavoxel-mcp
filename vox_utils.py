"""
Utility functions for working with .vox files
Handles reading, writing, and manipulating MagicaVoxel .vox format
"""

import struct
from typing import List, Tuple, Optional, Dict
from pathlib import Path


class VoxelModel:
    """Represents a voxel model"""
    
    def __init__(self, size_x: int = 0, size_y: int = 0, size_z: int = 0):
        self.size_x = size_x
        self.size_y = size_y
        self.size_z = size_z
        self.voxels: dict[Tuple[int, int, int], int] = {}  # (x, y, z) -> color_index
        self.palette = self._default_palette()
    
    def _default_palette(self) -> List[Tuple[int, int, int, int]]:
        """Default MagicaVoxel palette (RGBA)"""
        # First color is always transparent
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
        """Set a voxel at position (x, y, z) with color index"""
        # Allow placing voxels up to 255 (max for .vox format)
        # Don't restrict to model size since we want to support large models
        if 0 <= x <= 255 and 0 <= y <= 255 and 0 <= z <= 255:
            if color_index > 0:  # 0 is transparent
                self.voxels[(x, y, z)] = color_index
            elif (x, y, z) in self.voxels:
                del self.voxels[(x, y, z)]
    
    def get_voxel(self, x: int, y: int, z: int) -> int:
        """Get color index at position (x, y, z), returns 0 if empty"""
        return self.voxels.get((x, y, z), 0)
    
    def remove_voxel(self, x: int, y: int, z: int):
        """Remove a voxel at position (x, y, z)"""
        if (x, y, z) in self.voxels:
            del self.voxels[(x, y, z)]
    
    def fill_box(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, color_index: int):
        """Fill a box region with voxels"""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.set_voxel(x, y, z, color_index)
    
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
    
    def create_sphere(self, center_x: int, center_y: int, center_z: int, radius: int, color_index: int, hollow: bool = False):
        """Create a sphere at the specified center with given radius"""
        radius_sq = radius * radius
        for x in range(center_x - radius, center_x + radius + 1):
            for y in range(center_y - radius, center_y + radius + 1):
                for z in range(center_z - radius, center_z + radius + 1):
                    dx = x - center_x
                    dy = y - center_y
                    dz = z - center_z
                    dist_sq = dx*dx + dy*dy + dz*dz
                    
                    if hollow:
                        # Hollow sphere: only place voxels on the surface
                        if abs(dist_sq - radius_sq) <= radius:
                            self.set_voxel(x, y, z, color_index)
                    else:
                        # Solid sphere
                        if dist_sq <= radius_sq:
                            self.set_voxel(x, y, z, color_index)
    
    def create_cylinder(self, center_x: int, center_y: int, center_z: int, radius: int, height: int, 
                       axis: str = 'y', color_index: int = 1, hollow: bool = False):
        """Create a cylinder. Axis can be 'x', 'y', or 'z'"""
        radius_sq = radius * radius
        
        if axis == 'y':
            for y in range(center_y, center_y + height):
                for x in range(center_x - radius, center_x + radius + 1):
                    for z in range(center_z - radius, center_z + radius + 1):
                        dx = x - center_x
                        dz = z - center_z
                        dist_sq = dx*dx + dz*dz
                        if hollow:
                            if abs(dist_sq - radius_sq) <= radius:
                                self.set_voxel(x, y, z, color_index)
                        else:
                            if dist_sq <= radius_sq:
                                self.set_voxel(x, y, z, color_index)
        elif axis == 'x':
            for x in range(center_x, center_x + height):
                for y in range(center_y - radius, center_y + radius + 1):
                    for z in range(center_z - radius, center_z + radius + 1):
                        dy = y - center_y
                        dz = z - center_z
                        dist_sq = dy*dy + dz*dz
                        if hollow:
                            if abs(dist_sq - radius_sq) <= radius:
                                self.set_voxel(x, y, z, color_index)
                        else:
                            if dist_sq <= radius_sq:
                                self.set_voxel(x, y, z, color_index)
        else:  # axis == 'z'
            for z in range(center_z, center_z + height):
                for x in range(center_x - radius, center_x + radius + 1):
                    for y in range(center_y - radius, center_y + radius + 1):
                        dx = x - center_x
                        dy = y - center_y
                        dist_sq = dx*dx + dy*dy
                        if hollow:
                            if abs(dist_sq - radius_sq) <= radius:
                                self.set_voxel(x, y, z, color_index)
                        else:
                            if dist_sq <= radius_sq:
                                self.set_voxel(x, y, z, color_index)
    
    def create_pyramid(self, base_x: int, base_y: int, base_z: int, base_width: int, base_depth: int, 
                     height: int, color_index: int = 1, hollow: bool = False):
        """Create a pyramid with rectangular base"""
        for y in range(height):
            current_width = int(base_width * (1 - y / height))
            current_depth = int(base_depth * (1 - y / height))
            if current_width < 1:
                current_width = 1
            if current_depth < 1:
                current_depth = 1
            
            offset_x = (base_width - current_width) // 2
            offset_z = (base_depth - current_depth) // 2
            
            if hollow and y < height - 1:
                # Hollow: only outline
                for x in range(base_x + offset_x, base_x + offset_x + current_width):
                    self.set_voxel(x, base_y + y, base_z + offset_z, color_index)
                    self.set_voxel(x, base_y + y, base_z + offset_z + current_depth - 1, color_index)
                for z in range(base_z + offset_z, base_z + offset_z + current_depth):
                    self.set_voxel(base_x + offset_x, base_y + y, z, color_index)
                    self.set_voxel(base_x + offset_x + current_width - 1, base_y + y, z, color_index)
            else:
                # Solid: fill the layer
                for x in range(base_x + offset_x, base_x + offset_x + current_width):
                    for z in range(base_z + offset_z, base_z + offset_z + current_depth):
                        self.set_voxel(x, base_y + y, z, color_index)
    
    def replace_color(self, old_color: int, new_color: int):
        """Replace all voxels of one color with another"""
        for pos in list(self.voxels.keys()):
            if self.voxels[pos] == old_color:
                self.voxels[pos] = new_color
    
    def set_palette_color(self, color_index: int, r: int, g: int, b: int, a: int = 255):
        """Set a specific palette color"""
        if 0 <= color_index < 256:
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
        source_voxels = {}
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    if (x, y, z) in self.voxels:
                        source_voxels[(x, y, z)] = self.voxels[(x, y, z)]
        
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
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    if (x, y, z) in self.voxels:
                        del self.voxels[(x, y, z)]
    
    def create_torus(self, center_x: int, center_y: int, center_z: int, 
                     major_radius: int, minor_radius: int, 
                     axis: str = 'y', color_index: int = 1, hollow: bool = False):
        """Create a torus (donut). Major radius is distance from center to tube center,
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
        elif axis == 'x':
            for x in range(center_x - minor_radius, center_x + minor_radius + 1):
                for y in range(center_y - max_r, center_y + max_r + 1):
                    for z in range(center_z - max_r, center_z + max_r + 1):
                        dy = y - center_y
                        dz = z - center_z
                        dist_from_center = (dy*dy + dz*dz) ** 0.5
                        if dist_from_center == 0:
                            continue
                        
                        dist_from_torus_center = abs(dist_from_center - major_radius)
                        dx = x - center_x
                        
                        dist_sq = dist_from_torus_center * dist_from_torus_center + dx * dx
                        
                        if hollow:
                            if abs(dist_sq - minor_r_sq) <= minor_radius:
                                self.set_voxel(x, y, z, color_index)
                        else:
                            if dist_sq <= minor_r_sq:
                                self.set_voxel(x, y, z, color_index)
        else:  # axis == 'z'
            for x in range(center_x - max_r, center_x + max_r + 1):
                for y in range(center_y - max_r, center_y + max_r + 1):
                    for z in range(center_z - minor_radius, center_z + minor_radius + 1):
                        dx = x - center_x
                        dy = y - center_y
                        dist_from_center = (dx*dx + dy*dy) ** 0.5
                        if dist_from_center == 0:
                            continue
                        
                        dist_from_torus_center = abs(dist_from_center - major_radius)
                        dz = z - center_z
                        
                        dist_sq = dist_from_torus_center * dist_from_torus_center + dz * dz
                        
                        if hollow:
                            if abs(dist_sq - minor_r_sq) <= minor_radius:
                                self.set_voxel(x, y, z, color_index)
                        else:
                            if dist_sq <= minor_r_sq:
                                self.set_voxel(x, y, z, color_index)
    
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
        elif axis == 'x':
            for x in range(height):
                current_radius = int(base_radius * (1 - x / height))
                if current_radius < 1:
                    current_radius = 1
                
                radius_sq = current_radius * current_radius
                
                for y in range(base_y - base_radius, base_y + base_radius + 1):
                    for z in range(base_z - base_radius, base_z + base_radius + 1):
                        dy = y - base_y
                        dz = z - base_z
                        dist_sq = dy*dy + dz*dz
                        
                        if hollow and x < height - 1:
                            if abs(dist_sq - radius_sq) <= current_radius:
                                self.set_voxel(base_x + x, y, z, color_index)
                        else:
                            if dist_sq <= radius_sq:
                                self.set_voxel(base_x + x, y, z, color_index)
        else:  # axis == 'z'
            for z in range(height):
                current_radius = int(base_radius * (1 - z / height))
                if current_radius < 1:
                    current_radius = 1
                
                radius_sq = current_radius * current_radius
                
                for x in range(base_x - base_radius, base_x + base_radius + 1):
                    for y in range(base_y - base_radius, base_y + base_radius + 1):
                        dx = x - base_x
                        dy = y - base_y
                        dist_sq = dx*dx + dy*dy
                        
                        if hollow and z < height - 1:
                            if abs(dist_sq - radius_sq) <= current_radius:
                                self.set_voxel(x, y, base_z + z, color_index)
                        else:
                            if dist_sq <= radius_sq:
                                self.set_voxel(x, y, base_z + z, color_index)
    
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
                     plane: str, position: int):
        """Mirror a region across a plane. Plane: 'x', 'y', or 'z'. Position is the plane coordinate."""
        # Extract region voxels
        region_voxels = {}
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    if (x, y, z) in self.voxels:
                        region_voxels[(x, y, z)] = self.voxels[(x, y, z)]
        
        # Mirror and place (set_voxel already checks bounds 0-255)
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
            
            # set_voxel checks bounds (0-255), so this is safe
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


def read_vox_file(filepath: Path) -> VoxelModel:
    """Read a .vox file and return a VoxelModel"""
    with open(filepath, 'rb') as f:
        # Read header
        magic = f.read(4)
        if magic != b'VOX ':
            raise ValueError("Invalid .vox file format")
        
        version = struct.unpack('<I', f.read(4))[0]
        
        # Read MAIN chunk
        chunk_id = f.read(4)
        if chunk_id != b'MAIN':
            raise ValueError("Expected MAIN chunk")
        
        chunk_size = struct.unpack('<I', f.read(4))[0]
        child_chunks = struct.unpack('<I', f.read(4))[0]
        
        # Read SIZE chunk
        size_id = f.read(4)
        if size_id != b'SIZE':
            raise ValueError("Expected SIZE chunk")
        
        size_chunk_size = struct.unpack('<I', f.read(4))[0]
        size_child_chunks = struct.unpack('<I', f.read(4))[0]
        
        size_x = struct.unpack('<I', f.read(4))[0]
        size_y = struct.unpack('<I', f.read(4))[0]
        size_z = struct.unpack('<I', f.read(4))[0]
        
        # Create model with the size from file, but we'll allow placing voxels beyond it
        model = VoxelModel(size_x, size_y, size_z)
        
        # Read XYZI chunk (voxel data)
        xyzi_id = f.read(4)
        if xyzi_id == b'XYZI':
            xyzi_chunk_size = struct.unpack('<I', f.read(4))[0]
            xyzi_child_chunks = struct.unpack('<I', f.read(4))[0]
            
            num_voxels = struct.unpack('<I', f.read(4))[0]
            
            for _ in range(num_voxels):
                x = struct.unpack('<B', f.read(1))[0]
                y = struct.unpack('<B', f.read(1))[0]
                z = struct.unpack('<B', f.read(1))[0]
                color_index = struct.unpack('<B', f.read(1))[0]
                model.set_voxel(x, y, z, color_index)
        
        # Try to read RGBA palette if present
        rgba_id = f.read(4)
        if rgba_id == b'RGBA':
            rgba_chunk_size = struct.unpack('<I', f.read(4))[0]
            rgba_child_chunks = struct.unpack('<I', f.read(4))[0]
            
            palette = []
            for _ in range(256):
                r = struct.unpack('<B', f.read(1))[0]
                g = struct.unpack('<B', f.read(1))[0]
                b = struct.unpack('<B', f.read(1))[0]
                a = struct.unpack('<B', f.read(1))[0]
                palette.append((r, g, b, a))
            model.palette = palette
    
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


def write_vox_file(filepath: Path, model: VoxelModel):
    """Write a VoxelModel to a .vox file"""
    with open(filepath, 'wb') as f:
        # Write header
        f.write(b'VOX ')
        f.write(struct.pack('<I', 150))  # Version 150
        
        # Calculate chunk sizes
        # Use the model's declared size, but ensure it's at least as large as the bounds
        if model.voxels:
            actual_bounds = model.get_bounds()
            # Use the larger of declared size or actual bounds
            size_x = max(model.size_x, actual_bounds[0])
            size_y = max(model.size_y, actual_bounds[1])
            size_z = max(model.size_z, actual_bounds[2])
        else:
            # Use specified size
            size_x, size_y, size_z = model.size_x, model.size_y, model.size_z
        
        num_voxels = len(model.voxels)
        
        # SIZE chunk
        size_chunk_size = 12  # 3 * 4 bytes
        size_chunk_child = 0
        
        # XYZI chunk
        xyzi_chunk_size = 4 + (num_voxels * 4)  # 4 bytes for count + 4 bytes per voxel
        xyzi_chunk_child = 0
        
        # RGBA chunk
        rgba_chunk_size = 256 * 4  # 256 colors * 4 bytes
        rgba_chunk_child = 0
        
        # MAIN chunk
        main_chunk_size = 0  # MAIN chunk contains child chunks
        main_chunk_child = 8 + size_chunk_size + 8 + xyzi_chunk_size + 8 + rgba_chunk_size
        
        # Write MAIN chunk header
        f.write(b'MAIN')
        f.write(struct.pack('<I', main_chunk_size))
        f.write(struct.pack('<I', main_chunk_child))
        
        # Write SIZE chunk
        f.write(b'SIZE')
        f.write(struct.pack('<I', size_chunk_size))
        f.write(struct.pack('<I', size_chunk_child))
        f.write(struct.pack('<I', size_x))
        f.write(struct.pack('<I', size_y))
        f.write(struct.pack('<I', size_z))
        
        # Write XYZI chunk
        f.write(b'XYZI')
        f.write(struct.pack('<I', xyzi_chunk_size))
        f.write(struct.pack('<I', xyzi_chunk_child))
        f.write(struct.pack('<I', num_voxels))
        
        for (x, y, z), color_index in model.voxels.items():
            f.write(struct.pack('<B', x))
            f.write(struct.pack('<B', y))
            f.write(struct.pack('<B', z))
            f.write(struct.pack('<B', color_index))
        
        # Write RGBA chunk
        f.write(b'RGBA')
        f.write(struct.pack('<I', rgba_chunk_size))
        f.write(struct.pack('<I', rgba_chunk_child))
        
        for r, g, b, a in model.palette:
            f.write(struct.pack('<B', r))
            f.write(struct.pack('<B', g))
            f.write(struct.pack('<B', b))
            f.write(struct.pack('<B', a))
