export interface InstanceResponse {
  id: number;
  definition_id: number;
  workflow_name: string;
  current_state: string;
  status: string;
  context: Record<string, any>;
  version: number;
  created_at: string;
  updated_at: string;
  available_events?: string[];
}

export interface TriggerSchema {
  name: string;
  payload_schema: {
    type?: string;
    properties?: Record<string, {
      type: string;
      enum?: string[];
      description?: string;
    }>;
    required?: string[];
  };
}

export interface InstanceDetailResponse extends InstanceResponse {
  available_events: string[];
  available_triggers: TriggerSchema[];
  mermaid_definition: string;
}

export interface TransitionLogResponse {
  id: number;
  from_state: string;
  to_state: string;
  event: string;
  triggered_by: string | null;
  context_snapshot: Record<string, any>;
  error_message: string | null;
  created_at: string;
}

export interface TriggerResponse {
  success: boolean;
  instance_id: number;
  previous_state: string;
  new_state: string;
  trigger_name: string;
  execution_mode: string;
  version: number;
  error?: string;
  action_results?: Record<string, any>[];
}

export interface CreateInstanceRequest {
  workflow_name: string;
  context: Record<string, any>;
}
