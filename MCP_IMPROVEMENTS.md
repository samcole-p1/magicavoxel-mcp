# MCP Tool Improvements to Prevent Character Creation Mistakes

## Problems Identified

1. **Disconnected Parts**: Arms, hands not connecting to body
2. **Gaps**: Head not connecting to torso
3. **Incorrect Proportions**: Head too large, legs too short
4. **No Validation**: Tools don't check if operations create valid structures

## Root Cause Analysis

### Issue 1: No Connection Validation
**Problem**: When placing body parts, tools don't check if they connect to existing parts.

**Example**: 
- Torso at x=5-11
- Arms placed at x=3 and x=13
- Result: Arms don't touch torso → disconnected

**Solution**: Add connection validation to placement tools.

### Issue 2: No Proportional Guidance
**Problem**: Tools don't know about human proportions or suggest correct sizes.

**Example**:
- User creates head with radius 3 → too large
- No feedback that head should be ~4 voxels for 32-height character

**Solution**: Add proportional helpers and validation.

### Issue 3: No Gap Detection
**Problem**: Tools don't detect gaps between body parts.

**Example**:
- Head at y=28-32
- Torso at y=14-25
- Gap at y=26-27 → head floating

**Solution**: Add gap detection and auto-fill options.

### Issue 4: No Structure Validation
**Problem**: No way to check if model is valid before completion.

**Example**:
- Model has 5 disconnected pieces
- No warning until after creation

**Solution**: Add validation tools that can be called during/after creation.

---

## Proposed Improvements

### Improvement 1: Connection-Aware Placement

**Enhance existing tools** to check connections:

#### Option A: Add `ensure_connection` parameter
```python
# Enhanced fill_box tool
fill_box(
    filename="character",
    x1=4, y1=20, z1=6,
    x2=4, y2=24, z2=10,
    color_index=1,
    ensure_connection=True  # NEW: Check if connects to existing parts
)
```

**Behavior**:
- If `ensure_connection=True`, check if box touches existing voxels
- If not, suggest/adjust coordinates to connect
- Return warning if can't connect

#### Option B: Add connection validation helper
```python
# New validation in tool responses
fill_box(...) 
# Returns: "Created box. Warning: Box at (4,20,6) does not connect to existing parts at (5,20,6)"
```

### Improvement 2: Proportional Validation

**Add proportional checks** to shape creation tools:

```python
# Enhanced create_sphere for heads
create_sphere(
    filename="character",
    center_x=8, center_y=30, center_z=8,
    radius=3,
    color_index=1,
    validate_proportions=True  # NEW: Check if size is reasonable
)
```

**Behavior**:
- If model height is 32 and radius=3 creates head >4 voxels → warning
- Suggest correct radius based on model size
- Return: "Warning: Head radius 3 creates 6-voxel head. Suggested: radius 2 for 4-voxel head."

### Improvement 3: Gap Detection & Auto-Fill

**Add gap detection** to tools:

```python
# Enhanced tool response
fill_box(...)
# Returns: "Created box. Detected 2-voxel gap at y=26-27. Use fill_box to connect?"
```

**Or add auto-fill option**:
```python
fill_box(
    ...,
    auto_fill_gaps=True  # NEW: Automatically fill small gaps
)
```

### Improvement 4: Structure Validation Tool

**Enhance existing `find_connected_components`** to be more proactive:

```python
# Current: Only reports components
find_connected_components(filename)

# Enhanced: Also suggests fixes
find_connected_components(
    filename,
    suggest_fixes=True  # NEW: Suggest how to connect parts
)
```

**Returns**:
```json
{
    "components": [...],
    "issues": [
        {
            "type": "disconnected",
            "component1": {"bounds": {...}},
            "component2": {"bounds": {...}},
            "suggestion": "Add voxels at (4,20,8) to connect arm to torso"
        }
    ]
}
```

### Improvement 5: Smart Defaults Based on Model

**Enhance tools** to suggest positions based on existing model:

```python
# Enhanced create_cylinder
create_cylinder(
    filename="character",
    center_x=None,  # NEW: Auto-calculate if None
    center_y=None,
    center_z=None,
    radius=1,
    height=10,
    axis='y',
    color_index=1,
    attach_to="torso"  # NEW: Automatically position to attach
)
```

**Behavior**:
- If `attach_to="torso"`, find torso bounds
- Calculate position to connect arm to torso
- Place cylinder at correct position automatically

### Improvement 6: Validation After Operations

