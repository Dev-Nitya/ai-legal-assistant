import React, { useState, useRef, useEffect } from "react";
import { useStreamingChat } from "../hooks/useStreamingChat";

interface StreamingChatProps {
  className?: string;
  userId?: string;
}

export const StreamingChat: React.FC<StreamingChatProps> = ({
  className = "",
  userId,
}) => {
  const [question, setQuestion] = useState("");
  const [complexityLevel, setComplexityLevel] = useState("intermediate");
  const [messages, setMessages] = useState<
    Array<{
      type: "user" | "assistant";
      content: string;
      timestamp: number;
      metadata?: any;
    }>
  >([]);

  const {
    isStreaming,
    currentResponse,
    status,
    error,
    finalData,
    sendStreamingMessage,
    stopStreaming,
  } = useStreamingChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentResponse, messages]);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isStreaming) return;

    // Add user message to chat
    const userMessage = {
      type: "user" as const,
      content: question,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Start streaming
    await sendStreamingMessage(question, complexityLevel, userId);

    // Clear input
    setQuestion("");
  };

  // When streaming completes, add the final message
  useEffect(() => {
    if (!isStreaming && currentResponse && status === "Complete") {
      const assistantMessage = {
        type: "assistant" as const,
        content: currentResponse,
        timestamp: Date.now(),
        metadata: finalData,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    }
  }, [isStreaming, currentResponse, status, finalData]);

  const getStatusColor = () => {
    if (error) return "text-red-500";
    if (isStreaming) return "text-blue-500";
    if (status === "Complete") return "text-green-500";
    return "text-gray-500";
  };

  const getStatusIcon = () => {
    if (error) return "❌";
    if (isStreaming) return "⚡";
    if (status === "Complete") return "✅";
    return "💭";
  };

  return (
    <div
      className={`flex flex-col h-full bg-white rounded-lg shadow-lg ${className}`}
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-4 rounded-t-lg">
        <h2 className="text-xl font-semibold">
          AI Legal Assistant - Streaming Chat
        </h2>
        <div className={`text-sm mt-2 ${getStatusColor()}`}>
          {getStatusIcon()} {status || "Ready"}
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.type === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-3xl px-4 py-3 rounded-lg ${
                message.type === "user"
                  ? "bg-blue-500 text-white ml-12"
                  : "bg-gray-100 text-gray-900 mr-12"
              }`}
            >
              {message.type === "user" ? (
                <div className="whitespace-pre-wrap">{message.content}</div>
              ) : (
                <div
                  className="prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: message.content }}
                />
              )}
              {message.metadata && (
                <div className="text-xs mt-2 opacity-70">
                  Response time:{" "}
                  {message.metadata.response_time_ms
                    ? (message.metadata.response_time_ms / 1000).toFixed(2)
                    : message.metadata.response_time_seconds?.toFixed(2)}
                  s{message.metadata.from_cache && " (cached)"}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Current streaming response */}
        {isStreaming && currentResponse && (
          <div className="flex justify-start">
            <div className="max-w-3xl px-4 py-3 rounded-lg bg-gray-100 text-gray-900 mr-12">
              <div
                className="prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: currentResponse }}
              />
              <div className="inline-block w-2 h-5 bg-blue-500 animate-pulse ml-1"></div>
            </div>
          </div>
        )}

        {/* Error display */}
        {error && (
          <div className="flex justify-center">
            <div className="px-4 py-3 rounded-lg bg-red-100 text-red-700 border border-red-200">
              <div className="flex items-center space-x-2">
                <span>❌</span>
                <span>{error}</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="border-t bg-gray-50 p-4 rounded-b-lg">
        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Complexity selector */}
          <div className="flex items-center space-x-3 text-sm">
            <label className="text-gray-700 font-medium">Complexity:</label>
            <select
              value={complexityLevel}
              onChange={(e) => setComplexityLevel(e.target.value)}
              disabled={isStreaming}
              className="px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              <option value="simple">Simple</option>
              <option value="intermediate">Intermediate</option>
              <option value="complex">Complex</option>
            </select>
          </div>

          {/* Input and send button */}
          <div className="flex space-x-3">
            <textarea
              ref={textareaRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a legal question..."
              disabled={isStreaming}
              rows={2}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />

            {isStreaming ? (
              <button
                type="button"
                onClick={stopStreaming}
                className="px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors"
              >
                Stop
              </button>
            ) : (
              <button
                type="submit"
                disabled={!question.trim()}
                className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Send
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};
