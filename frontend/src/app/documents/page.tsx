"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useWorkspaceStore } from "@/lib/stores";
import { listWorkspaces, listDocuments, uploadDocument, deleteDocument } from "@/lib/api-client";
import type { Workspace, Document } from "@/types";
import UploadDropzone from "@/components/documents/UploadDropzone";
import DocumentCard from "@/components/documents/DocumentCard";

export default function DocumentsPage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const { activeWorkspaceId, setActiveWorkspace } = useWorkspaceStore();

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) { router.push("/login"); return; }
    listWorkspaces().then((d) => {
      setWorkspaces(d.workspaces);
      if (!activeWorkspaceId && d.workspaces.length > 0) {
        setActiveWorkspace(d.workspaces[0].id);
      }
    }).catch(() => {});
  }, [token]);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    listDocuments(activeWorkspaceId).then((d) => setDocuments(d.documents)).catch(() => {});
  }, [activeWorkspaceId]);

  async function handleUpload(file: File) {
    if (!activeWorkspaceId) return;
    setUploading(true);
    setUploadError(null);
    try {
      await uploadDocument(activeWorkspaceId, file);
      const d = await listDocuments(activeWorkspaceId);
      setDocuments(d.documents);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      setUploadError(msg);
      console.error("Upload failed:", err);
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(docId: string) {
    if (!activeWorkspaceId) return;
    if (!confirm("Delete this document? (Admin only)")) return;
    try {
      await deleteDocument(activeWorkspaceId, docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Delete failed";
      alert("Delete failed: " + msg + "\n\nOnly workspace admins can delete documents.");
    }
  }

  const currentWs = workspaces.find((w) => w.id === activeWorkspaceId);

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload and manage your knowledge documents in{" "}
          <span className="font-medium text-gray-700">{currentWs?.name || "..."}</span>
        </p>
      </div>

      {/* Workspace Selector */}
      <div className="mb-6">
        <select
          value={activeWorkspaceId || ""}
          onChange={(e) => setActiveWorkspace(e.target.value)}
          className="text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {workspaces.map((w) => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
        </select>
      </div>

      {/* Upload Area */}
      <div className="mb-8">
        <UploadDropzone onUpload={handleUpload} uploading={uploading} />
        {uploadError && (
          <p className="mt-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{uploadError}</p>
        )}
      </div>

      {/* Document List */}
      <div>
        <h2 className="text-sm font-semibold text-gray-700 mb-3">
          Uploaded Documents ({documents.length})
        </h2>
        {documents.length === 0 ? (
          <p className="text-sm text-gray-400 py-8 text-center">
            No documents yet. Drag & drop files above to get started.
          </p>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <DocumentCard key={doc.id} doc={doc} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
