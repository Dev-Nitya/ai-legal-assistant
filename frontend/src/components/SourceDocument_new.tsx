import React from "react";
import { motion } from "framer-motion";
import { FiFileText as FileText } from "react-icons/fi";
import type { SourceDocument as SourceDocumentType } from "../types";

interface SourceDocumentProps {
  source: SourceDocumentType;
}

const SourceDocument: React.FC<SourceDocumentProps> = ({ source }) => {
  const getDocumentTypeColor = (type: string) => {
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

  const formatDocumentType = (type: string) => {
    return type.replace("_", " ").replace(/\b\w/g, (l) => l.toUpperCase());
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:border-blue-300 transition-colors"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          <FileText className="h-4 w-4 text-blue-600" />
          <span className="font-medium text-gray-900 text-sm truncate">
            {source.source}
          </span>
        </div>
        <span
          className={`px-2 py-1 rounded text-xs font-medium ${getDocumentTypeColor(
            source.document_type
          )}`}
        >
          {formatDocumentType(source.document_type)}
        </span>
      </div>

      {/* Content */}
      <div className="space-y-2">
        <p className="text-sm text-gray-700 line-clamp-3">
          {source.relevance_snippet}
        </p>

        {/* Metadata */}
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Page {source.page}</span>
          {source.confidence_score && (
            <span className="font-medium">
              {Math.round(source.confidence_score * 100)}% relevant
            </span>
          )}
        </div>

        {/* Legal Topics */}
        {source.legal_topics && source.legal_topics.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {source.legal_topics.slice(0, 3).map((topic, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-blue-50 text-blue-600 rounded text-xs"
              >
                {topic}
              </span>
            ))}
            {source.legal_topics.length > 3 && (
              <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                +{source.legal_topics.length - 3} more
              </span>
            )}
          </div>
        )}

        {/* Sections */}
        {source.sections && source.sections.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {source.sections.slice(0, 2).map((section, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-green-50 text-green-600 rounded text-xs font-mono"
              >
                {section}
              </span>
            ))}
            {source.sections.length > 2 && (
              <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                +{source.sections.length - 2} sections
              </span>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default SourceDocument;