**Add validation step** that can be called after each operation:

```python
# New validation response in all tools
fill_box(...)
# Returns: 
# "Created box. Model validation: ✓ Connected, ✓ Symmetric, ⚠ Head too large (5 voxels, should be 4)"
```

**Or separate validation tool**:
```python
validate_model(
    filename,
    check_connections=True,
    check_proportions=True,
    check_symmetry=True
)
```

---

## Recommended Implementation Priority

### Phase 1: Quick Wins (High Impact, Low Effort)

1. **Add connection warnings** to tool responses
   - Check if new voxels connect to existing
   - Return warning if disconnected
   - **Effort**: Low - just add check in tool handlers

2. **Add gap detection** to tool responses
   - After placing parts, check for gaps
   - Suggest coordinates to fill gaps
   - **Effort**: Low - add gap detection logic

3. **Enhance `find_connected_components`** with suggestions
   - When multiple components found, suggest how to connect
   - **Effort**: Medium - need to calculate connection points

### Phase 2: Smart Features (Medium Impact, Medium Effort)

4. **Add proportional validation** to shape tools
   - Check if sphere/cylinder size is reasonable for model
   - Suggest correct sizes
   - **Effort**: Medium - need proportion calculation logic

5. **Add `ensure_connection` parameter** to placement tools
   - Auto-adjust coordinates to ensure connection
   - **Effort**: Medium - need connection detection and adjustment

### Phase 3: Advanced Features (High Impact, High Effort)

6. **Add `attach_to` parameter** for smart placement
   - Automatically position parts to connect
   - **Effort**: High - need model analysis and positioning logic

7. **Add comprehensive validation tool**
   - Check connections, proportions, symmetry
   - Suggest all fixes at once
   - **Effort**: High - comprehensive validation system

---

## Implementation Example

### Enhanced `fill_box` Tool

```python
@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    ...
    elif name == "fill_box":
        filename = arguments["filename"]
        x1, y1, z1 = arguments["x1"], arguments["y1"], arguments["z1"]
        x2, y2, z2 = arguments["x2"], arguments["y2"], arguments["z2"]
        color_index = arguments.get("color_index", 1)
        ensure_connection = arguments.get("ensure_connection", False)
        check_gaps = arguments.get("check_gaps", True)
        
        filepath = get_vox_path(filename)
        if not filepath.exists():
            return [TextContent(type="text", text=f"Error: File '{filename}' not found")]
        
        try:
            model = read_vox_file(filepath)
            
            # NEW: Check connections if requested
            if ensure_connection:
                # Check if box connects to existing voxels
                connects = False
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    for y in range(min(y1, y2), max(y1, y2) + 1):
                        for z in range(min(z1, z2), max(z1, z2) + 1):
                            # Check neighbors
                            for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                                if (x+dx, y+dy, z+dz) in model.voxels:
                                    connects = True
                                    break
                            if connects:
                                break
                        if connects:
                            break
                    if connects:
                        break
                
                if not connects:
                    return [TextContent(
                        type="text",
                        text=f"Warning: Box at ({x1},{y1},{z1}) to ({x2},{y2},{z2}) does not connect to existing parts. Set ensure_connection=False to place anyway."
                    )]
            
            # Fill the box
            model.fill_box(x1, y1, z1, x2, y2, z2, color_index)
            
            # NEW: Check for gaps
            if check_gaps:
                gaps = detect_gaps(model, x1, y1, z1, x2, y2, z2)
                if gaps:
                    gap_info = ", ".join([f"y={g}" for g in gaps[:3]])
                    write_vox_file(filepath, model)
                    return [TextContent(
                        type="text",
                        text=f"Filled box. Detected gaps at {gap_info}. Consider filling gaps for better connection."
                    )]
            
            write_vox_file(filepath, model)
            return [TextContent(type="text", text=f"Filled box from ({x1},{y1},{z1}) to ({x2},{y2},{z2})")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
```

---

## Summary

**Key Improvements**:
1. ✅ **Connection validation** - Check if parts connect
2. ✅ **Gap detection** - Find and report gaps
3. ✅ **Proportional validation** - Warn about incorrect sizes
4. ✅ **Smart suggestions** - Suggest fixes for issues
5. ✅ **Validation tools** - Check model structure

**Implementation Strategy**:
- Start with warnings and suggestions (Phase 1)
- Add optional auto-fix features (Phase 2)
- Build comprehensive validation (Phase 3)

**Result**: Tools will catch mistakes early and guide users to create better models!
