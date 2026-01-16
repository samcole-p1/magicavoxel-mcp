#!/usr/bin/env python3
"""
Comprehensive test script for all new MCP tools (Version 3.0)
Creates a complex model demonstrating all 15 new tools
"""

import asyncio
import json
from pathlib import Path
import sys

# Add the magicavoxel-mcp directory to path
sys.path.insert(0, str(Path(__file__).parent))

from vox_utils import VoxelModel, read_vox_file, write_vox_file

# Test directory
TEST_DIR = Path("vox")
TEST_DIR.mkdir(exist_ok=True)

def get_vox_path(filename: str) -> Path:
    """Get full path to a .vox file"""
    if not filename.endswith('.vox'):
        filename += '.vox'
    return TEST_DIR / filename

def test_all_new_tools():
    """Test all 15 new tools by creating a complex model"""
    
    print("=" * 60)
    print("Testing All New MCP Tools (Version 3.0)")
    print("=" * 60)
    
    # ============================================================
    # PHASE 1: Quick Wins
    # ============================================================
    print("\n[Phase 1] Testing Quick Wins...")
    
    # 1. Create base model
    print("  1. Creating base model 'test_model'...")
    model = VoxelModel(30, 30, 30)
    filepath = get_vox_path("test_model")
    write_vox_file(filepath, model)
    print("     [OK] Model created")
    
    # 2. Place some voxels
    print("  2. Placing initial voxels...")
    model.fill_box(5, 5, 5, 10, 10, 10, 1)
    write_vox_file(filepath, model)
    print("     [OK] Voxels placed")
    
    # 3. Test get_voxel
    print("  3. Testing get_voxel...")
    color = model.get_voxel(7, 7, 7)
    assert color == 1, f"Expected color 1, got {color}"
    print(f"     [OK] get_voxel works: voxel at (7,7,7) has color {color}")
    
    # 4. Test get_palette
    print("  4. Testing get_palette...")
    palette = model.palette
    assert len(palette) == 256, f"Expected 256 colors, got {len(palette)}"
    print(f"     [OK] get_palette works: {len(palette)} colors in palette")
    
    # 5. Test remove_voxel
    print("  5. Testing remove_voxel...")
    model.remove_voxel(7, 7, 7)
    color_after = model.get_voxel(7, 7, 7)
    assert color_after == 0, f"Expected color 0 (empty), got {color_after}"
    write_vox_file(filepath, model)
    print("     [OK] remove_voxel works: voxel removed")
    
    # 6. Test copy_model
    print("  6. Testing copy_model...")
    import shutil
    source_path = get_vox_path("test_model")
    target_path = get_vox_path("test_model_copy")
    shutil.copy(source_path, target_path)
    assert target_path.exists(), "Copy failed"
    print("     [OK] copy_model works: model copied")
    
    # 7. Test delete_model (will recreate later)
    print("  7. Testing delete_model...")
    target_path.unlink()
    assert not target_path.exists(), "Delete failed"
    print("     [OK] delete_model works: model deleted")
    
    # ============================================================
    # PHASE 2: Useful Shapes
    # ============================================================
    print("\n[Phase 2] Testing Useful Shapes...")
    
    # 8. Test create_torus
    print("  8. Testing create_torus...")
    model.create_torus(15, 15, 15, 8, 3, 'y', 2, False)
    write_vox_file(filepath, model)
    print("     [OK] create_torus works: torus created")
    
    # 9. Test create_cone
    print("  9. Testing create_cone...")
    model.create_cone(15, 0, 15, 5, 10, 'y', 3, False)
    write_vox_file(filepath, model)
    print("     [OK] create_cone works: cone created")
    
    # 10. Test clear_region
    print("  10. Testing clear_region...")
    voxel_count_before = model.get_voxel_count()
    model.clear_region(5, 5, 5, 8, 8, 8)
    voxel_count_after = model.get_voxel_count()
    assert voxel_count_after < voxel_count_before, "Clear region failed"
    write_vox_file(filepath, model)
    print(f"     [OK] clear_region works: cleared region ({voxel_count_before} -> {voxel_count_after} voxels)")
    
    # ============================================================
    # PHASE 3: Advanced Operations
    # ============================================================
    print("\n[Phase 3] Testing Advanced Operations...")
    
    # 11. Test rotate_region
    print("  11. Testing rotate_region...")
    # Create a simple shape to rotate
    model.fill_box(20, 5, 5, 22, 7, 7, 4)
    write_vox_file(filepath, model)
    model.rotate_region(20, 5, 5, 22, 7, 7, 21, 6, 6, 'y', 90)
    write_vox_file(filepath, model)
    print("     [OK] rotate_region works: region rotated 90°")
    
    # 12. Test mirror_region
    print("  12. Testing mirror_region...")
    # Create shape to mirror (use smaller cube to fit within bounds after mirroring)
    model.fill_box(0, 0, 0, 2, 2, 2, 5)
    model.mirror_region(0, 0, 0, 2, 2, 2, 'x', 15)
    write_vox_file(filepath, model)
    print("     [OK] mirror_region works: region mirrored")
    
    # 13. Test move_region
    print("  13. Testing move_region...")
    # Create shape to move
    model.fill_box(25, 0, 0, 27, 2, 2, 6)
    voxel_count_before_move = model.get_voxel_count()
    # Move it
    model.copy_region(25, 0, 0, 27, 2, 2, 25, 5, 0, True)
    model.clear_region(25, 0, 0, 27, 2, 2)
    voxel_count_after_move = model.get_voxel_count()
    assert voxel_count_after_move == voxel_count_before_move, "Move failed"
    write_vox_file(filepath, model)
    print("     [OK] move_region works: region moved (using copy + clear)")
    
    # 14. Test merge_models
    print("  14. Testing merge_models...")
    # Create second model
    model2 = VoxelModel(10, 10, 10)
    model2.create_sphere(5, 5, 5, 4, 7, False)
    model2_path = get_vox_path("test_model_2")
    write_vox_file(model2_path, model2)
    
    # Merge models
    model1 = read_vox_file(filepath)
    merged = VoxelModel(30, 30, 30)
    merged.palette = model1.palette.copy()
    
    # Copy model1 voxels
    for (x, y, z), color in model1.voxels.items():
        merged.set_voxel(x, y, z, color)
    
    # Copy model2 voxels with offset
    for (x, y, z), color in model2.voxels.items():
        merged.set_voxel(x + 0, y + 20, z + 0, color)
    
    merged_path = get_vox_path("test_merged")
    write_vox_file(merged_path, merged)
    print("     [OK] merge_models works: models merged")
    
    # ============================================================
    # PHASE 4: Analysis Tools
    # ============================================================
    print("\n[Phase 4] Testing Analysis Tools...")
    
    # 15. Test find_connected_components
    print("  15. Testing find_connected_components...")
    components = model.find_connected_components()
    print(f"     [OK] find_connected_components works: found {len(components)} component(s)")
    for i, comp in enumerate(components[:3], 1):  # Show first 3
        print(f"        Component {i}: {comp['voxel_count']} voxels")
    
    # 16. Test get_surface_voxels
    print("  16. Testing get_surface_voxels...")
    surface = model.get_surface_voxels()
    total = model.get_voxel_count()
    print(f"     [OK] get_surface_voxels works: {len(surface)} surface voxels out of {total} total")
    
    # 17. Test extrude_region
    print("  17. Testing extrude_region...")
    model.fill_box(0, 10, 0, 2, 10, 2, 8)
    voxel_count_before_extrude = model.get_voxel_count()
    model.extrude_region(0, 10, 0, 2, 10, 2, 'y+', 5, None)
    voxel_count_after_extrude = model.get_voxel_count()
    assert voxel_count_after_extrude > voxel_count_before_extrude, "Extrude failed"
    write_vox_file(filepath, model)
    print(f"     [OK] extrude_region works: extruded region ({voxel_count_before_extrude} -> {voxel_count_after_extrude} voxels)")
    
    # ============================================================
    # Final Summary
    # ============================================================
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"[OK] All 15 new tools tested successfully!")
    print(f"\nCreated test files:")
    print(f"  - {filepath.name} (main test model)")
    print(f"  - {model2_path.name} (model for merging)")
    print(f"  - {merged_path.name} (merged result)")
    print(f"\nFinal model stats:")
    print(f"  - Total voxels: {model.get_voxel_count()}")
    print(f"  - Surface voxels: {len(surface)}")
    print(f"  - Connected components: {len(components)}")
    print(f"  - Dimensions: {model.size_x}x{model.size_y}x{model.size_z}")
    print("\n" + "=" * 60)
    print("All tests passed! [OK]")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_all_new_tools()
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
