import React, { useMemo } from "react";
import { motion } from "framer-motion";
import { FileText, BookOpen } from "lucide-react";
import type { Message } from "../types";

interface SourceDocumentProps {
  messages: Message[];
}

const SourceDocument: React.FC<SourceDocumentProps> = ({ messages }) => {
  const uniqueSources = useMemo(() => {
    const sources = new Set<string>();
    messages.forEach((message) => {
      if (message.sources) {
        message.sources.forEach((source) => sources.add(source));
      }
    });
    return Array.from(sources);
  }, [messages]);

  if (uniqueSources.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white/60 backdrop-blur-xl rounded-2xl shadow-elegant border border-white/30 p-6"
      >
        <h3 className="font-bold text-gray-800 mb-4 flex items-center text-lg">
          <BookOpen className="h-6 w-6 text-primary-500 mr-3" />
          Referenced Documents
        </h3>
        <div className="text-center py-8 bg-gray-50/40 rounded-xl border border-gray-200/50">
          <p className="text-gray-500 font-medium">
            No documents referenced yet. Start a conversation to see relevant
            sources.
          </p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="bg-white/60 backdrop-blur-xl rounded-2xl shadow-elegant border border-white/30 p-6"
    >
      <h3 className="font-bold text-gray-800 mb-4 flex items-center text-lg">
        <BookOpen className="h-6 w-6 text-primary-500 mr-3" />
        Referenced Documents
      </h3>
      <div className="space-y-3 max-h-64 overflow-y-auto scrollbar-elegant">
        {uniqueSources.map((source, index) => (
          <motion.div
            key={source}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-center space-x-3 p-4 rounded-xl bg-gray-50/60 hover:bg-gray-100/60 transition-all duration-300 border border-gray-200/50 hover:border-primary-300/50 group cursor-pointer"
            whileHover={{ x: 5, scale: 1.02 }}
          >
            <FileText className="h-5 w-5 text-primary-500 flex-shrink-0 group-hover:scale-110 transition-transform duration-200" />
            <span
              className="text-gray-700 truncate font-medium group-hover:text-primary-600 transition-colors duration-200"
              title={source}
            >
              {source}
            </span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};

export default SourceDocument;
