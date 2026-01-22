import { useState, useEffect, useRef } from 'react';
import { getKbs } from '../../api/kb';
import { BookOpenIcon, XMarkIcon, PlusIcon, ChevronDownIcon } from '@heroicons/react/24/outline';

export default function KbSelector({ selectedKbs, onChange }) {
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
    <div className="flex flex-wrap gap-2 items-center mb-2 px-4 max-w-3xl mx-auto">
      {selectedKbs.map(kb => (
        <div key={kb.kb_id} className="flex items-center gap-1 px-3 py-1.5 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 rounded-full text-sm border border-primary-200 dark:border-primary-800 transition-all shadow-sm">
          <BookOpenIcon className="w-4 h-4" />
          <span>{kb.name}</span>
          <button onClick={() => handleRemove(kb.kb_id)} className="hover:text-primary-900 dark:hover:text-primary-100 rounded-full p-0.5 hover:bg-primary-100 dark:hover:bg-primary-800 transition-colors">
            <XMarkIcon className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}

      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-all border ${
            selectedKbs.length === 0 
              ? 'bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:shadow-sm hover:-translate-y-0.5' 
              : 'bg-white dark:bg-gray-800 border-dashed border-gray-300 dark:border-gray-700 text-gray-500 hover:text-primary hover:border-primary dark:hover:border-primary-500'
          }`}
        >
          {selectedKbs.length === 0 ? (
            <>
              <BookOpenIcon className="w-4 h-4" />
              <span>选择知识库</span>
            </>
          ) : (
            <>
              <PlusIcon className="w-4 h-4" />
              <span>添加</span>
            </>
          )}
          <ChevronDownIcon className="w-3.5 h-3.5" />
        </button>

        {isOpen && (
          <div className="absolute top-full left-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-100 dark:border-gray-700 z-50 overflow-hidden animate-fade-in-up">
            <div className="max-h-60 overflow-y-auto py-1 custom-scrollbar">
              {availableKbs.length > 0 ? (
                availableKbs.map(kb => (
                  <button
                    key={kb.kb_id}
                    onClick={() => handleSelect(kb)}
                    className="w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-700/50 flex items-center gap-2 text-gray-700 dark:text-gray-200 transition-colors border-b last:border-0 border-gray-50 dark:border-gray-700/30"
                  >
                    <BookOpenIcon className="w-4 h-4 text-gray-400" />
                    <div className="flex flex-col">
                      <span className="font-medium truncate">{kb.name}</span>
                      {kb.description && <span className="text-xs text-gray-400 truncate max-w-[160px]">{kb.description}</span>}
                    </div>
                  </button>
                ))
              ) : (
                <div className="px-4 py-3 text-sm text-gray-400 text-center">
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
