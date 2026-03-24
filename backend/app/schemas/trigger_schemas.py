"""
Dynamic Pydantic model generation from JSON Schema.

This module creates Pydantic models at runtime based on JSON Schema
definitions extracted from Mermaid notes or stored in TransitionMetadata.
"""
import json
from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel, Field, create_model, ValidationError


def json_schema_to_pydantic_field(field_name: str, field_schema: Dict[str, Any], required: bool) -> tuple:
    """
    Convert a JSON Schema field definition to Pydantic field specification.
    
    Args:
        field_name: Name of the field
        field_schema: JSON Schema definition for the field
        required: Whether the field is required
        
    Returns:
        Tuple of (type, Field) for use with create_model
    """
    json_type = field_schema.get("type", "string")
    
    type_mapping = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "object": dict,
        "array": list,
        "null": type(None)
    }
    
    python_type = type_mapping.get(json_type, str)
    
    # Handle optional fields
    if not required:
        python_type = Optional[python_type]
        default = Field(default=None)
    else:
        default = Field(...)
    
    # Add description if present
    if "description" in field_schema:
        default = Field(default=... if required else None, description=field_schema["description"])
    
    return (python_type, default)


def create_payload_model(
    schema: Dict[str, Any],
    model_name: str = "TriggerPayload"
) -> Type[BaseModel]:
    """
    Create a Pydantic model from a JSON Schema.
    
    Args:
        schema: JSON Schema object with 'properties' and 'required' keys
        model_name: Name for the generated model class
        
    Returns:
        Dynamically created Pydantic model class
    """
    if not schema or not schema.get("properties"):
        # Return a model that accepts any dict
        return create_model(model_name, __base__=BaseModel)
    
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    
    field_definitions = {}
    
    for field_name, field_schema in properties.items():
        is_required = field_name in required_fields
        python_type, field_default = json_schema_to_pydantic_field(
            field_name, field_schema, is_required
        )
        field_definitions[field_name] = (python_type, field_default)
    
    # Create the model dynamically
    model = create_model(model_name, **field_definitions)
    
    return model


def validate_payload(
    payload: Dict[str, Any],
    schema: Dict[str, Any],
    model_name: str = "TriggerPayload"
) -> Dict[str, Any]:
    """
    Validate a payload against a JSON Schema.
    
    Args:
        payload: The payload data to validate
        schema: JSON Schema to validate against
        model_name: Name for error messages
        
    Returns:
        Dict with 'valid' (bool), 'data' (validated data), and 'errors' (list of error dicts)
    """
    if not schema or not schema.get("properties"):
        # No schema defined, accept any payload
        return {
            "valid": True,
            "data": payload,
            "errors": []
        }
    
    try:
        model_class = create_payload_model(schema, model_name)
        validated = model_class(**payload)
        
        return {
            "valid": True,
            "data": validated.model_dump(),
            "errors": []
        }
    except ValidationError as e:
        errors = []
        for error in e.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        return {
            "valid": False,
            "data": None,
            "errors": errors
        }


def merge_schemas(
    mermaid_schema: Dict[str, Any],
    db_schema: Optional[Dict[str, Any]],
    action_schema: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Merge payload schemas from multiple sources.
    
    Priority (highest to lowest):
    1. DB override (TransitionMetadata.payload_schema)
    2. Mermaid notes
    3. Action parameters (inferred)
    
    Args:
        mermaid_schema: Schema extracted from Mermaid notes
        db_schema: Schema from TransitionMetadata table (override)
        action_schema: Schema inferred from action parameters
        
    Returns:
        Merged JSON Schema
    """
    # DB override takes precedence
    if db_schema and db_schema.get("properties"):
        return db_schema
    
    # Then Mermaid notes
    if mermaid_schema and mermaid_schema.get("properties"):
        return mermaid_schema
    
    # Finally, action parameters
    if action_schema and action_schema.get("properties"):
        return action_schema
    
    # No schema defined
    return {}


def infer_schema_from_actions(action_schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Infer a combined payload schema from multiple action parameter schemas.
    
    Args:
        action_schemas: List of JSON Schema objects from ActionDefinition.parameters_schema
        
    Returns:
        Combined JSON Schema with all required parameters
    """
    combined = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    for schema in action_schemas:
        if not schema:
            continue
            
        # Parse if string
        if isinstance(schema, str):
            try:
                schema = json.loads(schema)
            except json.JSONDecodeError:
                continue
        
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        for field_name, field_def in properties.items():
            if field_name not in combined["properties"]:
                combined["properties"][field_name] = field_def
                if field_name in required:
                    combined["required"].append(field_name)
    
    return combined


class PayloadValidator:
    """
    Validates trigger payloads using the hybrid schema approach.
    
    Schema sources (priority order):
    1. DB override (TransitionMetadata.payload_schema)
    2. Mermaid notes (Transition.payload_schema)
    3. Action parameters (inferred from ActionDefinition.parameters_schema)
    """
    
    def __init__(
        self,
        mermaid_schema: Optional[Dict[str, Any]] = None,
        db_schema: Optional[Dict[str, Any]] = None,
        action_schemas: Optional[List[Dict[str, Any]]] = None
    ):
        self.mermaid_schema = mermaid_schema or {}
        self.db_schema = db_schema or {}
        self.action_schemas = action_schemas or []
        
        # Compute effective schema
        action_inferred = infer_schema_from_actions(self.action_schemas) if self.action_schemas else {}
        self.effective_schema = merge_schemas(
            self.mermaid_schema,
            self.db_schema if self.db_schema.get("properties") else None,
            action_inferred
        )
    
    def validate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a payload against the effective schema.
        
        Returns:
            Dict with 'valid', 'data', and 'errors' keys
        """
        return validate_payload(payload, self.effective_schema)
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the effective JSON Schema."""
        return self.effective_schema
    
    def has_schema(self) -> bool:
        """Check if any schema is defined."""
        return bool(self.effective_schema.get("properties"))
