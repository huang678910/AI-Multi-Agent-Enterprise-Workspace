"use client";
import { useState } from "react";
import { FileText, File, Trash2, Eye } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Document } from "@/types";
import api from "@/lib/api";

interface DocumentCardProps {
  doc: Document;
  onDelete: (id: string) => void;
}

const fileIcons: Record<string, React.ReactNode> = {
  pdf: <FileText size={20} className="text-red-500" />,
  docx: <FileText size={20} className="text-blue-500" />,
  pptx: <FileText size={20} className="text-orange-500" />,
  txt: <File size={20} className="text-gray-500" />,
  md: <File size={20} className="text-green-500" />,
  markdown: <File size={20} className="text-green-500" />,
  audio: <File size={20} className="text-purple-500" />,
};

const statusColors: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  ready: "default",
  processing: "secondary",
  pending: "secondary",
  error: "destructive",
};

export default function DocumentCard({ doc, onDelete }: DocumentCardProps) {
  const [showPreview, setShowPreview] = useState(false);
  const [previewContent, setPreviewContent] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewInfo, setPreviewInfo] = useState<{ filename: string; source_type: string; chunk_count: number } | null>(null);

  async function handlePreview() {
    setShowPreview(true);
    setPreviewLoading(true);
    try {
      const res = await api.get(`/api/v1/workspaces/${doc.workspace_id}/documents/${doc.id}/preview`);
      setPreviewContent(res.data.content || "(No content)");
      setPreviewInfo({
        filename: res.data.filename,
        source_type: res.data.source_type,
        chunk_count: res.data.chunk_count,
      });
    } catch {
      setPreviewContent("Failed to load preview.");
    } finally {
      setPreviewLoading(false);
    }
  }

  const sourceLabel = (doc as Document & { source_type?: string }).source_type;
  const isExternal = sourceLabel && sourceLabel !== "upload";

  return (
    <>
      <div className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-100 hover:border-gray-200 transition-colors">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-gray-50 flex items-center justify-center">
            {fileIcons[doc.file_type] || <File size={20} className="text-gray-400" />}
          </div>
          <div>
            <p className="text-sm font-medium text-gray-800 truncate max-w-[400px]">{doc.filename}</p>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-gray-400">
                {doc.file_type.toUpperCase()} • {(doc.file_size / 1024).toFixed(1)} KB
              </span>
              {doc.status === "ready" && (
                <span className="text-xs text-gray-400">• {doc.chunk_count} chunks</span>
              )}
              {isExternal && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-50 text-purple-600">
                  {sourceLabel}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={statusColors[doc.status] || "outline"}>
            {doc.status}
          </Badge>
          <button
            onClick={handlePreview}
            className="p-1.5 hover:bg-blue-50 rounded-lg text-gray-400 hover:text-blue-500 transition-colors"
            title="Preview document"
          >
            <Eye size={16} />
          </button>
          <button
            onClick={() => onDelete(doc.id)}
            className="p-1.5 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-500 transition-colors"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {/* Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowPreview(false)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <div>
                <h3 className="text-sm font-semibold text-gray-800">
                  {previewInfo?.filename || doc.filename}
                </h3>
                {previewInfo && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    Source: {previewInfo.source_type} • {previewInfo.chunk_count} chunks
                  </p>
                )}
              </div>
              <button onClick={() => setShowPreview(false)}
                className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600 transition-colors">
                ✕
              </button>
            </div>
            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {previewLoading ? (
                <p className="text-sm text-gray-400 text-center py-12">Loading...</p>
              ) : (
                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
                  {previewContent}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
