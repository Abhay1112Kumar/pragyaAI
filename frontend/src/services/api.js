import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 120000,
});

export async function sendMessage(message) {
  const response = await api.post("/chat", {
    message,
  });

  return response.data;
}

export default api;