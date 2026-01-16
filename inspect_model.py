#!/usr/bin/env python3
"""Inspect a voxel model and show its structure"""

from pathlib import Path
from vox_utils import read_vox_file
from collections import defaultdict

def inspect_model(filename):
    model = read_vox_file(Path(f"../vox/{filename}.vox"))
    
    print(f"\n{'='*60}")
    print(f"Model: {filename}.vox")
    print(f"{'='*60}")
    print(f"Dimensions: {model.size_x} x {model.size_y} x {model.size_z}")
    print(f"Total voxels: {model.get_voxel_count()}")
    print(f"\nVoxel distribution by Y level (height):")
    print("-" * 60)
    
    # Group voxels by Y coordinate
    voxels_by_y = defaultdict(list)
    for (x, y, z), color in model.voxels.items():
        voxels_by_y[y].append((x, z, color))
    
    # Show each Y level
    for y in sorted(voxels_by_y.keys(), reverse=True):
        voxels = voxels_by_y[y]
        print(f"\nY={y:2d} (height level): {len(voxels)} voxels")
        
        # Create a simple 2D view of this Y level
        grid = {}
        for x, z, color in voxels:
            grid[(x, z)] = color
        
        # Find bounds
        if grid:
            xs = [x for x, z in grid.keys()]
            zs = [z for x, z in grid.keys()]
            min_x, max_x = min(xs), max(xs)
            min_z, max_z = min(zs), max(zs)
            
            print(f"  X range: {min_x} to {max_x}, Z range: {min_z} to {max_z}")
            print(f"  View from above (X-Z plane):")
            print("    ", end="")
            for z in range(min_z, max_z + 1):
                print(f"{z:2d}", end=" ")
            print()
            for x in range(min_x, max_x + 1):
                print(f"  {x:2d} ", end="")
                for z in range(min_z, max_z + 1):
                    if (x, z) in grid:
                        print("##", end=" ")
                    else:
                        print("  ", end=" ")
                print()
    
    print(f"\n{'='*60}")

if __name__ == "__main__":
    inspect_model("test")
