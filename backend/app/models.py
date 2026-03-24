from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field
from datetime import datetime
import json


class ActionDefinition(SQLModel, table=True):
    """Reusable action library - marketplace of available actions."""
    
    __tablename__ = "action_definitions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, description="Unique identifier: send_email, debit_account")
    display_name: str = Field(description="Human-readable name")
    category: str = Field(index=True, description="communication, payment, validation, workflow_control")
    description: str = Field(description="What this action does")
    python_function: str = Field(description="Full path: app.actions.email.send_email")
    parameters_schema: str = Field(default="{}", description="JSON schema for parameters")
    is_async: bool = Field(default=False)
    timeout_seconds: int = Field(default=300)
    retry_policy: str = Field(default='{"max_attempts": 3, "backoff": "exponential"}', description="JSON retry config")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StateMachineDefinition(SQLModel, table=True):
    """State machine templates defining states, transitions, and triggers."""
    
    __tablename__ = "state_machine_definitions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Unique name: p2p_transfer, kyc")
    version: int = Field(default=1)
    mermaid_definition: str = Field(description="Mermaid state diagram with notes for metadata")
    initial_state: str = Field(description="Starting state for new instances")
    description: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True, description="Whether this version is active")
    parent_version_id: Optional[int] = Field(default=None, description="ID of previous version")
    change_log: Optional[str] = Field(default=None, description="What changed in this version")
    created_by: str = Field(default="system", description="Who created this version")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TransitionMetadata(SQLModel, table=True):
    """Detailed transition configuration extracted from Mermaid."""
    
    __tablename__ = "transition_metadata"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    state_machine_definition_id: int = Field(foreign_key="state_machine_definitions.id", index=True)
    from_state: str = Field(index=True)
    to_state: str = Field(index=True)
    trigger_name: str = Field(description="Event/trigger name")
    trigger_type: str = Field(default="api", description="api, manual, timer, webhook, automatic")
    guard_expression: Optional[str] = Field(default=None, description="Condition for transition")
    payload_schema: str = Field(default="{}", description="JSON Schema for trigger payload validation")
    is_actionless: bool = Field(default=False, description="True for pure state transitions")
    timeout_seconds: int = Field(default=30, description="Max execution time for this transition")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TransitionAction(SQLModel, table=True):
    """Maps actions to transitions (many-to-many relationship)."""
    
    __tablename__ = "transition_actions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    transition_metadata_id: int = Field(foreign_key="transition_metadata.id", index=True)
    action_definition_id: int = Field(foreign_key="action_definitions.id", index=True)
    execution_order: int = Field(default=1, description="Order for multiple actions")
    timing: str = Field(default="during", description="before, during, after transition")
    parameter_mapping: str = Field(default="{}", description="JSON: map context to action params")
    continue_on_error: bool = Field(default=False, description="Don't fail transition if action fails")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StateMachineInstance(SQLModel, table=True):
    """Running state machine instances tracking current state."""
    
    __tablename__ = "state_machine_instances"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    definition_id: int = Field(foreign_key="state_machine_definitions.id")
    current_state: str = Field(index=True)
    context: str = Field(default="{}", description="JSON string storing instance data")
    status: str = Field(default="active", index=True)  # active, completed, failed
    version: int = Field(default=1, description="Optimistic locking version")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def get_context(self) -> Dict[str, Any]:
        """Parse context JSON string to dict."""
        return json.loads(self.context) if self.context else {}
    
    def set_context(self, data: Dict[str, Any]) -> None:
        """Serialize dict to context JSON string."""
        self.context = json.dumps(data)
    
    def update_context(self, data: Dict[str, Any]) -> None:
        """Merge new data into existing context."""
        current = self.get_context()
        current.update(data)
        self.set_context(current)


class StateMachineTransitionLog(SQLModel, table=True):
    """Audit trail of all state transitions."""
    
    __tablename__ = "state_machine_transition_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    instance_id: int = Field(foreign_key="state_machine_instances.id", index=True)
    from_state: str
    to_state: str
    trigger_name: str = Field(description="Event/trigger that caused transition")
    trigger_type: str = Field(default="api")
    context_snapshot: str = Field(default="{}", description="Context at time of transition")
    triggered_by: Optional[str] = Field(default="system")
    error_message: Optional[str] = Field(default=None)
    correlation_id: Optional[str] = Field(default=None, index=True, description="End-to-end trace id (X-Correlation-Id header)")
    idempotency_key: Optional[str] = Field(default=None, index=True, description="Client-provided dedup key (Idempotency-Key header)")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowRelation(SQLModel, table=True):
    """Declarative relationships between workflows (parent/child linking)."""
    
    __tablename__ = "workflow_relations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    child_workflow: str = Field(index=True, description="Child workflow name, e.g. 'trade'")
    parent_workflow: str = Field(index=True, description="Parent workflow name, e.g. 'order'")
    context_key: str = Field(description="Key in child context holding parent instance id, e.g. 'order_id'")
    parent_id_type: str = Field(default="number", description="Type for comparison: 'number' or 'string'")
    created_from_state: Optional[str] = Field(default=None, description="Parent state that enables child creation, e.g. 'FILLED'")
    context_mapping: Optional[str] = Field(default=None, description="JSON mapping from parent context to child context")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskExecution(SQLModel, table=True):
    """Track individual action/task executions triggered by transitions."""
    
    __tablename__ = "task_executions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    transition_log_id: int = Field(foreign_key="state_machine_transition_logs.id", index=True)
    action_definition_id: int = Field(foreign_key="action_definitions.id", index=True)
    status: str = Field(default="pending", index=True, description="pending, running, completed, failed")
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    result: Optional[str] = Field(default=None, description="JSON result from action")
    error_message: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
