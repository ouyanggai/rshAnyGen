import { useState, useCallback, useEffect } from 'react';
import {
  DocumentArrowUpIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  PlayIcon,
  ArrowPathIcon,
  PlusIcon,
  PencilSquareIcon,
  BookOpenIcon,
  ChevronRightIcon
} from '@heroicons/react/24/outline';
import knowledgeApi from '../../api/knowledge';
import { getKbs, deleteKb } from '../../api/kb';
import KbModal from '../../components/admin/KbModal';

export default function KnowledgeBase() {
  const [kbs, setKbs] = useState([]);
  const [selectedKb, setSelectedKb] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  
  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingKb, setEditingKb] = useState(null);

  // Load KBs on mount
  useEffect(() => {
    loadKbs();
  }, []);

  // Load documents when KB selected
  useEffect(() => {
    if (selectedKb) {
      fetchDocuments(selectedKb.kb_id);
    } else {
      setDocuments([]);
    }
  }, [selectedKb]);

  const loadKbs = async () => {
    try {
      const data = await getKbs();
      setKbs(data);
      // If we have KBs but none selected, select the first one
      if (data.length > 0 && !selectedKb) {
        setSelectedKb(data[0]);
      } else if (data.length === 0) {
        setSelectedKb(null);
      } else if (selectedKb) {
        // Refresh selected KB data
        const updated = data.find(k => k.kb_id === selectedKb.kb_id);
        if (updated) setSelectedKb(updated);
      }
    } catch (e) {
      console.error('Failed to load KBs:', e);
    }
  };

  const fetchDocuments = async (kbId) => {
    try {
      const docs = await knowledgeApi.getDocuments(kbId);
      const formattedDocs = docs.map(doc => ({
        ...doc,
        size: formatSize(doc.size),
        uploadedAt: new Date(doc.uploaded_at).toLocaleString(),
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

  // KB Operations
  const handleCreateKb = () => {
    setEditingKb(null);
    setIsModalOpen(true);
  };

  const handleEditKb = (kb, e) => {
    e.stopPropagation();
    setEditingKb(kb);
    setIsModalOpen(true);
  };

  const handleDeleteKb = async (kb, e) => {
    e.stopPropagation();
    if (confirm(`确定要删除知识库 "${kb.name}" 吗？此操作将删除所有相关文档和向量数据且无法恢复。`)) {
      try {
        await deleteKb(kb.kb_id);
        // Refresh list
        const newKbs = kbs.filter(k => k.kb_id !== kb.kb_id);
        setKbs(newKbs);
        if (selectedKb?.kb_id === kb.kb_id) {
          setSelectedKb(newKbs.length > 0 ? newKbs[0] : null);
        }
      } catch (err) {
        alert(`删除失败: ${err.message}`);
      }
    }
  };

  const handleKbSuccess = () => {
    loadKbs();
  };

  // Document Operations
  const handleFileUpload = useCallback(async (file) => {
    if (!selectedKb) return;
    
    const uploadId = Date.now();
    setUploadProgress({ id: uploadId, file: file.name, progress: 0 });

    try {
      const interval = setInterval(() => {
        setUploadProgress(prev => {
          if (!prev || prev.progress >= 90) return prev;
          return { ...prev, progress: prev.progress + 10 };
        });
      }, 500);

      await knowledgeApi.uploadFile(file, selectedKb.kb_id);
      
      clearInterval(interval);
      setUploadProgress(prev => ({ ...prev, progress: 100 }));
      
      await fetchDocuments(selectedKb.kb_id);
      // Refresh KB stats
      loadKbs();

      setUploadProgress(null);
    } catch (error) {
      console.error('Upload error:', error);
      setUploadProgress(null);
      alert(`上传失败: ${error.response?.data?.detail || error.message}`);
    }
  }, [selectedKb]);

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

  const handleIndex = async (docId) => {
    if (!selectedKb) return;
    try {
      await knowledgeApi.indexDocument(docId, selectedKb.kb_id);
      setDocuments(prev => prev.map(doc => 
        doc.id === docId ? { ...doc, status: 'processing' } : doc
      ));
      setTimeout(() => {
        fetchDocuments(selectedKb.kb_id);
        loadKbs();
      }, 2000);
    } catch (error) {
      console.error('Index error:', error);
      alert('索引失败');
    }
  };

  const handleDeleteDoc = async (docId) => {
    if (confirm('确定要删除这个文档吗？')) {
      try {
        await knowledgeApi.deleteDocument(docId);
        setDocuments(prev => prev.filter(doc => doc.id !== docId));
        // Refresh KB stats
        loadKbs();
      } catch (error) {
        console.error('Delete error:', error);
        alert('删除失败');
      }
    }
  };

  return (
    <div className="flex h-full bg-bg-primary dark:bg-bg-dark overflow-hidden">
      {/* Sidebar - KB List */}
      <div className="w-64 border-r border-border dark:border-border-dark flex flex-col bg-white dark:bg-bg-card-dark">
        <div className="p-4 border-b border-border dark:border-border-dark flex justify-between items-center">
          <h2 className="font-semibold text-text-primary dark:text-text-primary-dark">知识库列表</h2>
          <button 
            onClick={handleCreateKb}
            className="p-1.5 rounded-lg hover:bg-bg-tertiary dark:hover:bg-white/5 text-primary transition-colors"
            title="新建知识库"
          >
            <PlusIcon className="w-5 h-5" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {kbs.map(kb => (
            <div 
              key={kb.kb_id}
              onClick={() => setSelectedKb(kb)}
              className={`
                group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all
                ${selectedKb?.kb_id === kb.kb_id 
                  ? 'bg-primary/10 text-primary dark:bg-primary/20 dark:text-primary-400' 
                  : 'text-text-secondary dark:text-text-secondary-dark hover:bg-bg-tertiary dark:hover:bg-white/5'
                }
              `}
            >
              <div className="flex items-center gap-3 overflow-hidden">
                <BookOpenIcon className="w-5 h-5 flex-shrink-0" />
                <div className="flex flex-col overflow-hidden">
                  <span className="font-medium truncate">{kb.name}</span>
                  <span className="text-xs opacity-70 truncate">{kb.doc_count} 文档 · {kb.chunk_count} 分块</span>
                </div>
              </div>
              
              <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                <button 
                  onClick={(e) => handleEditKb(kb, e)}
                  className="p-1 hover:bg-white/50 dark:hover:bg-black/20 rounded"
                >
                  <PencilSquareIcon className="w-4 h-4" />
                </button>
                <button 
                  onClick={(e) => handleDeleteKb(kb, e)}
                  className="p-1 hover:text-red-500 hover:bg-white/50 dark:hover:bg-black/20 rounded"
                >
                  <TrashIcon className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}

          {kbs.length === 0 && (
            <div className="text-center py-8 text-sm text-text-muted dark:text-text-secondary-dark">
              暂无知识库<br/>点击右上角创建
            </div>
          )}
        </div>
      </div>

      {/* Main Content - Document List */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {selectedKb ? (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-5xl mx-auto">
              <div className="mb-6">
                <h1 className="text-2xl font-heading font-bold text-text-primary dark:text-text-primary-dark mb-2">
                  {selectedKb.name}
                </h1>
                <p className="text-text-secondary dark:text-text-secondary-dark">
                  {selectedKb.description || '暂无描述'}
                </p>
                <div className="mt-2 text-xs text-text-muted flex gap-4">
                  <span>ID: {selectedKb.kb_id}</span>
                  <span>Model: {selectedKb.embedding_model}</span>
                </div>
              </div>

              {/* Upload Area */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`
                  relative border-2 border-dashed rounded-xl p-8 mb-6 transition-all duration-200
                  ${isDragging
                    ? 'border-primary bg-primary/5 scale-[1.01]'
                    : 'border-border dark:border-border-dark hover:border-primary/50 bg-white/50 dark:bg-bg-card-dark/50'
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
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                    <DocumentArrowUpIcon className="w-6 h-6 text-primary" />
                  </div>
                  <p className="font-medium text-text-primary dark:text-text-primary-dark mb-1">
                    点击或拖拽上传文档
                  </p>
                  <p className="text-sm text-text-muted">
                    支持 TXT, MD, PDF, DOCX (单个文件最大 20MB)
                  </p>
                </label>

                {uploadProgress && (
                  <div className="absolute inset-0 bg-white/95 dark:bg-bg-card-dark/95 flex flex-col items-center justify-center rounded-xl z-10 backdrop-blur-sm">
                    <div className="w-48 h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden mb-3">
                      <div 
                        className="h-full bg-primary transition-all duration-300"
                        style={{ width: `${uploadProgress.progress}%` }}
                      />
                    </div>
                    <p className="text-sm font-medium text-text-primary dark:text-text-primary-dark">
                      正在上传 {uploadProgress.file}...
                    </p>
                  </div>
                )}
              </div>

              {/* Documents Table */}
              <div className="bg-white dark:bg-bg-card-dark rounded-xl border border-border dark:border-border-dark shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-border dark:border-border-dark flex justify-between items-center bg-gray-50/50 dark:bg-white/5">
                  <h3 className="font-semibold text-text-primary dark:text-text-primary-dark">
                    文档列表 ({documents.length})
                  </h3>
                </div>
                
                <div className="divide-y divide-border dark:divide-border-dark">
                  {documents.length === 0 ? (
                    <div className="p-12 text-center">
                      <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                        <BookOpenIcon className="w-8 h-8 text-gray-400" />
                      </div>
                      <p className="text-text-muted">还没有上传任何文档</p>
                    </div>
                  ) : (
                    documents.map((doc) => (
                      <DocumentRow
                        key={doc.id}
                        document={doc}
                        onIndex={() => handleIndex(doc.id)}
                        onDelete={() => handleDeleteDoc(doc.id)}
                      />
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-text-muted p-8">
            <BookOpenIcon className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-lg">请选择或创建一个知识库</p>
          </div>
        )}
      </div>

      <KbModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        kb={editingKb}
        onSuccess={handleKbSuccess}
      />
    </div>
  );
}

function DocumentRow({ document, onDelete, onIndex }) {
  const statusConfig = {
    indexed: { label: '已索引', color: 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400', icon: CheckCircleIcon },
    processing: { label: '处理中', color: 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 dark:text-yellow-400', icon: ArrowPathIcon, animate: true },
    uploaded: { label: '待索引', color: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400', icon: ClockIcon },
    error: { label: '失败', color: 'text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400', icon: XCircleIcon },
  };

  const config = statusConfig[document.status] || statusConfig.uploaded;
  const StatusIcon = config.icon;

  return (
    <div className="group flex items-center justify-between px-6 py-4 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
      <div className="flex items-center gap-4 min-w-0">
        <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 text-gray-500">
          <DocumentArrowUpIcon className="w-5 h-5" />
        </div>
        <div className="min-w-0">
          <p className="font-medium text-text-primary dark:text-text-primary-dark truncate pr-4">{document.name}</p>
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <span>{document.size}</span>
            <span>·</span>
            <span>{document.uploadedAt}</span>
            {document.chunks > 0 && (
              <>
                <span>·</span>
                <span>{document.chunks} 块</span>
              </>
            )}
          </div>
          {document.error_message && (
            <p className="text-xs text-red-500 mt-1 truncate max-w-md">{document.error_message}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4 flex-shrink-0">
        <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}>
          <StatusIcon className={`w-3.5 h-3.5 ${config.animate ? 'animate-spin' : ''}`} />
          {config.label}
        </span>
        
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {document.status === 'uploaded' && (
            <button
              onClick={onIndex}
              className="p-2 text-text-muted hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
              title="开始索引"
            >
              <PlayIcon className="w-4 h-4" />
            </button>
          )}
          
          <button
            onClick={onDelete}
            className="p-2 text-text-muted hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            title="删除文档"
          >
            <TrashIcon className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
