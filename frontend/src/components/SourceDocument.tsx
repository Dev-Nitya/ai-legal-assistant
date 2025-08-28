import React from "react";
import { motion } from "framer-motion";
import {
  FiFileText as FileText,
  FiBook as BookOpen,
  FiExternalLink as ExternalLink,
} from "react-icons/fi";
import type { SourceDocument as SourceDocumentType } from "../types";

interface SourceDocumentProps {
  sources: SourceDocumentType[];
}

const SourceDocument: React.FC<SourceDocumentProps> = ({ sources }) => {
  if (!sources || sources.length === 0) {
    return (
      <div className="text-gray-500 text-sm">
        No source documents available for this response.
      </div>
    );
  }

  const getDocumentTypeColor = (type?: string) => {
    switch (type) {
      case "case_law":
        return "bg-blue-100 text-blue-700";
      case "statute":
        return "bg-green-100 text-green-700";
      case "regulation":
        return "bg-purple-100 text-purple-700";
      case "constitution":
        return "bg-red-100 text-red-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  const formatDocumentType = (type?: string) => {
    if (!type) return "Document";
    return type.replace("_", " ").replace(/\b\w/g, (l) => l.toUpperCase());
  };

  return (
    <div className="space-y-4">
      {sources.map((source, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
          className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:border-blue-300 transition-colors"
        >
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center space-x-2">
              <FileText className="h-4 w-4 text-blue-600" />
              <h4 className="text-sm font-semibold text-gray-800 truncate">
                {source.source || "Legal Document"}
              </h4>
            </div>
            {source.document_type && (
              <span
                className={`px-2 py-1 rounded text-xs font-medium ${getDocumentTypeColor(
                  source.document_type
                )}`}
              >
                {formatDocumentType(source.document_type)}
              </span>
            )}
          </div>

          {source.relevance_snippet && (
            <div className="mb-3">
              <p className="text-sm text-gray-600 line-clamp-3">
                {source.relevance_snippet}
              </p>
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>Page {source.page || 1}</span>
            {source.confidence_score && (
              <span className="bg-blue-50 text-blue-600 px-2 py-1 rounded">
                {Math.round(source.confidence_score * 100)}% relevant
              </span>
            )}
          </div>

          {/* Legal Topics */}
          {source.legal_topics && source.legal_topics.length > 0 && (
            <div className="mt-3">
              {source.legal_topics
                .slice(0, 3)
                .map((topic: string, topicIndex: number) => (
                  <span
                    key={topicIndex}
                    className="inline-block bg-blue-100 text-blue-700 text-xs px-2 py-1 rounded mr-2 mb-1"
                  >
                    {topic}
                  </span>
                ))}
              {source.legal_topics.length > 3 && (
                <span className="text-xs text-gray-500">
                  +{source.legal_topics.length - 3} more
                </span>
              )}
            </div>
          )}

          {/* Sections */}
          {source.sections && source.sections.length > 0 && (
            <div className="mt-2">
              {source.sections
                .slice(0, 2)
                .map((section: string, sectionIndex: number) => (
                  <div
                    key={sectionIndex}
                    className="text-xs text-gray-600 mb-1"
                  >
                    <BookOpen className="h-3 w-3 inline mr-1" />
                    {section}
                  </div>
                ))}
            </div>
          )}

          {/* View Document Link */}
          <div className="mt-3 pt-3 border-t border-gray-200">
            <button className="flex items-center space-x-1 text-blue-600 hover:text-blue-700 text-sm font-medium">
              <ExternalLink className="h-3 w-3" />
              <span>View Document</span>
            </button>
          </div>
        </motion.div>
      ))}
    </div>
  );
};

export default SourceDocument;
