/**
 * Knowledge Base API
 */

const BASE_URL = '/api/v1/kb';

// Get all knowledge bases
export async function getKbs() {
  const response = await fetch(BASE_URL);
  if (!response.ok) {
    throw new Error('Failed to fetch knowledge bases');
  }
  return response.json();
}

// Create a new knowledge base
export async function createKb(name, description = '', embeddingModel = 'zhipu') {
  const response = await fetch(BASE_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name,
      description,
      embedding_model: embeddingModel,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create knowledge base');
  }

  return response.json();
}

// Get details of a knowledge base
export async function getKb(kbId) {
  const response = await fetch(`${BASE_URL}/${kbId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch knowledge base details');
  }
  return response.json();
}

// Update a knowledge base
export async function updateKb(kbId, data) {
  const response = await fetch(`${BASE_URL}/${kbId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error('Failed to update knowledge base');
  }

  return response.json();
}

// Delete a knowledge base
export async function deleteKb(kbId) {
  const response = await fetch(`${BASE_URL}/${kbId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error('Failed to delete knowledge base');
  }

  return response.json();
}
