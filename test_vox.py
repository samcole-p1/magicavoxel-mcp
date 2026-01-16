#!/usr/bin/env python3
"""
Simple test script to verify .vox file operations
"""

from pathlib import Path
from vox_utils import VoxelModel, read_vox_file, write_vox_file

# Test creating a simple model
print("Creating test model...")
model = VoxelModel(10, 10, 10)

# Place some voxels
model.set_voxel(5, 5, 5, 1)  # White
model.fill_box(0, 0, 0, 2, 2, 2, 2)  # Red box

# Save it
test_file = Path("test_model.vox")
write_vox_file(test_file, model)
print(f"Saved test model to {test_file}")

# Read it back
print("\nReading model back...")
loaded_model = read_vox_file(test_file)
print(f"Dimensions: {loaded_model.size_x}x{loaded_model.size_y}x{loaded_model.size_z}")
print(f"Voxel count: {loaded_model.get_voxel_count()}")
print(f"Voxel at (5,5,5): {loaded_model.get_voxel(5, 5, 5)}")

print("\nTest completed successfully!")
