import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class Transition:
    """Represents a state transition with metadata."""
    source: str
    target: str
    trigger_name: Optional[str] = None
    trigger_type: str = "api"
    actions: List[str] = field(default_factory=list)
    guards: List[str] = field(default_factory=list)
    is_actionless: bool = False
    payload_schema: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30


class MermaidParser:
    """Parses Mermaid state diagrams with extended metadata via notes."""
    
    TRANSITION_PATTERN = re.compile(r"(\w+)\s*-->\s*(\w+)(?:\s*:\s*(\w+))?")
    INITIAL_STATE_PATTERN = re.compile(r"\[\*\]\s*-->\s*(\w+)")
    NOTE_PATTERN = re.compile(r"note\s+(right|left)\s+of\s+(\w+)(.*?)end note", re.DOTALL | re.IGNORECASE)
    ENUM_PATTERN = re.compile(r"\[([^\]]*)\]")
    
    def __init__(self, mermaid_str: str):
        self.mermaid_str = mermaid_str
        self.transitions: List[Transition] = []
        self.notes: Dict[str, Dict[str, Any]] = {}
        self.initial_state: Optional[str] = None
        self._parse()
    
    def _parse(self) -> None:
        """Extract transitions and notes from Mermaid string."""
        self._parse_notes()
        self._parse_transitions()
    
    def _parse_notes(self) -> None:
        """Parse note blocks for metadata."""
        for match in self.NOTE_PATTERN.finditer(self.mermaid_str):
            position, state, content = match.groups()
            metadata = self._parse_note_content(content.strip())
            self.notes[state] = metadata
    
    def _parse_note_content(self, content: str) -> Dict[str, Any]:
        """Parse note content into structured metadata.
        
        Supports payload schema definition in notes:
            payload:
                amount: number, required
                account_id: string, required
                memo: string, optional
        """
        metadata = {
            "trigger_type": "api",
            "actions": [],
            "guards": [],
            "actionless": False,
            "payload_schema": {},
            "timeout_seconds": 30
        }
        
        in_payload_block = False
        in_guards_block = False
        payload_lines = []
        guard_lines = []
        
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            
            # Check for block starts (case-insensitive)
            if line_lower.startswith("payload:"):
                in_payload_block = True
                in_guards_block = False
                inline = line.split(":", 1)[1].strip()
                if inline:
                    payload_lines.append(inline)
                continue
            elif line_lower.startswith("guards:"):
                in_guards_block = True
                in_payload_block = False
                inline = line.split(":", 1)[1].strip()
                if inline:
                    metadata["guards"] = [g.strip() for g in inline.split(",")]
                continue
            
            # Check for other field starts (ends current block, case-insensitive)
            if any(line_lower.startswith(kw) for kw in ("trigger_type:", "actions:", "actionless:", "timeout:", "description:")):
                in_payload_block = False
                in_guards_block = False
            
            # Collect block content
            if in_payload_block:
                if line.startswith("-"):
                    line = line[1:].strip()
                payload_lines.append(line)
                continue
            
            if in_guards_block:
                if line.startswith("-"):
                    line = line[1:].strip()
                guard_lines.append(line)
                continue
            
            # Parse simple key-value fields (case-insensitive)
            if line_lower.startswith("trigger_type:"):
                metadata["trigger_type"] = line.split(":", 1)[1].strip()
            elif line_lower.startswith("actions:"):
                actions_str = line.split(":", 1)[1].strip()
                if actions_str:
                    metadata["actions"] = [a.strip() for a in actions_str.split(",")]
            elif line_lower.startswith("actionless:"):
                metadata["actionless"] = line.split(":", 1)[1].strip().lower() == "true"
            elif line_lower.startswith("timeout:"):
                try:
                    metadata["timeout_seconds"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
        
        # Process collected guard lines
        if guard_lines:
            metadata["guards"] = guard_lines
        
        # Process collected payload lines into JSON Schema
        if payload_lines:
            metadata["payload_schema"] = self._parse_payload_schema(payload_lines)
        
        return metadata
    
    def _parse_payload_schema(self, lines: List[str]) -> Dict[str, Any]:
        """Parse payload field definitions into JSON Schema format.
        
        Input format:
            field_name: type, required/optional ['OPT1', 'OPT2']
            
        Matches frontend parser behaviour:
        - Fields default to **optional** when neither required/optional is specified
        - Inline enum options ``[A, B]`` are captured in the ``enum`` keyword
        - Extra type aliases (date, datetime, decimal, json, map) accepted
        
        Output: JSON Schema object
        """
        schema: Dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        type_mapping = {
            "string": "string",
            "str": "string",
            "number": "number",
            "float": "number",
            "decimal": "number",
            "integer": "integer",
            "int": "integer",
            "boolean": "boolean",
            "bool": "boolean",
            "object": "object",
            "dict": "object",
            "json": "object",
            "map": "object",
            "array": "array",
            "list": "array",
            "date": "string",
            "datetime": "string",
        }
        
        for line in lines:
            if ":" not in line:
                continue
            
            parts = line.split(":", 1)
            field_name = parts[0].strip()
            field_spec = parts[1].strip() if len(parts) > 1 else "string"
            
            # Extract inline enum options before splitting by comma
            enum_values: Optional[List[str]] = None
            enum_match = self.ENUM_PATTERN.search(field_spec)
            if enum_match:
                raw_opts = enum_match.group(1)
                enum_values = [
                    o.strip().strip("'\"")
                    for o in raw_opts.split(",")
                    if o.strip()
                ]
                field_spec = self.ENUM_PATTERN.sub("", field_spec)
            
            # Remove trailing parenthesised annotations e.g. (min: 1)
            field_spec = re.sub(r"\(.*?\)", "", field_spec).strip()
            
            spec_parts = [p.strip().lower() for p in field_spec.split(",") if p.strip()]
            
            field_type = "string"
            is_required = False  # default to optional (matches frontend guide)
            
            for part in spec_parts:
                if part in type_mapping:
                    field_type = type_mapping[part]
                elif part == "required":
                    is_required = True
                elif part == "optional":
                    is_required = False
            
            prop: Dict[str, Any] = {"type": field_type}
            if enum_values:
                prop["enum"] = enum_values
            schema["properties"][field_name] = prop
            
            if is_required:
                schema["required"].append(field_name)
        
        return schema
    
    def _resolve_note_metadata(self, source: str, target: str) -> Dict[str, Any]:
        """Resolve note metadata with target-first, source-fallback strategy.
        
        Matches the frontend parser contract: look up the note on the target
        state first; if not found (or has no payload section), fall back to
        the source state note.
        """
        target_meta = self.notes.get(target, {})
        if target_meta:
            return target_meta
        return self.notes.get(source, {})
    
    def _parse_transitions(self) -> None:
        """Extract transitions and merge with note metadata."""
        for line in self.mermaid_str.splitlines():
            line = line.strip()
            
            if not line or line.startswith("%%") or line.lower().startswith("statediagram"):
                continue
            
            # Skip direction and state declarations
            if line.lower().startswith("direction ") or line.lower().startswith("state "):
                continue
            
            if "[*]" in line:
                match = self.INITIAL_STATE_PATTERN.search(line)
                if match:
                    self.initial_state = match.group(1)
                continue
                
            if "note" in line.lower():
                continue
            
            match = self.TRANSITION_PATTERN.search(line)
            if match:
                source, target, trigger = match.groups()
                
                metadata = self._resolve_note_metadata(source, target)
                
                transition = Transition(
                    source=source,
                    target=target,
                    trigger_name=trigger,
                    trigger_type=metadata.get("trigger_type", "api"),
                    actions=metadata.get("actions", []),
                    guards=metadata.get("guards", []),
                    is_actionless=metadata.get("actionless", False),
                    payload_schema=metadata.get("payload_schema", {}),
                    timeout_seconds=metadata.get("timeout_seconds", 30)
                )
                
                self.transitions.append(transition)
    
    def validate(self, available_actions: Optional[List[str]] = None) -> List[str]:
        """Validate diagram and return errors."""
        errors = []
        
        if not self.transitions:
            errors.append("No valid transitions found in Mermaid diagram")
        
        seen = set()
        for t in self.transitions:
            if t.trigger_name:
                key = (t.source, t.trigger_name)
                if key in seen:
                    errors.append(f"Duplicate transition: {t.source} + {t.trigger_name}")
                seen.add(key)
        
        if available_actions is not None:
            for t in self.transitions:
                if not t.is_actionless and not t.actions:
                    errors.append(
                        f"Transition {t.source} -> {t.target} ({t.trigger_name}) "
                        f"has no actions and is not marked as actionless"
                    )
                
                for action_name in t.actions:
                    if action_name not in available_actions:
                        errors.append(f"Action '{action_name}' not found in action library")
        
        return errors
    
    def get_transitions_from(self, state: str) -> List[Transition]:
        """Get all transitions from a state."""
        return [t for t in self.transitions if t.source == state]
    
    def get_transition(self, from_state: str, trigger_name: str) -> Optional[Transition]:
        """Get specific transition by state and trigger."""
        for t in self.transitions:
            if t.source == from_state and t.trigger_name == trigger_name:
                return t
        return None
    
    def get_all_states(self) -> set:
        """Get all unique states."""
        states = set()
        for t in self.transitions:
            states.add(t.source)
            states.add(t.target)
        return states


class StateMachine:
    """Validates and manages state transitions for a state machine instance."""
    
    def __init__(self, mermaid_definition: str, current_state: str, validate_actions: bool = False):
        self.parser = MermaidParser(mermaid_definition)
        self.current_state = current_state
        
        available_actions = None
        if validate_actions:
            from app.registry import get_action_names
            available_actions = get_action_names()
        
        errors = self.parser.validate(available_actions)
        if errors:
            raise ValueError(f"Invalid Mermaid definition: {'; '.join(errors)}")
    
    def can_transition(self, trigger_name: str) -> bool:
        """Check if a trigger is valid from the current state."""
        return self.get_next_state(trigger_name) is not None
    
    def get_next_state(self, trigger_name: str) -> Optional[str]:
        """Get the target state for a trigger, or None if invalid."""
        for transition in self.parser.transitions:
            if transition.source == self.current_state and transition.trigger_name == trigger_name:
                return transition.target
        return None
    
    def get_transition(self, trigger_name: str) -> Optional[Transition]:
        """Get the full transition object for a trigger."""
        return self.parser.get_transition(self.current_state, trigger_name)
    
    def get_available_triggers(self) -> List[str]:
        """Get all valid triggers from the current state."""
        triggers = []
        for transition in self.parser.get_transitions_from(self.current_state):
            if transition.trigger_name:
                triggers.append(transition.trigger_name)
        return triggers

    def get_available_triggers_with_schema(self) -> List[Dict[str, Any]]:
        """Get all valid triggers from the current state, including payload schemas."""
        triggers = []
        for transition in self.parser.get_transitions_from(self.current_state):
            if transition.trigger_name:
                triggers.append({
                    "name": transition.trigger_name,
                    "payload_schema": transition.payload_schema or {},
                })
        return triggers
    
    def is_terminal_state(self) -> bool:
        """Check if current state has no outgoing transitions."""
        return len(self.parser.get_transitions_from(self.current_state)) == 0
    
    def get_all_states(self) -> set:
        """Get all states in the state machine."""
        return self.parser.get_all_states()
