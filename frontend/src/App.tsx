import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  FileText,
  Scale,
  MessageSquare,
  ChevronDown,
  Loader2,
} from "lucide-react";
import ChatMessage from "./components/ChatMessage";
import SourceDocument from "./components/SourceDocument";
import { useChatAPI } from "./hooks/useChatAPI";
import type { Message } from "./types";

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { sendMessage, isLoading, error } = useChatAPI();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");

    try {
      const response = await sendMessage(inputValue);
      console.log("Response received:", response);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.answer,
        sender: "assistant",
        timestamp: new Date(),
        sources: response.source_documents.map((doc) => doc.source), // Extract source names
        confidence: response.confidence,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Error in handleSubmit:", err);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content:
          "I apologize, but I encountered an error processing your request. Please try again.",
        sender: "assistant",
        timestamp: new Date(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const quickQuestions = [
    "What are the requirements for filing a case?",
    "Explain the process of bail applications",
    "What are the fundamental rights in the Constitution?",
    "How does the appeal process work?",
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-100 to-gray-200 flex flex-col overflow-hidden">
      {/* Header with Glass Effect */}
      <header className="bg-white/60 backdrop-blur-xl border-b border-white/20 sticky top-0 z-50 shadow-elegant">
        <div className="px-8 py-6">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <motion.div
              className="flex items-center space-x-5"
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            >
              <div className="relative">
                <div className="bg-gradient-to-r from-primary-500 via-primary-600 to-primary-700 p-4 rounded-2xl shadow-golden glow-premium">
                  <Scale className="h-8 w-8 text-white" />
                </div>
                <div className="absolute inset-0 bg-gradient-to-r from-primary-400 to-primary-600 rounded-2xl blur-lg opacity-30 -z-10"></div>
              </div>
              <div>
                <h1 className="text-4xl font-bold text-gradient mb-1">
                  AI Legal Assistant
                </h1>
                <p className="text-lg text-gray-600 font-medium">
                  Your intelligent legal companion
                </p>
              </div>
            </motion.div>

            <div className="relative">
              <motion.button
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                className="btn-secondary flex items-center space-x-3"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <MessageSquare className="h-5 w-5" />
                <span className="font-semibold">Quick Questions</span>
                <motion.div
                  animate={{ rotate: isMenuOpen ? 180 : 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <ChevronDown className="h-5 w-5" />
                </motion.div>
              </motion.button>

              <AnimatePresence>
                {isMenuOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -10, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className="absolute right-0 mt-3 w-96 bg-white/90 backdrop-blur-xl rounded-2xl shadow-premium border border-white/30 py-3 z-50 overflow-hidden"
                  >
                    <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-primary-500 to-transparent"></div>
                    {quickQuestions.map((question, index) => (
                      <motion.button
                        key={index}
                        onClick={() => {
                          setInputValue(question);
                          setIsMenuOpen(false);
                        }}
                        className="w-full text-left px-6 py-4 hover:bg-primary-50/50 transition-all duration-200 text-gray-700 border-b border-gray-100/50 last:border-b-0 group"
                        whileHover={{ x: 5 }}
                        transition={{ duration: 0.2 }}
                      >
                        <span className="group-hover:text-primary-600 transition-colors duration-200 font-medium">
                          {question}
                        </span>
                      </motion.button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </header>

      {/* Main Chat Container - Full Screen */}
      <div className="flex-1 flex flex-col overflow-hidden max-w-7xl mx-auto w-full px-8 py-6">
        <div className="flex-1 flex flex-col card-premium overflow-hidden">
          {/* Messages Container with Enhanced Styling */}
          <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6 scrollbar-elegant">
            <AnimatePresence>
              {messages.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6 }}
                  className="flex flex-col items-center justify-center h-full text-center py-20"
                >
                  <motion.div
                    className="relative mb-8"
                    animate={{
                      rotate: [0, 5, -5, 0],
                      scale: [1, 1.05, 1],
                    }}
                    transition={{
                      duration: 4,
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                  >
                    <div className="bg-gradient-to-r from-primary-500 via-primary-600 to-primary-700 p-8 rounded-3xl w-24 h-24 mx-auto shadow-golden glow-premium flex items-center justify-center">
                      <Scale className="h-12 w-12 text-white" />
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-r from-primary-400 to-primary-600 rounded-3xl blur-2xl opacity-20 animate-pulse"></div>
                  </motion.div>

                  <motion.h3
                    className="text-3xl font-bold text-gray-800 mb-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                  >
                    Welcome to AI Legal Assistant
                  </motion.h3>

                  <motion.p
                    className="text-xl text-gray-600 max-w-2xl mx-auto mb-12 leading-relaxed"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                  >
                    Ask me any legal question and I'll provide you with
                    comprehensive answers based on Indian legal documents.
                  </motion.p>

                  <motion.div
                    className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl w-full"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.7 }}
                  >
                    {quickQuestions.slice(0, 4).map((question, index) => (
                      <motion.button
                        key={index}
                        onClick={() => setInputValue(question)}
                        className="text-left p-6 bg-white/80 hover:bg-white/90 backdrop-blur-md rounded-2xl border border-white/30 transition-all duration-300 hover:shadow-xl hover:scale-105 text-gray-700 group relative overflow-hidden"
                        whileHover={{ y: -5 }}
                        transition={{ duration: 0.2 }}
                      >
                        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-primary-500 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                        <span className="font-medium group-hover:text-primary-600 transition-colors duration-300">
                          {question}
                        </span>
                      </motion.button>
                    ))}
                  </motion.div>
                </motion.div>
              ) : (
                messages.map((message, index) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 20, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{
                      duration: 0.4,
                      delay: index * 0.1,
                      ease: "easeOut",
                    }}
                  >
                    <ChatMessage message={message} />
                  </motion.div>
                ))
              )}
            </AnimatePresence>

            {isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-start space-x-4 max-w-3xl"
              >
                <div className="bg-gradient-to-r from-gray-600 via-gray-700 to-gray-800 p-3 rounded-full shadow-xl avatar-assistant">
                  <Scale className="h-5 w-5 text-white" />
                </div>
                <div className="bg-white/90 backdrop-blur-xl text-gray-800 rounded-3xl rounded-tl-lg py-6 px-8 shadow-xl border border-white/30 relative overflow-hidden">
                  <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-r from-transparent via-primary-500 to-transparent"></div>
                  <div className="loading-dots mb-3">
                    <div
                      className="loading-dot bg-primary-500"
                      style={{ animationDelay: "0ms" }}
                    ></div>
                    <div
                      className="loading-dot bg-primary-500"
                      style={{ animationDelay: "150ms" }}
                    ></div>
                    <div
                      className="loading-dot bg-primary-500"
                      style={{ animationDelay: "300ms" }}
                    ></div>
                  </div>
                  <p className="text-sm text-gray-500 font-medium">
                    Analyzing your question...
                  </p>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Enhanced Input Form */}
          <div className="border-t border-white/20 bg-white/40 backdrop-blur-xl p-8">
            <form
              onSubmit={handleSubmit}
              className="flex space-x-4 items-end max-w-6xl mx-auto"
            >
              <div className="flex-1 relative">
                <motion.input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Ask your legal question..."
                  className="input-field text-lg font-medium"
                  disabled={isLoading}
                  whileFocus={{ scale: 1.02 }}
                  transition={{ duration: 0.2 }}
                />
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-primary-500/10 to-transparent opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
              </div>
              <motion.button
                type="submit"
                disabled={!inputValue.trim() || isLoading}
                className="btn-primary flex items-center space-x-3 text-lg relative overflow-hidden"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                transition={{ duration: 0.2 }}
              >
                <motion.div
                  animate={isLoading ? { rotate: 360 } : {}}
                  transition={
                    isLoading
                      ? { duration: 1, repeat: Infinity, ease: "linear" }
                      : {}
                  }
                >
                  {isLoading ? (
                    <Loader2 className="h-6 w-6" />
                  ) : (
                    <Send className="h-6 w-6" />
                  )}
                </motion.div>
                <span className="hidden sm:inline font-semibold">Send</span>
              </motion.button>
            </form>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 p-4 bg-red-50/80 backdrop-blur-md border border-red-200/60 rounded-xl text-red-700 text-sm font-medium max-w-6xl mx-auto"
              >
                {error}
              </motion.div>
            )}
          </div>
        </div>

        {/* Floating Premium Sidebar */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="fixed top-32 right-8 w-96 max-h-[calc(100vh-200px)] overflow-y-auto bg-white/70 backdrop-blur-xl rounded-3xl shadow-premium border border-white/30 hidden xl:block"
        >
          <div className="p-8 relative">
            <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-r from-transparent via-primary-500 to-transparent rounded-t-3xl"></div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              <SourceDocument messages={messages} />
            </motion.div>

            <div className="mt-8 space-y-6">
              <motion.div
                className="border-t border-gray-200/60 pt-6"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 }}
              >
                <h3 className="font-bold text-gray-800 mb-4 flex items-center text-lg">
                  <FileText className="h-6 w-6 text-primary-500 mr-3" />
                  Legal Resources
                </h3>
                <div className="space-y-3">
                  {[
                    "Indian Constitution",
                    "Criminal Procedure Code",
                    "Civil Procedure Code",
                    "Indian Penal Code",
                  ].map((resource) => (
                    <motion.div
                      key={resource}
                      className="flex items-center p-3 bg-gray-50/60 rounded-xl hover:bg-gray-100/60 transition-all duration-200 group cursor-pointer"
                      whileHover={{ x: 5 }}
                      transition={{ duration: 0.2 }}
                    >
                      <div className="w-2 h-2 bg-primary-500 rounded-full mr-3 group-hover:scale-125 transition-transform duration-200"></div>
                      <span className="text-gray-700 font-medium group-hover:text-primary-600 transition-colors duration-200">
                        {resource}
                      </span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>

              <motion.div
                className="border-t border-gray-200/60 pt-6"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1 }}
              >
                <h3 className="font-bold text-gray-800 mb-4 text-lg">
                  Expert Tips
                </h3>
                <div className="space-y-3">
                  {[
                    "Be specific in your questions",
                    "Mention relevant context",
                    "Ask about procedures, rights, or definitions",
                  ].map((tip, index) => (
                    <motion.div
                      key={tip}
                      className="flex items-start p-3 bg-primary-50/60 rounded-xl group"
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 1.2 + index * 0.1 }}
                    >
                      <div className="w-1.5 h-1.5 bg-primary-400 rounded-full mt-2.5 mr-3 group-hover:scale-150 transition-transform duration-200"></div>
                      <span className="text-gray-600 font-medium leading-relaxed">
                        {tip}
                      </span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

export default App;
