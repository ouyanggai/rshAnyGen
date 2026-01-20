import { useState, useCallback, useEffect } from 'react';
import {
  DocumentArrowUpIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import knowledgeApi from '../../api/knowledge';

// 模拟文档列表
const mockDocuments = [
  {
    id: 'doc-1',
    name: '产品手册.pdf',
    size: '2.3 MB',
    uploadedAt: '2025-01-15',
    status: 'indexed',
    chunks: 45,
  },
  {
    id: 'doc-2',
    name: 'API文档.md',
    size: '156 KB',
    uploadedAt: '2025-01-14',
    status: 'indexed',
    chunks: 12,
  },
  {
    id: 'doc-3',
    name: 'FAQ.txt',
    size: '45 KB',
    uploadedAt: '2025-01-13',
    status: 'processing',
    chunks: 0,
  },
];

export default function KnowledgeBase() {
  const [documents, setDocuments] = useState(mockDocuments);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);

  // 处理文件上传
  const handleFileUpload = useCallback(async (file) => {
    const uploadId = Date.now();
    setUploadProgress({ id: uploadId, file: file.name, progress: 0 });

    try {
      // TODO: 调用实际的API
      // const result = await knowledgeApi.uploadFile(file);

      // 模拟上传进度
      for (let i = 0; i <= 100; i += 10) {
        await new Promise(resolve => setTimeout(resolve, 100));
        setUploadProgress(prev => ({ ...prev, progress: i }));
      }

      // 添加到文档列表
      setDocuments(prev => [
        {
          id: `doc-${uploadId}`,
          name: file.name,
          size: `${(file.size / 1024).toFixed(0)} KB`,
          uploadedAt: new Date().toISOString().split('T')[0],
          status: 'processing',
          chunks: 0,
        },
        ...prev,
      ]);

      setUploadProgress(null);
    } catch (error) {
      console.error('Upload error:', error);
      setUploadProgress(null);
    }
  }, []);

  // 拖拽处理
  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    files.forEach(handleFileUpload);
  }, [handleFileUpload]);

  const handleFileInput = useCallback((e) => {
    const files = Array.from(e.target.files);
    files.forEach(handleFileUpload);
  }, [handleFileUpload]);

  // 删除文档
  const handleDelete = (docId) => {
    if (confirm('确定要删除这个文档吗？')) {
      setDocuments(prev => prev.filter(doc => doc.id !== docId));
    }
  };

  // 统计信息
  const stats = {
    totalDocs: documents.length,
    indexedDocs: documents.filter(d => d.status === 'indexed').length,
    totalChunks: documents.reduce((sum, d) => sum + (d.chunks || 0), 0),
  };

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-2xl font-heading font-semibold mb-6">知识库管理</h2>

        {/* 统计卡片 */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <StatCard label="总文档数" value={stats.totalDocs} icon={DocumentArrowUp} />
          <StatCard label="已索引" value={stats.indexedDocs} icon={CheckCircle} color="green" />
          <StatCard label="向量数量" value={stats.totalChunks} icon={Clock} color="blue" />
        </div>

        {/* 上传区域 */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`
            relative border-2 border-dashed rounded-lg p-8 mb-6 transition-colors
            ${isDragging
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/50'
            }
          `}
        >
          <input
            type="file"
            id="file-upload"
            className="hidden"
            multiple
            accept=".txt,.md,.pdf,.doc,.docx"
            onChange={handleFileInput}
          />
          <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
            <DocumentArrowUpIcon className="w-12 h-12 text-text-muted mb-4" />
            <p className="font-medium text-text-primary mb-1">
              拖拽文件到这里或点击上传
            </p>
            <p className="text-sm text-text-muted">
              支持 TXT, MD, PDF, DOC, DOCX 格式
            </p>
          </label>

          {/* 上传进度 */}
          {uploadProgress && (
            <div className="absolute inset-0 bg-white/90 flex items-center justify-center rounded-lg">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 relative">
                  <div className="absolute inset-0 border-4 border-gray-200 rounded-full" />
                  <div
                    className="absolute inset-0 border-4 border-primary rounded-full animate-spin"
                    style={{
                      borderRightColor: 'transparent',
                      borderBottomColor: 'transparent',
                    }}
                  />
                  <div className="absolute inset-0 flex items-center justify-center text-sm font-medium">
                    {uploadProgress.progress}%
                  </div>
                </div>
                <p className="text-sm text-text-muted">正在上传 {uploadProgress.file}</p>
              </div>
            </div>
          )}
        </div>

        {/* 文档列表 */}
        <div className="card">
          <div className="px-6 py-4 border-b border-border">
            <h3 className="font-semibold">已上传文档</h3>
          </div>
          <div className="divide-y divide-border">
            {documents.length === 0 ? (
              <div className="p-8 text-center text-text-muted">
                还没有上传任何文档
              </div>
            ) : (
              documents.map((doc) => (
                <DocumentRow
                  key={doc.id}
                  document={doc}
                  onDelete={() => handleDelete(doc.id)}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon: Icon, color = 'primary' }) {
  const colorClasses = {
    primary: 'bg-primary/10 text-primary',
    green: 'bg-green-500/10 text-green-500',
    blue: 'bg-blue-500/10 text-blue-500',
  };

  return (
    <div className="card p-4">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg ${colorClasses[color]} flex items-center justify-center`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-semibold">{value}</p>
          <p className="text-sm text-text-muted">{label}</p>
        </div>
      </div>
    </div>
  );
}

function DocumentRow({ document, onDelete }) {
  const statusConfig = {
    indexed: { label: '已索引', color: 'text-green-500 bg-green-50', icon: CheckCircle },
    processing: { label: '处理中', color: 'text-yellow-500 bg-yellow-50', icon: Clock },
    error: { label: '失败', color: 'text-red-500 bg-red-50', icon: XCircle },
  };

  const config = statusConfig[document.status] || statusConfig.processing;
  const StatusIcon = config.icon;

  return (
    <div className="flex items-center justify-between px-6 py-4 hover:bg-bg-tertiary transition-colors">
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-lg bg-bg-tertiary flex items-center justify-center">
          <DocumentArrowUpIcon className="w-5 h-5 text-text-muted" />
        </div>
        <div>
          <p className="font-medium text-text-primary">{document.name}</p>
          <p className="text-sm text-text-muted">
            {document.size} · {document.uploadedAt} · {document.chunks} 个分块
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}>
          <StatusIcon className="w-3.5 h-3.5" />
          {config.label}
        </span>
        <button
          onClick={onDelete}
          className="p-2 text-text-muted hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
        >
          <TrashIcon className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
