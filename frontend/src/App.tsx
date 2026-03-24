import { useState, useEffect } from "react";
import Header from "./components/Header";
import StatusBar from "./components/StatusBar";
import OrderEntryPanel from "./components/OrderEntryPanel";
import MarketColorRow from "./components/MarketColorRow";
import OrderBlotter from "./components/OrderBlotter";
import PositionsPanel from "./components/PositionsPanel";
import OrderDetailPanel from "./components/OrderDetailPanel";
import { useOrders } from "./hooks/useOrders";
import { useCreateOrder } from "./hooks/useCreateOrder";
import type { InstanceResponse } from "./api/types";

export default function App() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedOrder, setSelectedOrder] = useState<InstanceResponse | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const { data: orders = [], isError, refetch } = useOrders();
  const createOrder = useCreateOrder();

  useEffect(() => {
    if (createOrder.isSuccess) {
      setToast({ type: "success", message: "Order submitted" });
      const t = setTimeout(() => setToast(null), 2000);
      return () => clearTimeout(t);
    }
    if (createOrder.isError) {
      setToast({ type: "error", message: (createOrder.error as Error).message });
      const t = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(t);
    }
  }, [createOrder.isSuccess, createOrder.isError, createOrder.error]);

  const connected = !isError;

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Header
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onNewTrade={() => {}}
        onRefresh={() => refetch()}
      />

      <div className="flex-1 flex flex-col overflow-hidden p-1.5 gap-1.5">
        {/* Top: Sidebar + Charts/Blotter */}
        <div className="flex gap-1.5 flex-[3] min-h-0">
          <OrderEntryPanel
            onSubmit={(data) => createOrder.mutate(data)}
            isSubmitting={createOrder.isPending}
          />

          <div className="flex-1 flex flex-col gap-1.5 overflow-hidden">
            <MarketColorRow />
            <OrderBlotter
              orders={orders}
              searchQuery={searchQuery}
              onSelectOrder={setSelectedOrder}
              selectedOrderId={selectedOrder?.id ?? null}
            />
          </div>

          {selectedOrder && (
            <OrderDetailPanel
              order={selectedOrder}
              onClose={() => setSelectedOrder(null)}
            />
          )}
        </div>

        {/* Bottom: Positions */}
        <PositionsPanel />
      </div>

      <StatusBar connected={connected} latencyMs={connected ? 4 : 0} />

      {toast && (
        <div
          className={`fixed bottom-8 right-4 px-4 py-2 rounded shadow-lg text-xs font-bold z-50 ${
            toast.type === "error"
              ? "bg-accent-red/90 text-white"
              : "bg-accent-green/90 text-bg-main"
          }`}
        >
          {toast.message}
        </div>
      )}
    </div>
  );
}
