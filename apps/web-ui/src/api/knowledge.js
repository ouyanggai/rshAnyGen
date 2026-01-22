/**
 * 知识库 API
 */
import api from './client';

// 获取文档列表 (Scoped to KB)
export const getDocuments = async (kbId) => {
  const response = await api.get(`/v1/kb/${kbId}/documents`);
  return response.data;
};

// 上传文件 (Scoped to KB)
export const uploadFile = async (file, kbId) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post(`/v1/kb/${kbId}/documents`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000, // 5 minutes
  });
  return response.data;
};

// 开始索引 (Scoped to KB)
export const indexDocument = async (docId, kbId) => {
  const response = await api.post(`/v1/kb/${kbId}/documents/${docId}/index`);
  return response.data;
};

// 删除文档 (Global ID)
export const deleteDocument = async (docId) => {
  const response = await api.delete(`/v1/documents/${docId}`);
  return response.data;
};

// 摄取文本 (Scoped to KB)
export const ingestText = async (text, docId, kbId = 'default', metadata = {}) => {
  const response = await api.post('/v1/ingest/text', {
    text,
    doc_id: docId,
    kb_id: kbId,
    metadata,
  });
  return response.data;
};

export default {
  uploadFile,
  indexDocument,
  ingestText,
  getDocuments,
  deleteDocument,
};
