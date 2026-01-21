import { useState, useCallback, useEffect } from 'react';
import {
  DocumentArrowUpIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  PlayIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import knowledgeApi from '../../api/knowledge';

export default function KnowledgeBase() {
  const [documents, setDocuments] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);

  // Fetch documents on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const docs = await knowledgeApi.getDocuments();
      // Format size and date
      const formattedDocs = docs.map(doc => ({
        ...doc,
        size: formatSize(doc.size),
        uploadedAt: new Date(doc.uploaded_at).toLocaleString(), // Use toLocaleString for better readability
      }));
      setDocuments(formattedDocs);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  // 处理文件上传
  const handleFileUpload = useCallback(async (file) => {
    const uploadId = Date.now();
    setUploadProgress({ id: uploadId, file: file.name, progress: 0 });

    try {
      // 模拟上传进度 (since actual progress isn't streamed yet)
      const interval = setInterval(() => {
        setUploadProgress(prev => {
          if (!prev || prev.progress >= 90) return prev;
          return { ...prev, progress: prev.progress + 10 };
        });
      }, 500);

      await knowledgeApi.uploadFile(file);
      
      clearInterval(interval);
      setUploadProgress(prev => ({ ...prev, progress: 100 }));
      
      // Refresh list
      await fetchDocuments();

      setUploadProgress(null);
    } catch (error) {
      console.error('Upload error:', error);
      setUploadProgress(null);
      alert(`上传失败: ${error.response?.data?.detail || error.message}`);
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

  // 索引文档
  const handleIndex = async (docId) => {
    try {
      await knowledgeApi.indexDocument(docId);
      // Update status locally
      setDocuments(prev => prev.map(doc => 
        doc.id === docId ? { ...doc, status: 'processing' } : doc
      ));
      // Poll for updates (optional, or rely on manual refresh/socket)
      setTimeout(fetchDocuments, 2000);
    } catch (error) {
      console.error('Index error:', error);
      alert('索引失败');
    }
  };

  // 删除文档
  const handleDelete = async (docId) => {
    if (confirm('确定要删除这个文档吗？')) {
      try {
        await knowledgeApi.deleteDocument(docId);
        setDocuments(prev => prev.filter(doc => doc.id !== docId));
      } catch (error) {
        console.error('Delete error:', error);
        alert('删除失败');
      }
    }
  };

  // 统计信息
  const stats = {
    totalDocs: documents.length,
    indexedDocs: documents.filter(d => d.status === 'indexed').length,
    totalChunks: documents.reduce((sum, d) => sum + (d.chunks || 0), 0),
  };

  return (
    <div className="p-6 bg-bg-primary dark:bg-bg-dark min-h-full transition-colors duration-300">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-2xl font-heading font-semibold mb-6 text-text-primary dark:text-text-primary-dark">知识库管理</h2>

        {/* 统计卡片 */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <StatCard label="总文档数" value={stats.totalDocs} icon={DocumentArrowUpIcon} />
          <StatCard label="已索引" value={stats.indexedDocs} icon={CheckCircleIcon} color="green" />
          <StatCard label="向量数量" value={stats.totalChunks} icon={ClockIcon} color="blue" />
        </div>

        {/* 上传区域 */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`
            relative border-2 border-dashed rounded-lg p-8 mb-6 transition-colors
            ${isDragging
              ? 'border-primary bg-primary/5 dark:bg-primary/10'
              : 'border-border dark:border-border-dark hover:border-primary/50 dark:hover:border-primary/50'
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
            <DocumentArrowUpIcon className="w-12 h-12 text-text-muted dark:text-text-muted/60 mb-4" />
            <p className="font-medium text-text-primary dark:text-text-primary-dark mb-1">
              拖拽文件到这里或点击上传
            </p>
            <p className="text-sm text-text-muted dark:text-text-secondary-dark">
              支持 TXT, MD, PDF, DOC, DOCX 格式
            </p>
          </label>

          {/* 上传进度 */}
          {uploadProgress && (
            <div className="absolute inset-0 bg-white/90 dark:bg-bg-card-dark/90 flex items-center justify-center rounded-lg">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 relative">
                  <div className="absolute inset-0 border-4 border-gray-200 dark:border-gray-700 rounded-full" />
                  <div
                    className="absolute inset-0 border-4 border-primary rounded-full animate-spin"
                    style={{
                      borderRightColor: 'transparent',
                      borderBottomColor: 'transparent',
                    }}
                  />
                  <div className="absolute inset-0 flex items-center justify-center text-sm font-medium text-text-primary dark:text-text-primary-dark">
                    {uploadProgress.progress}%
                  </div>
                </div>
                <p className="text-sm text-text-muted dark:text-text-secondary-dark">正在上传 {uploadProgress.file}</p>
              </div>
            </div>
          )}
        </div>

        {/* 文档列表 */}
        <div className="card bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark shadow-elevation-1 rounded-2xl overflow-hidden">
          <div className="px-6 py-4 border-b border-border dark:border-border-dark">
            <h3 className="font-semibold text-text-primary dark:text-text-primary-dark">已上传文档</h3>
          </div>
          <div className="divide-y divide-border dark:divide-border-dark">
            {documents.length === 0 ? (
              <div className="p-8 text-center text-text-muted dark:text-text-muted/60">
                还没有上传任何文档
              </div>
            ) : (
              documents.map((doc) => (
                <DocumentRow
                  key={doc.id}
                  document={doc}
                  onIndex={() => handleIndex(doc.id)}
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
    primary: 'bg-primary/10 text-primary dark:bg-primary/20 dark:text-primary-400',
    green: 'bg-green-500/10 text-green-500 dark:bg-green-500/20 dark:text-green-400',
    blue: 'bg-blue-500/10 text-blue-500 dark:bg-blue-500/20 dark:text-blue-400',
  };

  return (
    <div className="card p-4 bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark shadow-elevation-1 rounded-xl">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg ${colorClasses[color]} flex items-center justify-center`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-semibold text-text-primary dark:text-text-primary-dark">{value}</p>
          <p className="text-sm text-text-muted dark:text-text-secondary-dark">{label}</p>
        </div>
      </div>
    </div>
  );
}

function DocumentRow({ document, onDelete, onIndex }) {
  const statusConfig = {
    indexed: { label: '已索引', color: 'text-green-500 bg-green-50 dark:bg-green-900/20 dark:text-green-400', icon: CheckCircleIcon },
    processing: { label: '处理中', color: 'text-yellow-500 bg-yellow-50 dark:bg-yellow-900/20 dark:text-yellow-400', icon: ArrowPathIcon, animate: true },
    uploaded: { label: '待索引', color: 'text-blue-500 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400', icon: ClockIcon },
    error: { label: '失败', color: 'text-red-500 bg-red-50 dark:bg-red-900/20 dark:text-red-400', icon: XCircleIcon },
  };

  const config = statusConfig[document.status] || statusConfig.uploaded;
  const StatusIcon = config.icon;

  return (
    <div className="flex items-center justify-between px-6 py-4 hover:bg-bg-tertiary dark:hover:bg-white/5 transition-colors">
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark flex items-center justify-center">
          <DocumentArrowUpIcon className="w-5 h-5 text-text-muted dark:text-text-secondary-dark" />
        </div>
        <div>
          <p className="font-medium text-text-primary dark:text-text-primary-dark">{document.name}</p>
          <p className="text-sm text-text-muted dark:text-text-secondary-dark">
            {document.size} · {document.uploadedAt} · {document.chunks} 个分块
          </p>
          {document.error_message && (
            <p className="text-xs text-red-500 dark:text-red-400 mt-1">{document.error_message}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}>
          <StatusIcon className={`w-3.5 h-3.5 ${config.animate ? 'animate-spin' : ''}`} />
          {config.label}
        </span>
        
        {document.status === 'uploaded' && (
          <button
            onClick={onIndex}
            className="p-2 text-text-muted dark:text-text-secondary-dark hover:text-primary dark:hover:text-primary-400 hover:bg-primary/10 dark:hover:bg-primary/20 rounded-lg transition-all"
            title="开始索引"
          >
            <PlayIcon className="w-4 h-4" />
          </button>
        )}
        
        <button
          onClick={onDelete}
          className="p-2 text-text-muted dark:text-text-secondary-dark hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all"
          title="删除文档"
        >
          <TrashIcon className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
