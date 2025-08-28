import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FiSettings as Settings,
  FiFilter as Filter,
  FiZap as Zap,
  FiSearch as Search,
  FiBook as BookOpen,
  FiChevronDown as ChevronDown,
  FiRotateCcw as RotateCcw,
  FiX as X,
} from "react-icons/fi";
import type { ComplexityLevel, DocumentFilters, DocumentType } from "../types";

interface ChatSettingsProps {
  complexity: ComplexityLevel;
  useTools: boolean;
  useHybridSearch: boolean;
  includeCitations: boolean;
  maxSources: number;
  filters: DocumentFilters;
  onComplexityChange: (complexity: ComplexityLevel) => void;
  onUseToolsChange: (useTools: boolean) => void;
  onUseHybridSearchChange: (useHybridSearch: boolean) => void;
  onIncludeCitationsChange: (includeCitations: boolean) => void;
  onMaxSourcesChange: (maxSources: number) => void;
  onFiltersChange: (filters: DocumentFilters) => void;
  onReset: () => void;
}

const ChatSettings: React.FC<ChatSettingsProps> = ({
  complexity,
  useTools,
  useHybridSearch,
  includeCitations,
  maxSources,
  filters,
  onComplexityChange,
  onUseToolsChange,
  onUseHybridSearchChange,
  onIncludeCitationsChange,
  onMaxSourcesChange,
  onFiltersChange,
  onReset,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<"general" | "filters">("general");

  const documentTypes: { value: DocumentType; label: string }[] = [
    { value: "constitution", label: "Constitution" },
    { value: "statute", label: "Statutes" },
    { value: "case_law", label: "Case Law" },
    { value: "regulation", label: "Regulations" },
    { value: "legal_document", label: "Legal Documents" },
  ];

  const jurisdictions = [
    "Supreme Court of India",
    "High Courts",
    "District Courts",
    "Tribunals",
    "Central Government",
    "State Governments",
  ];

  const legalTopics = [
    "Criminal Law",
    "Civil Law",
    "Constitutional Law",
    "Corporate Law",
    "Labour Law",
    "Tax Law",
    "Property Law",
    "Family Law",
    "Environmental Law",
    "Intellectual Property",
  ];

  const handleDocumentTypeChange = (
    docType: DocumentType,
    checked: boolean
  ) => {
    const currentTypes = filters.document_types || [];
    const newTypes = checked
      ? [...currentTypes, docType]
      : currentTypes.filter((t) => t !== docType);

    onFiltersChange({
      ...filters,
      document_types: newTypes,
    });
  };

  const handleTopicChange = (topic: string, checked: boolean) => {
    const currentTopics = filters.legal_topics || [];
    const newTopics = checked
      ? [...currentTopics, topic]
      : currentTopics.filter((t) => t !== topic);

    onFiltersChange({
      ...filters,
      legal_topics: newTopics,
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/30 overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-200/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Settings className="h-5 w-5 text-primary-600" />
            <h3 className="text-lg font-semibold text-gray-800">
              Chat Settings
            </h3>
          </div>
          <div className="flex items-center space-x-2">
            <motion.button
              onClick={onReset}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors duration-200"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              title="Reset to defaults"
            >
              <RotateCcw className="h-4 w-4" />
            </motion.button>
            <motion.button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors duration-200"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <motion.div
                animate={{ rotate: isExpanded ? 180 : 0 }}
                transition={{ duration: 0.2 }}
              >
                <ChevronDown className="h-4 w-4" />
              </motion.div>
            </motion.button>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            {/* Tabs */}
            <div className="flex border-b border-gray-200/50">
              <motion.button
                onClick={() => setActiveTab("general")}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors duration-200 ${
                  activeTab === "general"
                    ? "text-primary-600 border-b-2 border-primary-500 bg-primary-50/50"
                    : "text-gray-600 hover:text-gray-800"
                }`}
                whileHover={{
                  backgroundColor:
                    activeTab === "general" ? undefined : "rgba(0,0,0,0.02)",
                }}
              >
                <div className="flex items-center justify-center space-x-2">
                  <Zap className="h-4 w-4" />
                  <span>General</span>
                </div>
              </motion.button>
              <motion.button
                onClick={() => setActiveTab("filters")}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors duration-200 ${
                  activeTab === "filters"
                    ? "text-primary-600 border-b-2 border-primary-500 bg-primary-50/50"
                    : "text-gray-600 hover:text-gray-800"
                }`}
                whileHover={{
                  backgroundColor:
                    activeTab === "filters" ? undefined : "rgba(0,0,0,0.02)",
                }}
              >
                <div className="flex items-center justify-center space-x-2">
                  <Filter className="h-4 w-4" />
                  <span>Filters</span>
                </div>
              </motion.button>
            </div>

            <div className="p-6">
              {activeTab === "general" && (
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="space-y-6"
                >
                  {/* Complexity Level */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      Response Complexity
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {(
                        [
                          "simple",
                          "intermediate",
                          "advanced",
                        ] as ComplexityLevel[]
                      ).map((level) => (
                        <motion.button
                          key={level}
                          onClick={() => onComplexityChange(level)}
                          className={`p-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                            complexity === level
                              ? "bg-primary-500 text-white shadow-md"
                              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                          }`}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                        >
                          {level.charAt(0).toUpperCase() + level.slice(1)}
                        </motion.button>
                      ))}
                    </div>
                  </div>

                  {/* Toggle Settings */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <Zap className="h-5 w-5 text-blue-500" />
                        <div>
                          <p className="font-medium text-gray-800">
                            Use AI Tools
                          </p>
                          <p className="text-sm text-gray-600">
                            Enable advanced legal research tools
                          </p>
                        </div>
                      </div>
                      <motion.button
                        onClick={() => onUseToolsChange(!useTools)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                          useTools ? "bg-primary-500" : "bg-gray-300"
                        }`}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        <motion.span
                          className="inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
                          animate={{ translateX: useTools ? 24 : 4 }}
                          transition={{
                            type: "spring",
                            stiffness: 500,
                            damping: 30,
                          }}
                        />
                      </motion.button>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <Search className="h-5 w-5 text-green-500" />
                        <div>
                          <p className="font-medium text-gray-800">
                            Hybrid Search
                          </p>
                          <p className="text-sm text-gray-600">
                            Combine semantic and keyword search
                          </p>
                        </div>
                      </div>
                      <motion.button
                        onClick={() =>
                          onUseHybridSearchChange(!useHybridSearch)
                        }
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                          useHybridSearch ? "bg-primary-500" : "bg-gray-300"
                        }`}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        <motion.span
                          className="inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
                          animate={{ translateX: useHybridSearch ? 24 : 4 }}
                          transition={{
                            type: "spring",
                            stiffness: 500,
                            damping: 30,
                          }}
                        />
                      </motion.button>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <BookOpen className="h-5 w-5 text-purple-500" />
                        <div>
                          <p className="font-medium text-gray-800">
                            Include Citations
                          </p>
                          <p className="text-sm text-gray-600">
                            Show detailed source references
                          </p>
                        </div>
                      </div>
                      <motion.button
                        onClick={() =>
                          onIncludeCitationsChange(!includeCitations)
                        }
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                          includeCitations ? "bg-primary-500" : "bg-gray-300"
                        }`}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        <motion.span
                          className="inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
                          animate={{ translateX: includeCitations ? 24 : 4 }}
                          transition={{
                            type: "spring",
                            stiffness: 500,
                            damping: 30,
                          }}
                        />
                      </motion.button>
                    </div>
                  </div>

                  {/* Max Sources */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Maximum Sources: {maxSources}
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={maxSources}
                      onChange={(e) =>
                        onMaxSourcesChange(parseInt(e.target.value))
                      }
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>1</span>
                      <span>5</span>
                      <span>10</span>
                    </div>
                  </div>
                </motion.div>
              )}

              {activeTab === "filters" && (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="space-y-6"
                >
                  {/* Document Types */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      Document Types
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {documentTypes.map((docType) => (
                        <motion.label
                          key={docType.value}
                          className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-50 cursor-pointer"
                          whileHover={{ backgroundColor: "rgba(0,0,0,0.02)" }}
                        >
                          <input
                            type="checkbox"
                            checked={
                              filters.document_types?.includes(docType.value) ||
                              false
                            }
                            onChange={(e) =>
                              handleDocumentTypeChange(
                                docType.value,
                                e.target.checked
                              )
                            }
                            className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <span className="text-sm text-gray-700">
                            {docType.label}
                          </span>
                        </motion.label>
                      ))}
                    </div>
                  </div>

                  {/* Legal Topics */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      Legal Topics
                    </label>
                    <div className="max-h-40 overflow-y-auto space-y-1">
                      {legalTopics.map((topic) => (
                        <motion.label
                          key={topic}
                          className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-50 cursor-pointer"
                          whileHover={{ backgroundColor: "rgba(0,0,0,0.02)" }}
                        >
                          <input
                            type="checkbox"
                            checked={
                              filters.legal_topics?.includes(topic) || false
                            }
                            onChange={(e) =>
                              handleTopicChange(topic, e.target.checked)
                            }
                            className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <span className="text-sm text-gray-700">{topic}</span>
                        </motion.label>
                      ))}
                    </div>
                  </div>

                  {/* Jurisdiction */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Jurisdiction
                    </label>
                    <select
                      value={filters.jurisdiction || ""}
                      onChange={(e) =>
                        onFiltersChange({
                          ...filters,
                          jurisdiction: e.target.value || undefined,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white/80"
                    >
                      <option value="">All Jurisdictions</option>
                      {jurisdictions.map((jurisdiction) => (
                        <option key={jurisdiction} value={jurisdiction}>
                          {jurisdiction}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Clear Filters */}
                  <motion.button
                    onClick={() => onFiltersChange({})}
                    className="w-full py-2 px-4 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors duration-200 flex items-center justify-center space-x-2"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <X className="h-4 w-4" />
                    <span>Clear All Filters</span>
                  </motion.button>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default ChatSettings;
