"""
TransitionMetadataService: Populates TransitionMetadata and TransitionAction tables
when a StateMachineDefinition is created or updated.

This bridges the gap between Mermaid diagram definitions and the database tables
that the TriggerExecutionEngine uses for action execution.
"""
import json
import logging
from typing import List, Optional

from sqlmodel import Session, select

from app.models import (
    StateMachineDefinition,
    TransitionMetadata,
    TransitionAction,
    ActionDefinition
)
from app.engine import MermaidParser, Transition

logger = logging.getLogger(__name__)


class TransitionMetadataService:
    """
    Service to extract and persist transition metadata from Mermaid definitions.
    
    Called when:
    - A new StateMachineDefinition is created
    - An existing StateMachineDefinition is updated (new version)
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def populate_for_definition(self, definition: StateMachineDefinition) -> int:
        """
        Extract transitions from Mermaid and populate TransitionMetadata + TransitionAction.
        
        Args:
            definition: The StateMachineDefinition to process
            
        Returns:
            Number of TransitionMetadata records created
        """
        # Parse the Mermaid definition
        parser = MermaidParser(definition.mermaid_definition)
        
        # Clear existing metadata for this definition (in case of re-processing)
        self._clear_existing_metadata(definition.id)
        
        # Create TransitionMetadata for each transition
        count = 0
        for transition in parser.transitions:
            metadata = self._create_transition_metadata(definition.id, transition)
            self.session.add(metadata)
            self.session.flush()  # Get the ID for linking actions
            
            # Create TransitionAction records for each action
            self._create_transition_actions(metadata, transition.actions)
            count += 1
        
        self.session.commit()
        logger.info(f"Populated {count} transition metadata records for definition {definition.id}")
        return count
    
    def _clear_existing_metadata(self, definition_id: int) -> None:
        """Remove existing TransitionMetadata and related TransitionActions."""
        # Find existing metadata
        statement = select(TransitionMetadata).where(
            TransitionMetadata.state_machine_definition_id == definition_id
        )
        existing = self.session.exec(statement).all()
        
        for meta in existing:
            # Delete related TransitionActions first
            action_stmt = select(TransitionAction).where(
                TransitionAction.transition_metadata_id == meta.id
            )
            actions = self.session.exec(action_stmt).all()
            for action in actions:
                self.session.delete(action)
            
            self.session.delete(meta)
        
        self.session.flush()
    
    def _create_transition_metadata(
        self,
        definition_id: int,
        transition: Transition
    ) -> TransitionMetadata:
        """Create a TransitionMetadata record from a parsed Transition."""
        # Convert payload schema to JSON string
        payload_schema_str = json.dumps(transition.payload_schema) if transition.payload_schema else "{}"
        
        # Convert guards list to expression string
        guard_expression = None
        if transition.guards:
            guard_expression = "\n".join(transition.guards)
        
        return TransitionMetadata(
            state_machine_definition_id=definition_id,
            from_state=transition.source,
            to_state=transition.target,
            trigger_name=transition.trigger_name or "",
            trigger_type=transition.trigger_type,
            guard_expression=guard_expression,
            payload_schema=payload_schema_str,
            is_actionless=transition.is_actionless,
            timeout_seconds=transition.timeout_seconds
        )
    
    def _create_transition_actions(
        self,
        metadata: TransitionMetadata,
        action_names: List[str]
    ) -> None:
        """Create TransitionAction records linking metadata to ActionDefinitions."""
        for order, action_name in enumerate(action_names, start=1):
            # Look up the ActionDefinition
            action_def = self._get_action_definition(action_name)
            
            if not action_def:
                logger.warning(
                    f"Action '{action_name}' not found in database for transition "
                    f"{metadata.from_state} -> {metadata.to_state}"
                )
                continue
            
            transition_action = TransitionAction(
                transition_metadata_id=metadata.id,
                action_definition_id=action_def.id,
                execution_order=order,
                timing="during",
                parameter_mapping="{}",
                continue_on_error=False
            )
            self.session.add(transition_action)
    
    def _get_action_definition(self, action_name: str) -> Optional[ActionDefinition]:
        """Look up an ActionDefinition by name."""
        statement = select(ActionDefinition).where(ActionDefinition.name == action_name)
        return self.session.exec(statement).first()
    
    def get_metadata_for_definition(
        self,
        definition_id: int
    ) -> List[TransitionMetadata]:
        """Get all TransitionMetadata for a definition."""
        statement = select(TransitionMetadata).where(
            TransitionMetadata.state_machine_definition_id == definition_id
        )
        return list(self.session.exec(statement).all())
    
    def get_actions_for_transition(
        self,
        metadata_id: int
    ) -> List[tuple]:
        """Get TransitionAction and ActionDefinition pairs for a transition."""
        statement = select(TransitionAction, ActionDefinition).join(
            ActionDefinition,
            TransitionAction.action_definition_id == ActionDefinition.id
        ).where(
            TransitionAction.transition_metadata_id == metadata_id
        ).order_by(TransitionAction.execution_order)
        
        return list(self.session.exec(statement).all())


def populate_transition_metadata(
    session: Session,
    definition: StateMachineDefinition
) -> int:
    """
    Convenience function to populate transition metadata for a definition.
    
    Args:
        session: Database session
        definition: The StateMachineDefinition to process
        
    Returns:
        Number of TransitionMetadata records created
    """
    service = TransitionMetadataService(session)
    return service.populate_for_definition(definition)
