import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FiSliders as Sliders,
  FiRefreshCw as RefreshCw,
  FiCheck as Check,
  FiLoader as Loader,
  FiAlertCircle as AlertCircle,
} from "react-icons/fi";

type Status = {
  kind: "idle" | "loading" | "success" | "error";
  message?: string;
};

const API_PATH = "http://localhost:8000/api/rerank-weights";

const clamp = (v: number) => Math.max(0, Math.min(1, v));

const RerankWeightsControl: React.FC = () => {
  const [alpha, setAlpha] = useState<number>(0.75);
  const [beta, setBeta] = useState<number>(0.25);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  useEffect(() => {
    (async () => {
      setStatus({ kind: "loading" });
      try {
        const res = await fetch(API_PATH);
        if (!res.ok) throw new Error(`Failed to load: ${res.status}`);
        const json = await res.json();
        setAlpha(Number(json.alpha ?? 0.75));
        setBeta(Number(json.beta ?? 0.25));
        setStatus({ kind: "success", message: "Loaded weights" });
      } catch (err: any) {
        setStatus({
          kind: "error",
          message: err?.message ?? "Failed to load weights",
        });
      }
    })();
  }, []);

  const onSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setStatus({ kind: "loading" });
    try {
      // normalize client-side so server receives reasonable values
      const a = clamp(Number(alpha));
      const b = clamp(Number(beta));
      if (a === 0 && b === 0) {
        setStatus({
          kind: "error",
          message: "Alpha and beta cannot both be zero",
        });
        return;
      }
      const res = await fetch(API_PATH, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ alpha: a, beta: b }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(
          body?.detail || body?.message || `Server ${res.status}`
        );
      }
      const json = await res.json();
      setAlpha(Number(json.alpha));
      setBeta(Number(json.beta));
      setStatus({ kind: "success", message: "Weights updated successfully" });

      // Clear success message after 3 seconds
      setTimeout(() => {
        setStatus({ kind: "idle" });
      }, 3000);
    } catch (err: any) {
      setStatus({ kind: "error", message: err?.message ?? "Failed to update" });
    }
  };

  const resetWeights = () => {
    setAlpha(0.75);
    setBeta(0.25);
    setStatus({ kind: "idle" });
  };

  const normalizeWeights = () => {
    const s = alpha + beta;
    if (s === 0) {
      setStatus({
        kind: "error",
        message: "Alpha and beta cannot both be zero",
      });
      return;
    }
    setAlpha(Number((alpha / s).toFixed(2)));
    setBeta(Number((beta / s).toFixed(2)));
    setStatus({ kind: "idle" });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/30 overflow-hidden"
    >
      {/* Header */}
      <div className="p-6 border-b border-gray-200/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-r from-primary-500 to-primary-600 p-2 rounded-lg">
              <Sliders className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-800">
                Rerank Weights
              </h3>
              <p className="text-sm text-gray-600">
                Configure similarity vs evaluation score balance
              </p>
            </div>
          </div>
          <motion.button
            onClick={resetWeights}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors duration-200"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            title="Reset to defaults"
          >
            <RefreshCw className="h-4 w-4" />
          </motion.button>
        </div>
      </div>

      {/* Form Content */}
      <form onSubmit={onSubmit} className="p-6 space-y-6">
        {/* Alpha Weight Control */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">
              Alpha (Similarity Weight)
            </label>
            <span className="text-sm text-gray-500">
              {(alpha * 100).toFixed(0)}%
            </span>
          </div>

          <div className="space-y-2">
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={alpha}
              onChange={(e) => setAlpha(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
              style={{
                background: `linear-gradient(to right, rgb(59 130 246) 0%, rgb(59 130 246) ${
                  alpha * 100
                }%, rgb(229 231 235) ${alpha * 100}%, rgb(229 231 235) 100%)`,
              }}
            />
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={Number(alpha.toFixed(2))}
              onChange={(e) => setAlpha(clamp(Number(e.target.value)))}
              className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all duration-200"
            />
          </div>
        </div>

        {/* Beta Weight Control */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">
              Beta (Evaluation Score Weight)
            </label>
            <span className="text-sm text-gray-500">
              {(beta * 100).toFixed(0)}%
            </span>
          </div>

          <div className="space-y-2">
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={beta}
              onChange={(e) => setBeta(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
              style={{
                background: `linear-gradient(to right, rgb(168 85 247) 0%, rgb(168 85 247) ${
                  beta * 100
                }%, rgb(229 231 235) ${beta * 100}%, rgb(229 231 235) 100%)`,
              }}
            />
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={Number(beta.toFixed(2))}
              onChange={(e) => setBeta(clamp(Number(e.target.value)))}
              className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all duration-200"
            />
          </div>
        </div>

        {/* Weight Sum Display */}
        <div className="p-4 bg-gray-50/80 rounded-lg">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Total Weight:</span>
            <span
              className={`font-medium ${
                Math.abs(alpha + beta - 1) < 0.01
                  ? "text-green-600"
                  : "text-orange-600"
              }`}
            >
              {(alpha + beta).toFixed(2)}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-3">
          <motion.button
            type="submit"
            disabled={status.kind === "loading"}
            className="flex-1 px-4 py-3 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-lg font-medium hover:from-primary-600 hover:to-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center space-x-2"
            whileHover={{ scale: status.kind === "loading" ? 1 : 1.02 }}
            whileTap={{ scale: status.kind === "loading" ? 1 : 0.98 }}
          >
            {status.kind === "loading" ? (
              <>
                <Loader className="h-4 w-4 animate-spin" />
                <span>Applying...</span>
              </>
            ) : (
              <>
                <Check className="h-4 w-4" />
                <span>Apply Weights</span>
              </>
            )}
          </motion.button>

          <motion.button
            type="button"
            onClick={normalizeWeights}
            className="px-4 py-3 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-all duration-200"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Normalize
          </motion.button>
        </div>

        {/* Status Messages */}
        <AnimatePresence>
          {status.kind !== "idle" && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`p-3 rounded-lg flex items-center space-x-2 text-sm ${
                status.kind === "success"
                  ? "bg-green-50 text-green-700 border border-green-200"
                  : status.kind === "error"
                  ? "bg-red-50 text-red-700 border border-red-200"
                  : "bg-blue-50 text-blue-700 border border-blue-200"
              }`}
            >
              {status.kind === "success" && <Check className="h-4 w-4" />}
              {status.kind === "error" && <AlertCircle className="h-4 w-4" />}
              {status.kind === "loading" && (
                <Loader className="h-4 w-4 animate-spin" />
              )}
              <span>{status.message}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </form>
    </motion.div>
  );
};

export default RerankWeightsControl;
