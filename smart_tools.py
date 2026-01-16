#!/usr/bin/env python3
"""
Smart tools that use intelligence layer for enhanced MCP operations
"""

from typing import Any, Dict, List
from pathlib import Path
from intelligence import MCPIntelligence

class SmartMCPTools:
    """Smart wrapper around MCP tools with intelligence"""
    
    def __init__(self, vox_dir: Path):
        self.intelligence = MCPIntelligence(vox_dir)
    
    def smart_create_model(self, filename: str, template: Optional[str] = None, 
                          width: Optional[int] = None, height: Optional[int] = None, 
                          depth: Optional[int] = None) -> Dict[str, Any]:
        """Smart model creation with template support"""
        # Use template if provided
        if template:
            template_data = self.intelligence.get_template(template)
            if template_data:
                dims = template_data["dimensions"]
                width = width or dims[0]
                height = height or dims[1]
                depth = depth or dims[2]
        
        # Get smart defaults
        defaults = self.intelligence.get_smart_defaults("create_voxel_model", filename)
        if defaults.get("suggested_dimensions"):
            width = width or defaults["suggested_dimensions"][0]
            height = height or defaults["suggested_dimensions"][1]
            depth = depth or defaults["suggested_dimensions"][2]
        
        # Use reasonable defaults
        width = width or 16
        height = height or 32
        depth = depth or 16
        
        # Validate
        is_valid, error = self.intelligence.validate_operation(
            "create_voxel_model",
            {"width": width, "height": height, "depth": depth}
        )
        
        if not is_valid:
            return {"success": False, "error": error}
        
        return {
            "success": True,
            "filename": filename,
            "width": width,
            "height": height,
            "depth": depth,
            "suggestions": self.intelligence.suggest_next_operations(filename)
        }
    
    def smart_create_sphere(self, filename: str, material: Optional[str] = None,
                           center_x: Optional[int] = None, center_y: Optional[int] = None,
                           center_z: Optional[int] = None, radius: Optional[int] = None) -> Dict[str, Any]:
        """Smart sphere creation with material-based colors"""
        # Get model info for defaults
        model_info = self.intelligence._get_model_info(filename)
        if not model_info:
            return {"success": False, "error": f"Model '{filename}' not found"}
        
        dims = model_info["dimensions"]
        
        # Smart defaults
        defaults = self.intelligence.get_smart_defaults("create_sphere", filename)
        center_x = center_x or defaults.get("suggested_position", [dims["x"]//2])[0]
        center_y = center_y or defaults.get("suggested_position", [0, dims["y"]//2, 0])[1]
        center_z = center_z or defaults.get("suggested_position", [0, 0, dims["z"]//2])[2]
        radius = radius or defaults.get("suggested_radius", 5)
        
        # Get color from material
        color_index = 1  # Default
        if material:
            color_rgb = self.intelligence.suggest_color(material)
            if color_rgb:
                # Would need to set palette color, but for now use index
                color_index = 1
        
        # Validate
        is_valid, error = self.intelligence.validate_operation(
            "create_sphere",
            {
                "center_x": center_x,
                "center_y": center_y,
                "center_z": center_z,
                "radius": radius
            },
            filename
        )
        
        if not is_valid:
            return {"success": False, "error": error}
        
        return {
            "success": True,
            "filename": filename,
            "center_x": center_x,
            "center_y": center_y,
            "center_z": center_z,
            "radius": radius,
            "color_index": color_index,
            "material": material
        }
    
    def get_suggestions(self, model_name: str) -> List[str]:
        """Get suggestions for a model"""
        return self.intelligence.suggest_next_operations(model_name)
    
    def get_templates(self) -> List[str]:
        """Get available templates"""
        return self.intelligence.list_templates()