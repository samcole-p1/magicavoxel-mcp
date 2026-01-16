#!/usr/bin/env python3
"""
Model Builder - High-level interface for creating models using MCP tools
This makes model creation much more efficient by using the MCP tools directly
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from vox_utils import VoxelModel, read_vox_file, write_vox_file

class ModelBuilder:
    """High-level builder for creating voxel models efficiently"""
    
    def __init__(self, filename: str, width: int = 32, height: int = 32, depth: int = 32):
        """Initialize a new model builder"""
        self.filename = filename
        self.filepath = Path("vox") / f"{filename}.vox"
        self.model = VoxelModel(width, height, depth)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
    
    def save(self):
        """Save the model to file"""
        write_vox_file(self.filepath, self.model)
        return self
    
    def color(self, index: int, r: int, g: int, b: int, a: int = 255):
        """Set a palette color"""
        self.model.set_palette_color(index, r, g, b, a)
        return self
    
    def box(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, color: int = 1):
        """Fill a box region"""
        self.model.fill_box(x1, y1, z1, x2, y2, z2, color)
        return self
    
    def sphere(self, x: int, y: int, z: int, radius: int, color: int = 1, hollow: bool = False):
        """Create a sphere"""
        self.model.create_sphere(x, y, z, radius, color, hollow)
        return self
    
    def cylinder(self, x: int, y: int, z: int, radius: int, height: int, 
                 axis: str = 'y', color: int = 1, hollow: bool = False):
        """Create a cylinder"""
        self.model.create_cylinder(x, y, z, radius, height, axis, color, hollow)
        return self
    
    def cone(self, x: int, y: int, z: int, radius: int, height: int,
             axis: str = 'y', color: int = 1, hollow: bool = False):
        """Create a cone"""
        self.model.create_cone(x, y, z, radius, height, axis, color, hollow)
        return self
    
    def pyramid(self, x: int, y: int, z: int, width: int, depth: int, height: int,
                color: int = 1, hollow: bool = False):
        """Create a pyramid"""
        self.model.create_pyramid(x, y, z, width, depth, height, color, hollow)
        return self
    
    def torus(self, x: int, y: int, z: int, major_r: int, minor_r: int,
              axis: str = 'y', color: int = 1, hollow: bool = False):
        """Create a torus"""
        self.model.create_torus(x, y, z, major_r, minor_r, axis, color, hollow)
        return self
    
    def clear(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int):
        """Clear a region"""
        self.model.clear_region(x1, y1, z1, x2, y2, z2)
        return self
    
    def copy(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
             tx: int, ty: int, tz: int, overwrite: bool = True):
        """Copy a region"""
        self.model.copy_region(x1, y1, z1, x2, y2, z2, tx, ty, tz, overwrite)
        return self
    
    def move(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
             tx: int, ty: int, tz: int):
        """Move a region"""
        self.model.copy_region(x1, y1, z1, x2, y2, z2, tx, ty, tz, True)
        self.model.clear_region(x1, y1, z1, x2, y2, z2)
        return self
    
    def rotate(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
               cx: int, cy: int, cz: int, axis: str, degrees: int):
        """Rotate a region"""
        self.model.rotate_region(x1, y1, z1, x2, y2, z2, cx, cy, cz, axis, degrees)
        return self
    
    def mirror(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
               plane: str, position: int):
        """Mirror a region"""
        self.model.mirror_region(x1, y1, z1, x2, y2, z2, plane, position)
        return self
    
    def extrude(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                direction: str, distance: int, color: Optional[int] = None):
        """Extrude a region"""
        self.model.extrude_region(x1, y1, z1, x2, y2, z2, direction, distance, color)
        return self
    
    def place(self, x: int, y: int, z: int, color: int = 1):
        """Place a single voxel"""
        self.model.set_voxel(x, y, z, color)
        return self
    
    def remove(self, x: int, y: int, z: int):
        """Remove a single voxel"""
        self.model.remove_voxel(x, y, z)
        return self

# Example usage:
if __name__ == "__main__":
    # Create a dog using the builder (much simpler!)
    dog = (ModelBuilder("dog_v2", 16, 16, 24)
        .color(1, 141, 110, 99)  # Brown
        .color(2, 50, 30, 20)    # Dark brown
        .color(3, 180, 150, 120) # Light brown
        .color(4, 240, 240, 240) # White
        
        # Body
        .box(4, 4, 6, 11, 11, 16, 1)
        
        # Head
        .box(5, 5, 17, 10, 10, 22, 1)
        .box(6, 6, 23, 9, 9, 23, 1)  # Snout
        
        # Legs
        .cylinder(6, 0, 13, 1, 5, 'y', 1)
        .cylinder(10, 0, 13, 1, 5, 'y', 1)
        .cylinder(6, 0, 8, 1, 5, 'y', 1)
        .cylinder(10, 0, 8, 1, 5, 'y', 1)
        
        # Paws
        .box(4, 0, 11, 7, 1, 14, 2)
        .box(8, 0, 11, 11, 1, 14, 2)
        .box(4, 0, 6, 7, 1, 9, 2)
        .box(8, 0, 6, 11, 1, 9, 2)
        
        # Tail
        .box(7, 8, 5, 8, 8, 5, 1)
        .box(7, 9, 4, 8, 9, 4, 1)
        .box(7, 10, 3, 8, 10, 3, 1)
        .place(7, 11, 2, 4)  # Tail tip
        .place(8, 11, 2, 4)
        
        # Details
        .place(7, 7, 23, 2)  # Nose
        .place(8, 7, 23, 2)
        .place(5, 7, 19, 2)  # Eyes
        .place(10, 7, 19, 2)
        .box(6, 4, 16, 9, 6, 16, 4)  # Chest
        .box(5, 4, 8, 10, 4, 14, 3)  # Belly
        
        # Ears
        .box(4, 8, 19, 4, 10, 20, 1)
        .box(11, 8, 19, 11, 10, 20, 1)
        
        .save())
    
    print(f"Created {dog.filename}.vox using ModelBuilder!")
