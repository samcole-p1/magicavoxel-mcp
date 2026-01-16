# Proportion System Improvements

## Summary

Based on research into human anatomy, character design principles, and Minecraft-specific measurements, the MCP server now includes a comprehensive proportion calculation and validation system.

## What Was Added

### 1. Proportion Calculation Functions (`vox_utils.py`)

#### `calculate_human_proportions(total_height, style)`
Calculates proper human body proportions based on:
- **Standard**: 8 heads tall (classical human anatomy)
- **Minecraft**: Minecraft player model proportions
- **Heroic**: 9 heads tall (exaggerated superhero style)
- **Chibi**: 4-5 heads tall (cute/stylized)

#### `calculate_minecraft_proportions()`
Returns official Minecraft measurements:
- Player height: 1.8 blocks (1.875 meters)
- Player width: 0.6 blocks
- Eye height: 1.62 meters
- Block size: 1 meter = 1 block
- Texture resolution: 16 pixels per block

#### `check_proportions(model, part_name, dimensions, model_height, style)`
Validates if body part dimensions are proportional:
- Checks head, torso, legs, arms
- Warns if parts are >1.5x or <0.5x expected size
- Returns helpful warning messages

#### `suggest_proportions(model_height, style)`
Provides detailed dimension suggestions for all body parts:
- Head dimensions and radius
- Neck dimensions
- Torso dimensions
- Legs dimensions
- Arms dimensions

### 2. MCP Tool Integration (`server.py`)

#### Automatic Proportion Checking
- **`fill_box`**: Automatically checks proportions for vertical boxes that might be body parts
  - Detects torso (upper third of model)
  - Detects legs (lower third of model)
  - Warns if dimensions are disproportionate

- **`create_sphere`**: Checks proportions for spheres near the top of the model
  - Detects likely heads
  - Warns if head is too large or too small

#### New Tool: `get_proportion_suggestions`
Get suggested proportions for a character model:
```python
get_proportion_suggestions(
    model_height=32,
    style="standard"  # or "minecraft", "heroic", "chibi"
)
```

Returns:
- Suggested dimensions for all body parts
- Minecraft reference data (if style="minecraft")

## Research Basis

### Human Anatomy (8 Heads Rule)
- Based on classical art and character design
- Standard human: 7.5-8 heads tall
- Head = 1/8 of total height
- Legs = 1/2 of total height
- Torso = 3/8 of total height

### Minecraft Measurements
- Based on official Minecraft Wiki and game code
- Player height: 1.8 blocks (1.875 meters)
- Player width: 0.6 blocks
- Eye height: 1.62 meters above base
- Standard skin: 32 voxels tall

### Character Design Styles
- **Heroic**: 9 heads tall (exaggerated)
- **Chibi**: 4-5 heads tall (cute)
- **Standard**: 8 heads tall (realistic)

## Example Output

### Standard 32-voxel Character:
```
Head: 4 voxels (1/8 of height)
Neck: 1 voxel
Torso: 12 voxels (3/8 of height)
Legs: 16 voxels (1/2 of height)
Arms: 12 voxels (3/8 of height)
```

### Minecraft Character:
```
Head: 8 voxels (Minecraft standard)
Torso: 12 voxels
Legs: 12 voxels
Player height: 1.8 blocks
Player width: 0.6 blocks
```

## Benefits

1. **Prevents Common Mistakes**
   - Catches heads that are too large (e.g., 8 voxels instead of 4)
   - Catches legs that are too short (e.g., 12 voxels instead of 16)
   - Warns immediately during model creation

2. **Style Consistency**
   - Ensures models match intended art style
   - Supports multiple character styles
   - Minecraft-compatible proportions

3. **Educational**
   - Teaches proper character proportions
   - Provides reference data
   - Shows expected vs actual dimensions

4. **Automatic Validation**
   - Tools warn when proportions are off
   - No need to manually check
   - Actionable suggestions provided

## Usage Examples

### Example 1: Get Proportion Suggestions
```python
# Get suggestions for 32-voxel standard character
get_proportion_suggestions(model_height=32, style="standard")

# Returns:
# Head: 4×4×4 voxels (radius: 2)
# Torso: 12×8×6 voxels
# Legs: 16×6×6 voxels
# Arms: 12×3×3 voxels
```

### Example 2: Automatic Warnings
```python
# Create a head that's too large
create_sphere(filename="character", center_x=8, center_y=30, center_z=8, radius=4)

# Returns:
# "Created sphere at (8, 30, 8) with radius 4
# Warning: head height (9 voxels) is too large. Expected ~4 voxels for 32-voxel standard character (2.3x expected size)."
```

### Example 3: Check Proportions Programmatically
```python
from vox_utils import check_proportions, read_vox_file

model = read_vox_file("character.vox")
warning = check_proportions(model, "head", (6, 6, 6), 32, "standard")

if warning:
    print(warning)  # Shows proportion warning
```

## Files Modified

1. **`magicavoxel-mcp/vox_utils.py`**
   - Added `calculate_human_proportions()`
   - Added `calculate_minecraft_proportions()`
   - Added `check_proportions()`
   - Added `suggest_proportions()`

2. **`magicavoxel-mcp/server.py`**
   - Updated imports to include proportion functions
   - Enhanced `fill_box` handler with proportion checking
   - Enhanced `create_sphere` handler with proportion checking
   - Added new `get_proportion_suggestions` tool

3. **Documentation**
   - Created `PROPORTION_SYSTEM.md` (detailed documentation)
   - Created `PROPORTION_IMPROVEMENTS.md` (this file)

## Testing

The proportion system has been tested and verified:
- ✅ Standard proportions calculate correctly
- ✅ Minecraft proportions match official measurements
- ✅ Proportion checking works for heads, torsos, legs
- ✅ Warnings are generated for disproportionate parts
- ✅ Suggestions are accurate and helpful

## Future Enhancements

- Support for more character styles (anime, realistic, etc.)
- Gender-specific proportions (male vs female)
- Age-based proportions (child, adult, elder)
- Automatic proportion correction suggestions
- Integration with intelligence layer for smart defaults
- Visual proportion guides in tool responses
