import React from "react";
import {
  FiUser as User,
  FiCpu as Bot,
  FiClock as Clock,
  FiCheckCircle as CheckCircle,
  FiAlertCircle as AlertCircle,
} from "react-icons/fi";
import type { Message } from "../types";

interface ChatMessageProps {
  message: Message;
}

function safeTimestamp(ts: unknown): Date {
  if (!ts) return new Date();
  if (ts instanceof Date) return ts;
  if (typeof ts === "number") return new Date(ts);
  if (typeof ts === "string") {
    const parsed = Date.parse(ts);
    return isNaN(parsed) ? new Date() : new Date(parsed);
  }
  return new Date();
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.sender === "user";
  const timestamp = safeTimestamp(message.timestamp);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-6`}>
      <div
        className={`flex max-w-[80%] ${
          isUser ? "flex-row-reverse" : "flex-row"
        }`}
      >
        {/* Avatar */}
        <div className={`flex-shrink-0 ${isUser ? "ml-3" : "mr-3"}`}>
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center ${
              isUser
                ? "bg-gradient-to-r from-amber-400 to-amber-600"
                : "bg-gradient-to-r from-blue-500 to-blue-600"
            }`}
          >
            {isUser ? (
              <User className="w-4 h-4 text-white" />
            ) : (
              <Bot className="w-4 h-4 text-white" />
            )}
          </div>
        </div>

        {/* Message Content */}
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? "bg-gradient-to-r from-amber-500 to-amber-600 text-white"
              : "bg-white border border-gray-200 text-gray-800 shadow-sm"
          }`}
        >
          {/* Message Text */}
          <div className={`${isUser ? "text-white" : "text-gray-800"}`}>
            {isUser ? (
              // User messages as plain text
              <p className="whitespace-pre-wrap break-words">
                {message.content}
              </p>
            ) : (
              // Assistant messages as HTML
              <div
                className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-800 prose-strong:text-gray-900 prose-em:text-gray-700 prose-ul:text-gray-800 prose-ol:text-gray-800 prose-blockquote:text-gray-700 prose-blockquote:border-amber-500"
                dangerouslySetInnerHTML={{ __html: message.content || "" }}
              />
            )}

            {/* Streaming indicator */}
            {message.isStreaming && !isUser && (
              <div className="inline-flex items-center ml-2 mt-1">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  <div
                    className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"
                    style={{ animationDelay: "0.2s" }}
                  ></div>
                  <div
                    className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"
                    style={{ animationDelay: "0.4s" }}
                  ></div>
                </div>
                <span className="ml-2 text-xs text-blue-600">Streaming...</span>
              </div>
            )}
          </div>

          {/* Message Metadata */}
          {!isUser && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              {/* Sources */}
              {message.sources && message.sources.length > 0 && (
                <div className="mb-2">
                  <p className="text-xs font-medium text-gray-600 mb-1">
                    Sources:
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {message.sources.map((source, index) => (
                      <span
                        key={index}
                        className="inline-block px-2 py-1 bg-amber-100 text-amber-800 text-xs rounded-full"
                      >
                        {typeof source === "string" ? source : source.source}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Timestamp */}
              <div className="flex items-center text-xs text-gray-400">
                <Clock className="w-3 h-3 mr-1" />
                <span>
                  {timestamp.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            </div>
          )}

          {/* Error State */}
          {message.isError && (
            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              <AlertCircle className="w-4 h-4 inline mr-1" />
              Error processing your request
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default React.memo(ChatMessage);
