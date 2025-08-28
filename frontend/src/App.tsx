import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FiSend as Send,
  FiFileText as FileText,
  FiAward as Scale,
  FiMessageSquare as MessageSquare,
  FiChevronDown as ChevronDown,
  FiLoader as Loader2,
  FiSettings as Settings,
  FiBarChart as BarChart3,
  FiUser as User,
  FiLogIn as LogIn,
  FiX as X,
} from "react-icons/fi";
import ChatMessage from "./components/ChatMessage";
import SourceDocument from "./components/SourceDocument";
import LoginForm from "./components/LoginForm";
import UserDashboard from "./components/UserDashboard";
import AdvancedChatSettings from "./components/AdvancedChatSettings";
import EvaluationInterface from "./components/EvaluationInterface";
import { useChatAPI } from "./hooks/useChatAPI";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import type {
  Message,
  ComplexityLevel,
  DocumentFilters,
  SourceDocument as SourceDocumentType,
} from "./types";

// Separate MainApp component to use auth context
const MainApp: React.FC = () => {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [activeView, setActiveView] = useState<
    "chat" | "evaluation" | "settings"
  >("chat");
  const [showLogin, setShowLogin] = useState(false);
  const [showUserDashboard, setShowUserDashboard] = useState(false);

  // Chat settings
  const [chatSettings, setChatSettings] = useState({
    complexity: "simple" as ComplexityLevel,
    useTools: true,
    useHybridSearch: true,
    includeCitations: true,
    maxSources: 5,
    filters: {} as DocumentFilters,
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { sendMessage, isLoading, error } = useChatAPI({
    token: user?.user_id ? "placeholder-token" : undefined,
    userId: user?.user_id,
  });

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
      const response = await sendMessage(inputValue, true); // Use enhanced chat
      console.log("Response received:", response);

      // Convert source documents to proper format
      const sources: SourceDocumentType[] = (
        response.source_documents || []
      ).map((doc, index) => {
        if (typeof doc === "string") {
          return {
            source: doc,
            page: index + 1,
            document_type: "legal_document" as const,
            relevance_snippet: `Content from ${doc}`,
            sections: [],
            legal_topics: [],
            confidence_score: 0.8,
          };
        }
        return doc;
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.answer,
        sender: "assistant",
        timestamp: new Date(),
        sources,
        confidence: response.confidence,
        tools_used: response.tools_used,
        citations: response.citations,
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

  const handleQuickQuestion = (question: string) => {
    setInputValue(question);
    setIsMenuOpen(false);
  };

  const resetChatSettings = () => {
    setChatSettings({
      complexity: "simple",
      useTools: true,
      useHybridSearch: true,
      includeCitations: true,
      maxSources: 5,
      filters: {},
    });
  };

  const quickQuestions = [
    "What are the requirements for filing a case?",
    "Explain the process of bail applications",
    "What are the fundamental rights in the Constitution?",
    "How does the appeal process work?",
  ];

  // Get latest assistant message with sources
  const latestAssistantMessage = messages
    .filter(
      (m) => m.sender === "assistant" && m.sources && m.sources.length > 0
    )
    .slice(-1)[0];

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-100 to-gray-200 flex items-center justify-center">
        <div className="flex items-center space-x-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
          <span className="text-lg font-medium text-gray-700">Loading...</span>
        </div>
      </div>
    );
  }

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

            <div className="flex items-center space-x-4">
              {/* Navigation Buttons */}
              <div className="flex items-center space-x-2 bg-white/70 backdrop-blur-md rounded-xl p-1">
                <motion.button
                  onClick={() => setActiveView("chat")}
                  className={`p-2 rounded-lg transition-all duration-200 ${
                    activeView === "chat"
                      ? "bg-primary-500 text-white shadow-md"
                      : "text-gray-600 hover:text-gray-800 hover:bg-white/50"
                  }`}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <MessageSquare className="h-5 w-5" />
                </motion.button>
                <motion.button
                  onClick={() => setActiveView("evaluation")}
                  className={`p-2 rounded-lg transition-all duration-200 ${
                    activeView === "evaluation"
                      ? "bg-primary-500 text-white shadow-md"
                      : "text-gray-600 hover:text-gray-800 hover:bg-white/50"
                  }`}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <BarChart3 className="h-5 w-5" />
                </motion.button>
                <motion.button
                  onClick={() => setActiveView("settings")}
                  className={`p-2 rounded-lg transition-all duration-200 ${
                    activeView === "settings"
                      ? "bg-primary-500 text-white shadow-md"
                      : "text-gray-600 hover:text-gray-800 hover:bg-white/50"
                  }`}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Settings className="h-5 w-5" />
                </motion.button>
              </div>

              {/* User Actions */}
              {isAuthenticated ? (
                <motion.button
                  onClick={() => setShowUserDashboard(!showUserDashboard)}
                  className="btn-secondary flex items-center space-x-3"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <User className="h-5 w-5" />
                  <span className="font-semibold">
                    {user?.full_name || "User"}
                  </span>
                </motion.button>
              ) : (
                <motion.button
                  onClick={() => setShowLogin(true)}
                  className="btn-primary flex items-center space-x-3"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <LogIn className="h-5 w-5" />
                  <span className="font-semibold">Sign In</span>
                </motion.button>
              )}

              {/* Quick Questions Menu */}
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
                    <ChevronDown className="h-4 w-4" />
                  </motion.div>
                </motion.button>

                <AnimatePresence>
                  {isMenuOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -10, scale: 0.95 }}
                      transition={{ duration: 0.2 }}
                      className="absolute right-0 mt-2 w-80 bg-white/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/30 z-50 overflow-hidden"
                    >
                      <div className="p-2">
                        {quickQuestions.map((question, index) => (
                          <motion.button
                            key={index}
                            onClick={() => handleQuickQuestion(question)}
                            className="w-full text-left px-6 py-4 hover:bg-primary-50/50 transition-all duration-200 text-gray-700 border-b border-gray-100/50 last:border-b-0 group"
                            whileHover={{ x: 5 }}
                            transition={{ duration: 0.2 }}
                          >
                            <span className="group-hover:text-primary-600 transition-colors duration-200 font-medium">
                              {question}
                            </span>
                          </motion.button>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden max-w-7xl mx-auto w-full px-8 py-6 space-x-6">
        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {activeView === "chat" && (
            <div className="flex-1 flex flex-col card-premium overflow-hidden">
              {/* Messages Container */}
              <div className="flex-1 overflow-y-auto scrollbar-elegant p-8 space-y-6">
                <AnimatePresence>
                  {messages.length === 0 ? (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      className="flex flex-col items-center justify-center h-full text-center py-20"
                    >
                      <motion.div
                        className="relative mb-8"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.2, type: "spring" }}
                      >
                        <div className="w-20 h-20 bg-gradient-to-r from-primary-500 via-primary-600 to-primary-700 rounded-full flex items-center justify-center shadow-2xl">
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
                        {quickQuestions.map((question, index) => (
                          <motion.button
                            key={index}
                            onClick={() => handleQuickQuestion(question)}
                            className="group p-6 bg-white/70 backdrop-blur-md border border-white/40 rounded-2xl hover:bg-white/90 hover:shadow-xl hover:border-primary-200 transition-all duration-300 text-left relative overflow-hidden"
                            whileHover={{ y: -2, scale: 1.02 }}
                            transition={{ duration: 0.2 }}
                          >
                            <span className="font-medium group-hover:text-primary-600 transition-colors duration-300">
                              {question}
                            </span>
                            <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-primary-500/10 to-transparent opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
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
          )}

          {activeView === "evaluation" && (
            <EvaluationInterface
              token={user?.user_id ? "placeholder-token" : undefined}
            />
          )}

          {activeView === "settings" && (
            <AdvancedChatSettings
              complexity={chatSettings.complexity}
              useTools={chatSettings.useTools}
              useHybridSearch={chatSettings.useHybridSearch}
              includeCitations={chatSettings.includeCitations}
              maxSources={chatSettings.maxSources}
              filters={chatSettings.filters}
              onComplexityChange={(complexity) =>
                setChatSettings((prev) => ({ ...prev, complexity }))
              }
              onUseToolsChange={(useTools) =>
                setChatSettings((prev) => ({ ...prev, useTools }))
              }
              onUseHybridSearchChange={(useHybridSearch) =>
                setChatSettings((prev) => ({ ...prev, useHybridSearch }))
              }
              onIncludeCitationsChange={(includeCitations) =>
                setChatSettings((prev) => ({ ...prev, includeCitations }))
              }
              onMaxSourcesChange={(maxSources) =>
                setChatSettings((prev) => ({ ...prev, maxSources }))
              }
              onFiltersChange={(filters) =>
                setChatSettings((prev) => ({ ...prev, filters }))
              }
              onReset={resetChatSettings}
            />
          )}
        </div>

        {/* Sidebar */}
        <div className="w-80 space-y-6">
          {/* User Dashboard */}
          {isAuthenticated && showUserDashboard && <UserDashboard />}

          {/* Source Documents */}
          {latestAssistantMessage && activeView === "chat" && (
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4, duration: 0.6 }}
              className="bg-white/80 backdrop-blur-xl rounded-2xl shadow-xl border border-white/30 p-6"
            >
              <div className="flex items-center space-x-3 mb-6">
                <FileText className="h-6 w-6 text-primary-600" />
                <h3 className="text-xl font-bold text-gray-800">
                  Referenced Sources
                </h3>
              </div>
              <SourceDocument sources={latestAssistantMessage.sources || []} />
            </motion.div>
          )}
        </div>
      </div>

      {/* Login Modal */}
      <AnimatePresence>
        {showLogin && !isAuthenticated && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
            onClick={() => setShowLogin(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="relative">
                <motion.button
                  onClick={() => setShowLogin(false)}
                  className="absolute -top-4 -right-4 w-8 h-8 bg-white rounded-full flex items-center justify-center text-gray-600 hover:text-gray-800 shadow-lg z-10"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                >
                  <X className="h-4 w-4" />
                </motion.button>
                <LoginForm onSuccess={() => setShowLogin(false)} />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Main App component with AuthProvider
function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;
