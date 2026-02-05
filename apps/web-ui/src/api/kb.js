/**
 * Knowledge Base API
 */
import api from './client';

const BASE_URL = '/v1/kb';

// Get all knowledge bases
export async function getKbs() {
  const response = await api.get(BASE_URL);
  return response.data;
}

// Create a new knowledge base
export async function createKb(name, description = '', embeddingModel = 'zhipu') {
  const response = await api.post(BASE_URL, {
    name,
    description,
    embedding_model: embeddingModel,
  });

  return response.data;
}

// Get details of a knowledge base
export async function getKb(kbId) {
  const response = await api.get(`${BASE_URL}/${kbId}`);
  return response.data;
}

// Update a knowledge base
export async function updateKb(kbId, data) {
  const response = await api.put(`${BASE_URL}/${kbId}`, data);
  return response.data;
}

// Delete a knowledge base
export async function deleteKb(kbId) {
  const response = await api.delete(`${BASE_URL}/${kbId}`);
  return response.data;
}
