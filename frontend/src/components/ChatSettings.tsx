import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FiX as X,
  FiSettings as Settings,
  FiFilter as Filter,
  FiSliders as Sliders,
} from "react-icons/fi";
import type {
  ChatSettings as ChatSettingsType,
  ComplexityLevel,
  DocumentType,
} from "../types";

interface ChatSettingsProps {
  isOpen: boolean;
  onClose: () => void;
  settings: ChatSettingsType;
  onSettingsChange: (settings: ChatSettingsType) => void;
}

const ChatSettings: React.FC<ChatSettingsProps> = ({
  isOpen,
  onClose,
  settings,
  onSettingsChange,
}) => {
  const updateSettings = (updates: Partial<ChatSettingsType>) => {
    onSettingsChange({ ...settings, ...updates });
  };

  const updateFilters = (
    filterUpdates: Partial<ChatSettingsType["filters"]>
  ) => {
    updateSettings({
      filters: { ...settings.filters, ...filterUpdates },
    });
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black bg-opacity-50"
          onClick={onClose}
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="sticky top-0 bg-white border-b border-gray-200 p-6 rounded-t-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Settings className="h-6 w-6 text-blue-600" />
                <h2 className="text-xl font-semibold text-gray-900">
                  Chat Settings
                </h2>
              </div>
              <button
                onClick={onClose}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 space-y-8">
            {/* General Settings */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center space-x-2">
                <Sliders className="h-5 w-5" />
                <span>General Settings</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Complexity Level
                  </label>
                  <select
                    value={settings.complexity_level}
                    onChange={(e) =>
                      updateSettings({
                        complexity_level: e.target.value as ComplexityLevel,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="simple">Simple</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                  <p className="text-sm text-gray-500 mt-1">
                    Controls the depth and complexity of responses
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Max Sources
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={settings.max_sources}
                    onChange={(e) =>
                      updateSettings({
                        max_sources: parseInt(e.target.value),
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Maximum number of source documents to retrieve
                  </p>
                </div>
              </div>

              <div className="mt-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Use AI Tools
                    </label>
                    <p className="text-sm text-gray-500">
                      Enable advanced AI tools for research and analysis
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.use_tools}
                      onChange={(e) =>
                        updateSettings({ use_tools: e.target.checked })
                      }
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Hybrid Search
                    </label>
                    <p className="text-sm text-gray-500">
                      Combine keyword and semantic search for better results
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.use_hybrid_search}
                      onChange={(e) =>
                        updateSettings({ use_hybrid_search: e.target.checked })
                      }
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Include Citations
                    </label>
                    <p className="text-sm text-gray-500">
                      Add legal citations and references to responses
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.include_citations}
                      onChange={(e) =>
                        updateSettings({ include_citations: e.target.checked })
                      }
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
              </div>
            </div>

            {/* Document Filters */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center space-x-2">
                <Filter className="h-5 w-5" />
                <span>Document Filters</span>
              </h3>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Document Types
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { value: "case_law", label: "Case Law" },
                      { value: "statute", label: "Statutes" },
                      { value: "regulation", label: "Regulations" },
                      { value: "constitution", label: "Constitution" },
                      { value: "legal_document", label: "Legal Documents" },
                    ].map(({ value, label }) => (
                      <label
                        key={value}
                        className="flex items-center space-x-2"
                      >
                        <input
                          type="checkbox"
                          checked={
                            settings.filters.document_types?.includes(
                              value as DocumentType
                            ) || false
                          }
                          onChange={(e) => {
                            const currentTypes =
                              settings.filters.document_types || [];
                            if (e.target.checked) {
                              updateFilters({
                                document_types: [
                                  ...currentTypes,
                                  value as DocumentType,
                                ],
                              });
                            } else {
                              updateFilters({
                                document_types: currentTypes.filter(
                                  (t) => t !== value
                                ),
                              });
                            }
                          }}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-700">{label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Jurisdiction
                  </label>
                  <input
                    type="text"
                    value={settings.filters.jurisdiction || ""}
                    onChange={(e) =>
                      updateFilters({ jurisdiction: e.target.value })
                    }
                    placeholder="e.g., Federal, State, International"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Legal Topics
                    </label>
                    <input
                      type="text"
                      value={settings.filters.legal_topics?.join(", ") || ""}
                      onChange={(e) =>
                        updateFilters({
                          legal_topics: e.target.value
                            .split(",")
                            .map((t) => t.trim())
                            .filter((t) => t),
                        })
                      }
                      placeholder="e.g., Contract Law, Criminal Law"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <p className="text-sm text-gray-500 mt-1">
                      Separate topics with commas
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Acts/Statutes
                    </label>
                    <input
                      type="text"
                      value={settings.filters.acts?.join(", ") || ""}
                      onChange={(e) =>
                        updateFilters({
                          acts: e.target.value
                            .split(",")
                            .map((a) => a.trim())
                            .filter((a) => a),
                        })
                      }
                      placeholder="e.g., Indian Penal Code, Constitution"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <p className="text-sm text-gray-500 mt-1">
                      Separate acts with commas
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-gray-50 px-6 py-4 rounded-b-lg border-t border-gray-200">
            <div className="flex justify-end space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Close
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default ChatSettings;
