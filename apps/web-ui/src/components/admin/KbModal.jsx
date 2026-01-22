import { useState, useEffect } from 'react';
import { Dialog } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { createKb, updateKb } from '../../api/kb';

export default function KbModal({ isOpen, onClose, kb = null, onSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    embedding_model: 'zhipu'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (kb) {
      setFormData({
        name: kb.name,
        description: kb.description || '',
        embedding_model: kb.embedding_model
      });
    } else {
      setFormData({
        name: '',
        description: '',
        embedding_model: 'zhipu'
      });
    }
    setError(null);
  }, [kb, isOpen]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (kb) {
        await updateKb(kb.kb_id, formData);
      } else {
        await createKb(formData.name, formData.description, formData.embedding_model);
      }
      onSuccess();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />

      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="mx-auto max-w-md w-full rounded-2xl bg-white dark:bg-bg-card-dark p-6 shadow-xl border border-border dark:border-border-dark">
          <div className="flex items-center justify-between mb-4">
            <Dialog.Title className="text-lg font-medium text-text-primary dark:text-text-primary-dark">
              {kb ? '编辑知识库' : '新建知识库'}
            </Dialog.Title>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-text-primary dark:hover:text-text-primary-dark transition-colors"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary-dark mb-1">
                名称
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark border border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-text-primary dark:text-text-primary-dark"
                placeholder="知识库名称"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary-dark mb-1">
                描述
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark border border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-text-primary dark:text-text-primary-dark resize-none h-24"
                placeholder="可选描述..."
              />
            </div>

            {!kb && (
              <div>
                <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary-dark mb-1">
                  Embedding 模型
                </label>
                <select
                  value={formData.embedding_model}
                  onChange={(e) => setFormData({ ...formData, embedding_model: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark border border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-text-primary dark:text-text-primary-dark"
                >
                  <option value="zhipu">Zhipu AI (zhipu)</option>
                  <option value="openai">OpenAI (text-embedding-3-small)</option>
                  <option value="qwen">Qwen (text-embedding-v3)</option>
                </select>
              </div>
            )}

            {error && (
              <div className="text-sm text-red-500 bg-red-50 dark:bg-red-900/20 p-2 rounded-lg">
                {error}
              </div>
            )}

            <div className="flex justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-text-secondary dark:text-text-secondary-dark hover:bg-bg-tertiary dark:hover:bg-white/5 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary-600 rounded-lg shadow-sm shadow-primary/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? '保存中...' : '保存'}
              </button>
            </div>
          </form>
        </Dialog.Panel>
      </div>
    </Dialog>
  );
}
