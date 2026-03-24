import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createOrder, fireTrigger } from "../api/etfOrders";
import type { OrderFormData } from "../components/OrderEntryPanel";

export function useCreateOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: OrderFormData) => {
      const ctx = {
        action: data.action,
        ticker: data.ticker,
        units: data.units,
        unit_size: data.unit_size,
        method: data.method,
        basket_type: data.basket_type,
      };

      const instance = await createOrder(ctx);

      // Auto-submit: fire SUBMIT trigger with the same payload.
      // This uses the "auto-submit collapse" pattern — the user fills one
      // form and the instance advances from NEW → SUBMITTED in one click.
      try {
        await fireTrigger(instance.id, "SUBMIT", ctx);
      } catch {
        // Non-fatal: order was still created in NEW state
      }

      return instance;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });
}
