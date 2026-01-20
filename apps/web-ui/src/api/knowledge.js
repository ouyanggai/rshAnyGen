/**
 * 知识库 API
 */
import api from './client';

// 上传文件
export const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/ingest/file', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// 摄取文本
export const ingestText = async (text, docId, metadata = {}) => {
  const response = await api.post('/ingest/text', {
    text,
    doc_id: docId,
    metadata,
  });
  return response.data;
};

// 获取集合状态
export const getCollectionStatus = async () => {
  const response = await api.get('/');
  return response.data;
};

export default {
  uploadFile,
  ingestText,
  getCollectionStatus,
};
