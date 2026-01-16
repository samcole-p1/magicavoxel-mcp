# Proportion Calculation System

## Overview

The MCP server now includes a comprehensive proportion calculation system based on research into human anatomy, character design principles, and Minecraft-specific measurements. This system helps ensure models are created with correct proportions.

## Supported Proportion Styles

### 1. Standard (8 Heads Tall)
**Based on:** Classical human anatomy and character design principles

- **Head**: 1/8 of total height
- **Neck**: 1/32 of total height
- **Torso**: 3/8 of total height (3 heads)
- **Legs**: 1/2 of total height (4 heads)
- **Arms**: 3/8 of total height (3 heads)

**Example for 32-voxel character:**
- Head: 4 voxels
- Neck: 1 voxel
- Torso: 12 voxels
- Legs: 16 voxels
- Arms: 12 voxels

### 2. Minecraft
**Based on:** Official Minecraft player model measurements

- **Player height**: 1.8 blocks (1.875 meters) when standing
- **Player width**: 0.6 blocks
- **Eye height**: 1.62 meters above base
- **Model structure**: 32 voxels tall (head: 8, torso: 12, legs: 12)

**Minecraft Reference:**
- 1 block = 1 meter
- 16 pixels = 1 block (texture resolution)
- Player hitbox: 1.8×0.6 blocks (standing)

### 3. Heroic (9 Heads Tall)
**Based on:** Exaggerated heroic character proportions

- **Head**: 1/9 of total height
- **Torso**: 3/9 of total height
- **Legs**: 4/9 of total height
- **Arms**: 3/9 of total height

### 4. Chibi (4-5 Heads Tall)
**Based on:** Cute/chibi style character design

- **Head**: 1/4 of total height (larger head)
- **Torso**: 1/4 of total height
- **Legs**: 1/4 of total height
- **Arms**: 1/4 of total height

## Functions

### `calculate_human_proportions(total_height, style="standard")`

Calculates proper human body proportions based on the selected style.

**Parameters:**
- `total_height`: Total height of the character in voxels
- `style`: "standard", "minecraft", "heroic", or "chibi"

**Returns:**
Dictionary with body part dimensions:
```python
{
    'head': 4,
    'neck': 1,
    'torso': 12,
    'legs': 16,
    'arms': 12,
    'total': 32
}
```

### `calculate_minecraft_proportions()`

Returns Minecraft-specific measurements based on official game data.

**Returns:**
Dictionary with Minecraft measurements:
```python
{
    'player_height_standing': 1.8,  # blocks
    'player_height_sneaking': 1.5,  # blocks
    'player_width': 0.6,  # blocks
    'eye_height_standing': 1.62,  # meters
    'block_size': 1.0,  # 1 block = 1 meter
    'pixels_per_block': 16,
    'meters_per_pixel': 0.0625,
    'player_model_height_voxels': 32,
    'head_voxels': 8,
    'torso_voxels': 12,
    'legs_voxels': 12
}
```

### `check_proportions(model, part_name, dimensions, model_height, style="standard")`

Validates if a body part's dimensions are proportional to the overall model.

**Parameters:**
- `model`: The VoxelModel instance
- `part_name`: "head", "torso", "legs", "arms", etc.
- `dimensions`: (width, height, depth) tuple
- `model_height`: Total model height (optional, calculated if not provided)
- `style`: Proportion style to use

**Returns:**
- `None` if proportions are OK
- Warning string if disproportionate

**Example:**
```python
warning = check_proportions(model, "head", (6, 6, 6), 32, "standard")
# Returns: "Warning: head height (6 voxels) is too large. Expected ~4 voxels..."
```

### `suggest_proportions(model_height, style="standard")`

Provides detailed dimension suggestions for all body parts.

**Returns:**
Dictionary with suggested dimensions for each body part:
```python
{
    'head': {'height': 4, 'width': 4, 'depth': 4, 'radius': 2},
    'neck': {'height': 1, 'width': 2, 'depth': 2},
    'torso': {'height': 12, 'width': 8, 'depth': 6},
    'legs': {'height': 16, 'width': 6, 'depth': 6},
    'arms': {'length': 12, 'width': 3, 'depth': 3}
}
```

## Integration with MCP Tools

### Automatic Proportion Checking

The following tools now automatically check proportions:

1. **`fill_box`**: Checks proportions for vertical boxes that might be body parts (torso, legs)
2. **`create_sphere`**: Checks proportions for spheres near the top of the model (likely heads)

### New MCP Tool: `get_proportion_suggestions`

Get suggested proportions for a character model:

```python
get_proportion_suggestions(
    model_height=32,
    style="standard"  # or "minecraft", "heroic", "chibi"
)
```

**Returns:**
- Suggested dimensions for all body parts
- Minecraft reference data (if style="minecraft")

## Usage Examples

### Example 1: Creating a Standard Character

```python
# Get suggestions for 32-voxel character
suggestions = suggest_proportions(32, "standard")

# Head: 4×4×4 voxels (radius 2)
# Torso: 12×8×6 voxels
# Legs: 16×6×6 voxels
# Arms: 12×3×3 voxels
```

### Example 2: Creating a Minecraft-Style Character

```python
# Get Minecraft proportions
suggestions = suggest_proportions(32, "minecraft")

# Head: 8×8×8 voxels (Minecraft standard)
# Torso: 12×8×6 voxels
# Legs: 12×6×6 voxels
```

### Example 3: Validating Proportions

```python
# Check if a head is too large
model = read_vox_file("character.vox")
warning = check_proportions(model, "head", (6, 6, 6), 32, "standard")

if warning:
    print(warning)  # "Warning: head height (6 voxels) is too large..."
```

## Research Basis

### Human Anatomy (8 Heads Rule)
- Based on classical art and character design principles
- Standard human figure is 7.5-8 heads tall
- Head = 1/8 of total height
- Legs = 1/2 of total height
- Torso = 3/8 of total height

### Minecraft Measurements
- Based on official Minecraft Wiki and game code
- Player height: 1.8 blocks (1.875 meters)
- Player width: 0.6 blocks
- Eye height: 1.62 meters above base
- Standard skin: 32 voxels tall (64×64 pixel texture)

### Character Design Styles
- **Heroic**: 9 heads tall (exaggerated, superhero style)
- **Chibi**: 4-5 heads tall (cute, stylized)
- **Standard**: 8 heads tall (realistic proportions)

## Benefits

1. **Prevents Common Mistakes**: Catches heads that are too large, legs that are too short
2. **Style Consistency**: Ensures models match the intended art style
3. **Minecraft Compatibility**: Helps create models that match Minecraft scale
4. **Educational**: Teaches proper character proportions
5. **Automatic Validation**: Tools warn when proportions are off

## Future Enhancements

- Support for more character styles (anime, realistic, etc.)
- Gender-specific proportions (male vs female)
- Age-based proportions (child, adult, elder)
- Automatic proportion correction suggestions
- Integration with intelligence layer for smart defaults
