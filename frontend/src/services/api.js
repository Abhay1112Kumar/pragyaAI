import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
  timeout: 120000,
});

export async function sendMessage(message, documentId = null) {
  const response = await api.post("/chat", {
    message,
    document_id: documentId,
  });

  return response.data;
}

export async function uploadDocument(file, onUploadProgress) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post(
    "/documents/upload",
    formData,
    {
      onUploadProgress,
    },
  );

  return response.data;
}

export default api;