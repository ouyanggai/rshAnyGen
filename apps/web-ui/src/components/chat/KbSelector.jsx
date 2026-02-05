import { useState, useEffect, useRef } from 'react';
import { getKbs } from '../../api/kb';
import { BookOpenIcon, XMarkIcon, PlusIcon, ChevronDownIcon } from '@heroicons/react/24/outline';

export default function KbSelector({ selectedKbs, onChange, className = '' }) {
  const [kbs, setKbs] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Load KBs
  useEffect(() => {
    loadKbs();
  }, []);

  const loadKbs = async () => {
    try {
      const data = await getKbs();
      setKbs(data);
    } catch (e) {
      console.error(e);
    }
  };

  // Click outside to close
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (kb) => {
    if (!selectedKbs.find(k => k.kb_id === kb.kb_id)) {
      onChange([...selectedKbs, kb]);
    }
    setIsOpen(false);
  };

  const handleRemove = (kbId) => {
    onChange(selectedKbs.filter(k => k.kb_id !== kbId));
  };

  const availableKbs = kbs.filter(k => !selectedKbs.find(sk => sk.kb_id === k.kb_id));

  return (
    <div className={['flex flex-wrap gap-2 items-center', className].join(' ')}>
      {selectedKbs.map(kb => (
        <div
          key={kb.kb_id}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm border border-border dark:border-border-dark bg-bg-tertiary dark:bg-bg-input-dark text-text-primary dark:text-text-primary-dark"
        >
          <BookOpenIcon className="w-4 h-4 text-text-muted" />
          <span>{kb.name}</span>
          <button
            type="button"
            onClick={() => handleRemove(kb.kb_id)}
            className="rounded-full p-0.5 hover:bg-white/70 dark:hover:bg-white/10 transition-colors"
            title="移除知识库"
          >
            <XMarkIcon className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}

      <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className={[
            'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-colors',
            'bg-white dark:bg-bg-card-dark border border-dashed border-border dark:border-border-dark',
            'text-text-secondary dark:text-text-secondary-dark hover:text-text-primary dark:hover:text-text-primary-dark hover:bg-bg-tertiary/70 dark:hover:bg-white/5',
          ].join(' ')}
        >
          <PlusIcon className="w-4 h-4" />
          <span>{selectedKbs.length === 0 ? '选择知识库' : '添加知识库'}</span>
          <ChevronDownIcon className="w-3.5 h-3.5" />
        </button>

        {isOpen && (
          <div className="absolute top-full left-0 mt-2 w-80 surface rounded-xl z-50 overflow-hidden shadow-xl border border-border dark:border-border-dark">
            <div className="max-h-60 overflow-y-auto py-1">
              {availableKbs.length > 0 ? (
                availableKbs.map(kb => (
                  <button
                    key={kb.kb_id}
                    onClick={() => handleSelect(kb)}
                    className="w-full text-left px-4 py-2.5 text-sm hover:bg-bg-tertiary dark:hover:bg-white/5 flex items-start gap-2 text-text-primary dark:text-text-primary-dark transition-colors border-b last:border-0 border-border/60 dark:border-border-dark/60"
                  >
                    <BookOpenIcon className="w-4 h-4 text-text-muted mt-0.5 flex-shrink-0" />
                    <div className="flex flex-col min-w-0">
                      <span className="font-medium truncate" title={kb.name}>{kb.name}</span>
                      {kb.description && (
                        <span className="text-xs text-text-muted truncate" title={kb.description}>
                          {kb.description}
                        </span>
                      )}
                    </div>
                  </button>
                ))
              ) : (
                <div className="px-4 py-3 text-sm text-text-muted text-center">
                  没有更多知识库
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
