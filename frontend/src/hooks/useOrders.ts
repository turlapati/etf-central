import { useQuery } from "@tanstack/react-query";
import { listOrders } from "../api/etfOrders";

export function useOrders() {
  return useQuery({
    queryKey: ["orders"],
    queryFn: listOrders,
    refetchInterval: 5000,
  });
}
