import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import UploadZone from "../components/UploadZone";
import { api } from "../lib/api";

type Stage = "idle" | "uploading" | "processing" | "done" | "failed";

export default function Upload() {
  const navigate = useNavigate();
  const [stage, setStage] = useState<Stage>("idle");
  const [reportId, setReportId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setStage("uploading");
    setError(null);
    try {
      const { id } = await api.reports.upload(file);
      setReportId(id);
      setStage("processing");
    } catch (e: any) {
      setError(e.message ?? "Upload failed");
      setStage("failed");
    }
  }

  // Poll status while processing
  useEffect(() => {
    if (stage !== "processing" || !reportId) return;
    const interval = setInterval(async () => {
      try {
        const { status, error_message } = await api.reports.status(reportId);
        if (status === "done") {
          setStage("done");
          clearInterval(interval);
        } else if (status === "failed") {
          setError(error_message ?? "Processing failed");
          setStage("failed");
          clearInterval(interval);
        }
      } catch {
        // keep polling
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [stage, reportId]);

  return (
    <div className="max-w-xl">
      <h2 className="text-2xl font-bold mb-1">Upload Lab Report</h2>
      <p className="text-gray-500 dark:text-gray-400 mb-6 text-sm">
        Upload a PDF or image of your blood work. OCR will extract biomarkers automatically.
      </p>

      {stage === "idle" && <UploadZone onFile={handleFile} />}

      {stage === "uploading" && (
        <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
          <Loader2 size={18} className="animate-spin" />
          Uploading…
        </div>
      )}

      {stage === "processing" && (
        <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
          <Loader2 size={18} className="animate-spin" />
          Extracting biomarkers via OCR… this may take a moment.
        </div>
      )}

      {stage === "done" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
            <CheckCircle size={20} />
            <span className="text-sm font-medium">Report processed successfully.</span>
          </div>
          <div className="flex gap-3">
            <button
              className="text-sm px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700"
              onClick={() => navigate("/")}
            >
              View Dashboard
            </button>
            <button
              className="text-sm px-4 py-2 rounded-md border border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-900"
              onClick={() => { setStage("idle"); setReportId(null); }}
            >
              Upload Another
            </button>
          </div>
        </div>
      )}

      {stage === "failed" && (
        <div className="space-y-4">
          <div className="flex items-start gap-2 text-red-600 dark:text-red-400">
            <XCircle size={20} className="shrink-0 mt-0.5" />
            <span className="text-sm">{error}</span>
          </div>
          <button
            className="text-sm px-4 py-2 rounded-md border border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-900"
            onClick={() => { setStage("idle"); setError(null); }}
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
}
