"use client";
import { useState, useRef } from "react";

export default function TwapPage() {
  const [logs, setLogs] = useState([]);
  const wsRef = useRef(null);

  const connectWebSocket = () => {
    if (wsRef.current) return; // avoid multiple connections

    const ws = new WebSocket("ws://127.0.0.1:8000/ws-twap");
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("Connected to TWAP WebSocket ✅");
      ws.send(JSON.stringify({
        instId: "BTC-USDT",
        percent: 10,
        slices: 5,
        interval: 5
      }));
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      setLogs(prev => [...prev, msg]);

      // Reset wsRef if TWAP completed
      if (msg.status === "completed" || msg.status === "error") {
        wsRef.current = null;
      }
    };

    ws.onclose = (event) => {
      console.log("WebSocket closed:", event.code, event.reason);
      wsRef.current = null;
    };

    ws.onerror = (err) => console.error("WebSocket error:", err);
  };

  const cancelTwap = () => {
    if (wsRef.current) {
      // send a cancel command to backend
      wsRef.current.send(JSON.stringify({ action: "cancel" }));
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>TWAP Execution Logs</h1>

      <button onClick={connectWebSocket} style={{ marginRight: "10px", padding: "10px" }}>
        Start TWAP
      </button>

      <button onClick={cancelTwap} style={{ padding: "10px" }}>
        Cancel TWAP
      </button>

      <div style={{
        border: "1px solid gray",
        padding: "10px",
        height: "400px",
        overflowY: "scroll",
        marginTop: "20px"
      }}>
        {logs.map((log, i) => (
          <div key={i}>
            {log.status} {log.slice ? `- Slice ${log.slice}/${log.total_slices}` : ""} {log.message || ""}
          </div>
        ))}
      </div>
    </div>
  );
}
