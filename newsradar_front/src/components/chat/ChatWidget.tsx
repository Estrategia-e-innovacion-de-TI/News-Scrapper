/**
 * ChatWidget — Optional chat widget that connects to the AI agent
 * via the backend WebSocket proxy at /api/chat.
 */
import React, { useState, useRef, useEffect, useCallback } from "react";
import { connectChat } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  text: string;
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!open) return;

    const ws = connectChat();
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: data.message ?? data.error ?? event.data },
        ]);
      } catch {
        setMessages((prev) => [...prev, { role: "assistant", text: event.data }]);
      }
    };

    ws.onerror = () => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Error de conexión con el agente." },
      ]);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [open]);

  const send = useCallback(() => {
    if (!input.trim() || !wsRef.current) return;
    wsRef.current.send(input);
    setMessages((prev) => [...prev, { role: "user", text: input }]);
    setInput("");
  }, [input]);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{ position: "fixed", bottom: 24, right: 24 }}
        aria-label="Abrir chat"
      >
        💬 Chat
      </button>
    );
  }

  return (
    <div
      style={{
        position: "fixed",
        bottom: 24,
        right: 24,
        width: 360,
        maxHeight: 480,
        border: "1px solid #ccc",
        borderRadius: 8,
        background: "#fff",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ padding: 8, borderBottom: "1px solid #eee", display: "flex", justifyContent: "space-between" }}>
        <strong>Chat ARAS / Riesgos</strong>
        <button onClick={() => setOpen(false)} aria-label="Cerrar chat">✕</button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 8 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ textAlign: m.role === "user" ? "right" : "left", margin: "4px 0" }}>
            <span
              style={{
                display: "inline-block",
                padding: "4px 8px",
                borderRadius: 4,
                background: m.role === "user" ? "#0070f3" : "#f0f0f0",
                color: m.role === "user" ? "#fff" : "#000",
              }}
            >
              {m.text}
            </span>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", borderTop: "1px solid #eee" }}>
        <input
          style={{ flex: 1, padding: 8, border: "none" }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Escribe tu pregunta..."
          aria-label="Mensaje de chat"
        />
        <button onClick={send} aria-label="Enviar mensaje">Enviar</button>
      </div>
    </div>
  );
}
