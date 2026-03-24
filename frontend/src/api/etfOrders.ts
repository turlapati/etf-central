import { apiFetch } from "./client";
import type {
  InstanceResponse,
  InstanceDetailResponse,
  TransitionLogResponse,
  TriggerResponse,
  CreateInstanceRequest,
} from "./types";

export async function createOrder(context: Record<string, any>): Promise<InstanceResponse> {
  return apiFetch<InstanceResponse>("/api/state-machines/instances", {
    method: "POST",
    body: JSON.stringify({ workflow_name: "etf_order", context } satisfies CreateInstanceRequest),
  });
}

export async function listOrders(): Promise<InstanceResponse[]> {
  return apiFetch<InstanceResponse[]>(
    "/api/state-machines/instances?workflow_name=etf_order&limit=100"
  );
}

export async function getOrder(id: number): Promise<InstanceDetailResponse> {
  return apiFetch<InstanceDetailResponse>(`/api/state-machines/instances/${id}`);
}

export async function getHistory(id: number): Promise<TransitionLogResponse[]> {
  return apiFetch<TransitionLogResponse[]>(`/api/state-machines/instances/${id}/history`);
}

export async function fireTrigger(
  id: number,
  trigger: string,
  payload: Record<string, any> = {}
): Promise<TriggerResponse> {
  return apiFetch<TriggerResponse>(`/api/etf_order/${id}/${trigger}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
