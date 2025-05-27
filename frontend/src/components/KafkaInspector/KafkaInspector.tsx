import React, { useState, useEffect, useRef } from "react";
import "./KafkaInspector.css";

interface KafkaMessage {
  id: string;
  data: any; // Consider defining a more specific type based on expected message structure
  timestamp: number;
}

const KafkaInspector: React.FC = () => {
  const [messages, setMessages] = useState<KafkaMessage[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);

  const MAX_MESSAGES = 50;

  useEffect(() => {
    const connectWebSocket = () => {
      // Determine WebSocket URL (ws or wss)
      const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      // Assuming backend is served on the same host/port or VITE_API_URL points to the base HTTP URL for the backend.
      // If VITE_API_URL is http://localhost:8000, then ws URL is ws://localhost:8000/ws/kafka-inspector
      const backendHost = import.meta.env.VITE_API_URL
        ? new URL(import.meta.env.VITE_API_URL).host
        : window.location.host;
      const wsUrl = `${wsProtocol}//${backendHost}/ws/kafka-inspector`;

      console.log(`Attempting to connect WebSocket to: ${wsUrl}`);
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log("Kafka Inspector WebSocket connected");
        setIsConnected(true);
        setError(null);
      };

      ws.current.onmessage = (event) => {
        try {
          const rawMessage = event.data;
          // console.log('Raw message received:', rawMessage);
          const parsedMessage = JSON.parse(rawMessage);
          setMessages((prevMessages) =>
            [
              {
                id: `msg-${Date.now()}-${Math.random()}`,
                data: parsedMessage,
                timestamp: Date.now(),
              },
              ...prevMessages,
            ].slice(0, MAX_MESSAGES),
          ); // Keep only the latest MAX_MESSAGES
        } catch (e) {
          console.error("Error parsing WebSocket message:", e);
          setError("Error parsing message from server.");
        }
      };

      ws.current.onerror = (event) => {
        console.error("Kafka Inspector WebSocket error:", event);
        setError("WebSocket connection error. Check console.");
        setIsConnected(false);
      };

      ws.current.onclose = (event) => {
        console.log(
          "Kafka Inspector WebSocket disconnected:",
          event.reason,
          event.code,
        );
        setIsConnected(false);
        // Optional: implement a reconnect strategy
        if (!event.wasClean) {
          setError("WebSocket disconnected. Attempting to reconnect in 5s...");
          setTimeout(() => {
            connectWebSocket();
          }, 5000);
        }
      };
    };

    connectWebSocket();

    return () => {
      if (ws.current) {
        console.log("Closing Kafka Inspector WebSocket");
        ws.current.close(1000, "Component unmounting"); // Clean close
      }
    };
  }, []);

  return (
    <div className="kafka-inspector">
      <div className="kafka-inspector-header">
        <h3>Kafka Inspector</h3>
        <span>
          Status:{" "}
          {isConnected ? (
            <span style={{ color: "green" }}>Connected</span>
          ) : (
            <span style={{ color: "red" }}>Disconnected</span>
          )}
        </span>
      </div>
      {error && (
        <div
          style={{
            padding: "10px",
            color: "red",
            borderBottom: "1px solid #ccc",
          }}
        >
          Error: {error}
        </div>
      )}
      <div className="kafka-inspector-messages">
        {messages.length === 0 && <p>No messages received yet. Listening...</p>}
        {messages.map((msg) => (
          <div key={msg.id} className="kafka-inspector-message">
            <strong>{new Date(msg.timestamp).toLocaleTimeString()}</strong>
            <pre>{JSON.stringify(msg.data, null, 2)}</pre>
          </div>
        ))}
      </div>
    </div>
  );
};

export default KafkaInspector;
