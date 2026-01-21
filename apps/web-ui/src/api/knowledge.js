/**
 * 知识库 API
 */
import api from './client';

// 上传文件 (Upload only)
export const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/v1/documents', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000,
  });
  return response.data;
};

// 开始索引 (Index existing document)
export const indexDocument = async (docId) => {
  const response = await api.post(`/v1/documents/${docId}/index`);
  return response.data;
};

// 获取文档列表
export const getDocuments = async () => {
  // 路径改为 /v1/documents
  const response = await api.get('/v1/documents');
  return response.data;
};

// 删除文档
export const deleteDocument = async (docId) => {
  // 路径改为 /v1/documents/${docId}
  const response = await api.delete(`/v1/documents/${docId}`);
  return response.data;
};

// 摄取文本
export const ingestText = async (text, docId, metadata = {}) => {
  // 路径改为 /v1/ingest/text
  const response = await api.post('/v1/ingest/text', {
    text,
    doc_id: docId,
    metadata,
  });
  return response.data;
};

// 获取集合状态
export const getCollectionStatus = async () => {
  const response = await api.get('/'); // Keep root for now, or update if health check is elsewhere
  return response.data;
};

export default {
  uploadFile,
  indexDocument,
  ingestText,
  getCollectionStatus,
  getDocuments,
  deleteDocument,
};
