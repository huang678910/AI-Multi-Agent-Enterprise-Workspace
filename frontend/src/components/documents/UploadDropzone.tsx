"use client";
import { useState, useCallback } from "react";
import { Upload } from "lucide-react";

interface UploadDropzoneProps {
  onUpload: (file: File) => Promise<void>;
  uploading: boolean;
}

const ACCEPTED_TYPES = ".pdf,.docx,.pptx,.ppt,.txt,.md,.markdown,.csv,.xlsx,.xls";

export default function UploadDropzone({ onUpload, uploading }: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const files = Array.from(e.dataTransfer.files);
      for (const file of files) {
        await onUpload(file);
      }
    },
    [onUpload]
  );

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    for (const file of files) {
      await onUpload(file);
    }
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer ${
        isDragging
          ? "border-blue-400 bg-blue-50"
          : "border-gray-300 hover:border-gray-400 bg-gray-50/50"
      }`}
    >
      <input
        type="file"
        onChange={handleFileSelect}
        accept={ACCEPTED_TYPES}
        multiple
        className="absolute inset-0 opacity-0 cursor-pointer"
      />
      {uploading ? (
        <div className="space-y-3">
          <div className="w-10 h-10 mx-auto border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Uploading & processing...</p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-blue-50 flex items-center justify-center">
            <Upload size={24} className="text-blue-500" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700">
              Drop documents here or click to browse
            </p>
            <p className="text-xs text-gray-400 mt-1">
              PDF, DOCX, PPTX, XLSX, CSV, TXT, Markdown (max 50MB)
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
