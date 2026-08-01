import { FileText, Plus, Upload, X } from "lucide-react";
import { useRef, useState } from "react";

import { uploadDocument } from "../services/api";

export default function DocumentUpload({
  document,
  onUploaded,
  onClear,
  disabled = false,
}) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleFile(file) {
    if (!file) {
      return;
    }

    const isPdf =
      file.type === "application/pdf" ||
      file.name.toLowerCase().endsWith(".pdf");

    if (!isPdf) {
      setError("Please select a PDF file.");
      return;
    }

    setError("");
    setProgress(0);
    setUploading(true);
    setMenuOpen(false);

    try {
      const result = await uploadDocument(file, (event) => {
        if (event.total) {
          const uploadedPercentage = Math.round(
            (event.loaded * 100) / event.total,
          );

          setProgress(uploadedPercentage);
        }
      });

      onUploaded(result);
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "PDF upload failed. Check that FastAPI and Ollama are running.",
      );
    } finally {
      setUploading(false);

      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  }

  if (document) {
    return (
      <div className="composer-document-chip">
        <FileText size={17} />

        <div>
          <strong>{document.filename}</strong>
          <span>{document.chunk_count} chunks ready</span>
        </div>

        <button
          type="button"
          onClick={onClear}
          aria-label="Stop using this document"
          title="Remove document"
        >
          <X size={16} />
        </button>
      </div>
    );
  }

  return (
    <div className="composer-upload">
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        hidden
        onChange={(event) => {
          handleFile(event.target.files?.[0]);
        }}
      />

      <button
        type="button"
        className="composer-plus-button"
        disabled={disabled || uploading}
        onClick={() => setMenuOpen((isOpen) => !isOpen)}
        aria-label="Add attachment"
        title="Add attachment"
      >
        <Plus size={20} />
      </button>

      {menuOpen && (
        <div className="upload-menu">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
          >
            <Upload size={17} />
            <span>Upload file</span>
          </button>
        </div>
      )}

      {(uploading || error) && (
        <div className={error ? "upload-status upload-error" : "upload-status"}>
          {error || `Processing PDF ${progress}%`}
        </div>
      )}
    </div>
  );
}
