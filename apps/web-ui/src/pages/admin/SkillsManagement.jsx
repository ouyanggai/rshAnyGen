import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSkills } from '../../hooks/useSkills';
import InstallSkillModal from '../../components/admin/InstallSkillModal';
import {
  CubeIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  ArrowPathIcon,
  TrashIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const CATEGORY_META = {
  search: { label: '搜索', tone: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
  knowledge: { label: '知识库', tone: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' },
  tools: { label: '工具', tone: 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300' },
  chat: { label: '对话', tone: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' },
  text_processing: { label: '文本处理', tone: 'bg-slate-50 text-slate-700 dark:bg-white/5 dark:text-slate-200' },
};

function Pill({ children, tone }) {
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border border-transparent", tone)}>
      {children}
    </span>
  );
}

function Toggle({ enabled, disabled, onToggle }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      disabled={disabled}
      onClick={onToggle}
      className={cn(
        'relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary',
        enabled ? 'bg-primary' : 'bg-zinc-300 dark:bg-zinc-600',
        disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
      )}
    >
      <span
        className={cn(
          'inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm transition-transform',
          enabled ? 'translate-x-4.5' : 'translate-x-1'
        )}
      />
    </button>
  );
}

export default function SkillsManagement() {
  const { skills, loading, error, mutating, toggleSkill, deleteSkill, loadSkills } = useSkills();
  const [searchQuery, setSearchQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [installOpen, setInstallOpen] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 12;

  // Reset page when filter changes
  useEffect(() => {
    setPage(1);
  }, [searchQuery, category]);

  const filteredSkills = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return skills
      .filter((s) => {
        if (category !== 'all' && (s.category || 'other') !== category) return false;
        if (!q) return true;
        const hay = `${s.name || ''} ${s.id || ''} ${s.description || ''}`.toLowerCase();
        return hay.includes(q);
      })
      .sort((a, b) => {
        if (a.enabled !== b.enabled) return a.enabled ? -1 : 1;
        return String(a.name || a.id).localeCompare(String(b.name || b.id), 'zh-CN');
      });
  }, [skills, searchQuery, category]);

  const totalPages = Math.ceil(filteredSkills.length / pageSize);
  const paginatedSkills = filteredSkills.slice((page - 1) * pageSize, page * pageSize);

  const onDelete = useCallback(async (skill) => {
    if (!window.confirm(`确定要卸载技能 "${skill.name || skill.id}" 吗?`)) return;
    try { await deleteSkill(skill.id); } catch { }
  }, [deleteSkill]);

  if (loading) {
    return <div className="h-full flex items-center justify-center"><div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" /></div>;
  }

  return (
    <div className="min-h-full p-6 lg:p-8 animate-fade-in">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">技能管理</h1>
            <p className="text-sm text-muted-foreground mt-1">管理和安装 AI 技能插件。</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={loadSkills} disabled={mutating} className="p-2 text-muted-foreground hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors">
              <ArrowPathIcon className={cn("w-5 h-5", mutating && "animate-spin")} />
            </button>
            <button
              onClick={() => setInstallOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-primary to-secondary text-white rounded-lg shadow-sm hover:shadow-md transition-all font-medium text-sm"
            >
              <PlusIcon className="w-4 h-4" />
              安装技能
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 items-center bg-card border border-border p-1 rounded-xl shadow-sm">
           <div className="relative flex-1 w-full sm:w-auto">
             <MagnifyingGlassIcon className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
             <input
               value={searchQuery}
               onChange={(e) => setSearchQuery(e.target.value)}
               placeholder="搜索技能..."
               className="w-full pl-9 pr-3 py-2 bg-transparent border-none text-sm focus:ring-0 placeholder:text-muted-foreground"
             />
           </div>
           <div className="h-6 w-px bg-border hidden sm:block" />
           <select
             value={category}
             onChange={(e) => setCategory(e.target.value)}
             className="w-full sm:w-auto px-3 py-2 bg-transparent text-sm border-none focus:ring-0 text-muted-foreground font-medium cursor-pointer hover:text-foreground transition-colors"
           >
             <option value="all">所有分类</option>
             {Object.entries(CATEGORY_META).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
           </select>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {paginatedSkills.map((skill) => (
            <div key={skill.id} className="group relative flex flex-col rounded-xl border border-border bg-card transition-all hover:border-primary/50 hover:shadow-md">
              <div className="p-4 flex-1">
                <div className="flex items-start justify-between mb-3">
                   <div className="flex items-center gap-2">
                     <div className={cn("w-2 h-2 rounded-full", skill.enabled ? "bg-green-500" : "bg-zinc-300 dark:bg-zinc-600")} />
                     <h3 className="font-semibold text-sm truncate max-w-[120px]" title={skill.name}>{skill.name || skill.id}</h3>
                   </div>
                   <Toggle enabled={Boolean(skill.enabled)} disabled={mutating} onToggle={() => toggleSkill(skill.id)} />
                </div>
                
                <p className="text-xs text-muted-foreground line-clamp-2 min-h-[2.5em] mb-3">
                  {skill.description || '暂无描述'}
                </p>

                <div className="flex flex-wrap gap-1.5">
                   <Pill tone={CATEGORY_META[skill.category]?.tone || 'bg-zinc-100 text-zinc-600'}>
                     {CATEGORY_META[skill.category]?.label || skill.category || '其他'}
                   </Pill>
                   {skill.version && <Pill tone="bg-zinc-50 text-zinc-500">v{skill.version}</Pill>}
                </div>
              </div>

              <div className="px-4 py-3 border-t border-border/50 bg-zinc-50/50 dark:bg-zinc-900/50 flex items-center justify-between rounded-b-xl">
                 <code className="text-[10px] text-muted-foreground font-mono truncate max-w-[150px]">{skill.id}</code>
                 <button onClick={() => onDelete(skill)} className="p-1 text-muted-foreground hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100">
                   <TrashIcon className="w-4 h-4" />
                 </button>
              </div>
            </div>
          ))}
          
          {/* Empty State */}
          {filteredSkills.length === 0 && (
            <div className="col-span-full py-12 flex flex-col items-center justify-center text-muted-foreground">
               <CubeIcon className="w-12 h-12 mb-3 opacity-20" />
               <p className="text-sm">未找到技能</p>
            </div>
          )}
        </div>
        
        {/* Pagination */}
        {filteredSkills.length > 0 && (
          <div className="flex items-center justify-between border-t border-border pt-4">
            <span className="text-sm text-muted-foreground">
              显示 {paginatedSkills.length > 0 ? (page - 1) * pageSize + 1 : 0} 到 {Math.min(page * pageSize, filteredSkills.length)} 条，共 {filteredSkills.length} 条
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
                className="p-2 rounded-lg border border-border hover:bg-zinc-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeftIcon className="w-4 h-4" />
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
                className="p-2 rounded-lg border border-border hover:bg-zinc-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRightIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      <InstallSkillModal
        isOpen={installOpen}
        onClose={() => setInstallOpen(false)}
        onInstalled={loadSkills}
      />
    </div>
  );
}