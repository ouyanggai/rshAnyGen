import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { toast } from 'sonner';
import {
  XMarkIcon,
  ArrowPathIcon,
  PlusIcon,
  TrashIcon,
  CodeBracketIcon,
  CommandLineIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

import {
  createSkillSource,
  deleteSkillSource,
  getSkillSources,
  getInstallJob,
  installFromSourceAsync,
  installSkillAsync,
  listAllSourceSkills,
  listSourceSkills,
  toggleSkillSource,
} from '../../api/skills';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const DEFAULT_FORM = {
  repo_url: '',
  skill: '',
  subdir: 'skills',
  ref: '',
  overwrite: false,
};

const DEFAULT_SOURCE_FORM = {
  repo_url: '',
  name: '',
  subdir: 'skills',
  ref: '',
};

function formatDuration(startIso, endIso) {
  const start = Date.parse(startIso || '');
  if (!Number.isFinite(start)) return '';
  const end = Number.isFinite(Date.parse(endIso || '')) ? Date.parse(endIso) : Date.now();
  const ms = Math.max(0, end - start);
  const totalSeconds = Math.floor(ms / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  return `${Math.floor(totalSeconds / 60)}m ${totalSeconds % 60}s`;
}

function inferInstallStage(job) {
  if (!job) return null;
  const status = job.status;
  const logs = job.logs || [];
  const has = (text) => logs.some((line) => line.includes(text));

  if (status === 'success') return { label: '安装完成', progress: 100 };
  if (status === 'error') return { label: '安装失败', progress: 100 };
  if (status === 'pending') return { label: '排队中', progress: 5 };

  let label = '准备中...';
  let progress = 10;
  
  if (has('git clone')) { label = '克隆仓库中...'; progress = 40; }
  if (has('校验技能目录') || has('解析 SKILL.md')) { label = '校验技能中...'; progress = 70; }
  if (has('复制文件到')) { label = '安装文件中...'; progress = 90; }
  if (has('安装完成')) { label = '完成中...'; progress = 100; }

  return { label, progress };
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
        enabled ? 'bg-green-500' : 'bg-zinc-300 dark:bg-zinc-600',
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

export default function InstallSkillModal({ isOpen, onClose, onInstalled }) {
  const [formData, setFormData] = useState(DEFAULT_FORM);
  const [tab, setTab] = useState('market');
  const [activeJob, setActiveJob] = useState(null);
  const [jobError, setJobError] = useState(null);
  const [pendingInstall, setPendingInstall] = useState(null);
  const [showJobLogs, setShowJobLogs] = useState(false); // Default hidden
  const logsEndRef = useRef(null);

  const [sources, setSources] = useState([]);
  const [sourcesLoading, setSourcesLoading] = useState(false);
  const [selectedSourceId, setSelectedSourceId] = useState('');
  const [scope, setScope] = useState('source'); // source | all

  const [sourceForm, setSourceForm] = useState(DEFAULT_SOURCE_FORM);
  const [addingSource, setAddingSource] = useState(false);

  const [remoteSkills, setRemoteSkills] = useState([]);
  const [remoteMeta, setRemoteMeta] = useState({ cached: false, source: null });
  const [remoteLoading, setRemoteLoading] = useState(false);
  const [remoteQuery, setRemoteQuery] = useState('');
  const [installingKey, setInstallingKey] = useState(null);
  
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const jobStage = useMemo(() => inferInstallStage(activeJob), [activeJob]);
  const latestLog = useMemo(() => {
    const logs = activeJob?.logs || [];
    return logs.length ? logs[logs.length - 1] : '';
  }, [activeJob?.logs]);
  const jobDuration = useMemo(() => formatDuration(activeJob?.created_at, activeJob?.updated_at), [activeJob?.created_at, activeJob?.updated_at]);

  // Reset state on open
  useEffect(() => {
    if (isOpen) {
      setFormData(DEFAULT_FORM);
      setActiveJob(null);
      setJobError(null);
      setPendingInstall(null);
      setShowJobLogs(false);
      setSourceForm(DEFAULT_SOURCE_FORM);
      setAddingSource(false);
    }
  }, [isOpen]);

  // Reset page on filter
  useEffect(() => {
    setPage(1);
  }, [remoteQuery, scope, selectedSourceId]);

  // Poll install job
  useEffect(() => {
    if (!isOpen || !activeJob?.id) return;
    const jobId = activeJob.id;
    let stopped = false;
    let timer = null;

    const poll = async () => {
      try {
        const data = await getInstallJob(jobId, { tail: 200 });
        if (stopped) return;
        setActiveJob(data);

        if (data?.status === 'success' || data?.status === 'error') {
          if (timer) clearInterval(timer);
          timer = null;
          setInstallingKey(null);

          if (data?.status === 'success') {
            toast.success('技能安装成功');
            if (pendingInstall?.type === 'source' && pendingInstall?.key) {
              setRemoteSkills((prev) => prev.map((s) => {
                const sourceId = s.source_id || selectedSourceId;
                const key = `${sourceId}:${s.slug}`;
                return key === pendingInstall.key ? { ...s, installed: true } : s;
              }));
            }
            onInstalled?.();
          } else {
            toast.error('安装失败');
            setJobError(data.error || 'Unknown error');
          }
        }
      } catch (e) {
        if (!stopped) setJobError(e.message);
      }
    };

    poll();
    timer = setInterval(poll, 1000);
    return () => {
      stopped = true;
      if (timer) clearInterval(timer);
    };
  }, [activeJob?.id, isOpen, onInstalled, pendingInstall, selectedSourceId]);

  // Auto scroll logs
  useEffect(() => {
    if (showJobLogs && activeJob?.logs?.length) {
      logsEndRef.current?.scrollIntoView({ block: 'end' });
    }
  }, [activeJob?.logs?.length, showJobLogs]);

  // Load Sources
  const loadSources = useCallback(async () => {
    setSourcesLoading(true);
    try {
      const data = await getSkillSources();
      const list = data?.sources || [];
      setSources(list);
      setSelectedSourceId(prev => {
        if (list.some(s => s.id === prev)) return prev;
        return list.find(s => s.enabled)?.id || list[0]?.id || '';
      });
    } catch (err) {
      toast.error('加载源失败');
    } finally {
      setSourcesLoading(false);
    }
  }, []);

  // Load Remote Skills
  const loadRemote = useCallback(async ({ refresh = false } = {}) => {
    setRemoteLoading(true);
    try {
      if (scope === 'all') {
        const data = await listAllSourceSkills({ refresh, enabledOnly: true });
        setRemoteSkills(data?.skills || []);
        setRemoteMeta({ cached: false, source: null });
      } else {
        if (!selectedSourceId) {
          setRemoteSkills([]);
          return;
        }
        const data = await listSourceSkills(selectedSourceId, { refresh });
        setRemoteSkills(data?.skills || []);
        setRemoteMeta({ cached: Boolean(data?.cached), source: data?.source || null });
      }
    } catch (err) {
      toast.error('加载技能失败');
      setRemoteSkills([]);
    } finally {
      setRemoteLoading(false);
    }
  }, [scope, selectedSourceId]);

  useEffect(() => {
    if (isOpen) loadSources();
  }, [isOpen, loadSources]);

  useEffect(() => {
    if (isOpen && tab === 'market') loadRemote({ refresh: false });
  }, [isOpen, tab, loadRemote]);

  const selectedSource = useMemo(() => sources.find((s) => s.id === selectedSourceId) || null, [sources, selectedSourceId]);

  const filteredRemoteSkills = useMemo(() => {
    const q = remoteQuery.trim().toLowerCase();
    const list = remoteSkills || [];
    if (!q) return list;
    return list.filter((s) => 
      `${s.title} ${s.id} ${s.slug} ${s.description} ${s.source_name}`.toLowerCase().includes(q)
    );
  }, [remoteSkills, remoteQuery]);

  const totalPages = Math.ceil(filteredRemoteSkills.length / pageSize);
  const paginatedRemoteSkills = filteredRemoteSkills.slice((page - 1) * pageSize, page * pageSize);

  const handleAddSource = async (e) => {
    e.preventDefault();
    setAddingSource(true);
    try {
      const payload = {
        repo_url: sourceForm.repo_url.trim(),
        name: sourceForm.name.trim() || null,
        subdir: (sourceForm.subdir || 'skills').trim(),
        ref: sourceForm.ref.trim() || null,
        enabled: true,
      };
      const created = await createSkillSource(payload);
      await loadSources();
      if (created?.id) {
        setSelectedSourceId(created.id);
        setScope('source');
      }
      setSourceForm(DEFAULT_SOURCE_FORM);
      toast.success('添加源成功');
    } catch (err) {
      toast.error(err.message || '添加源失败');
    } finally {
      setAddingSource(false);
    }
  };

  const handleToggleSource = async (sourceId, enabled) => {
    try {
      await toggleSkillSource(sourceId, enabled);
      await loadSources();
      toast.success(enabled ? '源已启用' : '源已禁用');
    } catch (err) {
      toast.error('更新源失败');
    }
  };

  const handleDeleteSource = async (sourceId, builtin) => {
    if (!window.confirm(builtin ? '禁用该内置源?' : '删除该源?')) return;
    try {
      await deleteSkillSource(sourceId);
      await loadSources();
      toast.success('源已删除');
    } catch (err) {
      toast.error('删除源失败');
    }
  };

  const handleInstallRemote = async (skill) => {
    if (activeJob?.status === 'pending' || activeJob?.status === 'running') return;
    const sourceId = skill.source_id || selectedSourceId;
    const slug = skill.slug;
    if (!sourceId || !slug) return;

    const key = `${sourceId}:${slug}`;
    setInstallingKey(key);
    setJobError(null);
    try {
      setPendingInstall({ type: 'source', key });
      const job = await installFromSourceAsync(sourceId, { slug, overwrite: Boolean(formData.overwrite) });
      setActiveJob(job);
      setShowJobLogs(true);
    } catch (err) {
      toast.error('安装启动失败');
      setInstallingKey(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (activeJob?.status === 'pending' || activeJob?.status === 'running') return;
    setJobError(null);
    try {
      const payload = {
        repo_url: formData.repo_url.trim(),
        skill: formData.skill.trim(),
        subdir: (formData.subdir || 'skills').trim(),
        ref: formData.ref.trim() || null,
        overwrite: Boolean(formData.overwrite),
      };
      setPendingInstall({ type: 'manual' });
      const job = await installSkillAsync(payload);
      setActiveJob(job);
      setShowJobLogs(true);
    } catch (err) {
      toast.error('安装启动失败');
    }
  };

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/20 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-5xl transform overflow-hidden rounded-2xl bg-white dark:bg-zinc-900 p-6 text-left align-middle shadow-xl border border-zinc-200 dark:border-zinc-800 transition-all">
                <div className="flex items-center justify-between mb-6">
                  <Dialog.Title as="h3" className="text-lg font-semibold leading-6 text-foreground">
                    安装技能
                  </Dialog.Title>
                  <button onClick={onClose} className="p-1 rounded-md text-muted-foreground hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                {/* Tabs */}
                <div className="flex gap-2 mb-6 border-b border-border pb-1">
                  <button
                    onClick={() => setTab('market')}
                    className={cn(
                      "px-4 py-2 text-sm font-medium rounded-t-lg transition-colors border-b-2",
                      tab === 'market' 
                        ? "border-primary text-primary bg-primary/5" 
                        : "border-transparent text-muted-foreground hover:text-foreground hover:bg-zinc-50"
                    )}
                  >
                    技能市场
                  </button>
                  <button
                    onClick={() => setTab('manual')}
                    className={cn(
                      "px-4 py-2 text-sm font-medium rounded-t-lg transition-colors border-b-2",
                      tab === 'manual' 
                        ? "border-primary text-primary bg-primary/5" 
                        : "border-transparent text-muted-foreground hover:text-foreground hover:bg-zinc-50"
                    )}
                  >
                    手动安装
                  </button>
                </div>

                {/* Active Job Status */}
                {activeJob && (
                  <div className="mb-6 rounded-xl border border-border bg-zinc-50/50 dark:bg-zinc-800/50 p-4">
                     <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                           {activeJob.status === 'running' || activeJob.status === 'pending' ? (
                             <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                           ) : activeJob.status === 'success' ? (
                             <div className="w-2 h-2 rounded-full bg-green-500" />
                           ) : (
                             <div className="w-2 h-2 rounded-full bg-red-500" />
                           )}
                           <span className="font-medium text-sm text-foreground">
                             {jobStage?.label || activeJob.status}
                           </span>
                           {jobDuration && <span className="text-xs text-muted-foreground ml-2">{jobDuration}</span>}
                        </div>
                        <button onClick={() => setShowJobLogs(!showJobLogs)} className="text-xs text-primary hover:underline">
                          {showJobLogs ? '隐藏日志' : '显示日志'}
                        </button>
                     </div>
                     
                     {/* Progress Bar */}
                     {(activeJob.status === 'running' || activeJob.status === 'pending') && (
                       <div className="h-1.5 w-full bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden mb-2">
                         <div 
                           className="h-full bg-primary transition-all duration-500 ease-out"
                           style={{ width: `${jobStage?.progress || 0}%` }}
                         />
                       </div>
                     )}

                     {/* Logs */}
                     {showJobLogs && (
                       <div className="mt-2 p-3 bg-zinc-900 rounded-lg max-h-48 overflow-auto font-mono text-xs text-zinc-300">
                         {activeJob.logs?.map((line, i) => (
                           <div key={i} className="whitespace-pre-wrap">{line}</div>
                         ))}
                         <div ref={logsEndRef} />
                       </div>
                     )}
                     
                     {/* Error */}
                     {(jobError || activeJob.error) && (
                       <div className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded">
                         {jobError || activeJob.error}
                       </div>
                     )}
                  </div>
                )}

                {/* Content */}
                {tab === 'market' ? (
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[500px]">
                    {/* Sidebar Sources */}
                    <div className="lg:col-span-4 flex flex-col h-full border-r border-border pr-4">
                       <div className="flex items-center justify-between mb-3">
                         <span className="text-sm font-semibold text-foreground">源</span>
                         <button onClick={loadSources} disabled={sourcesLoading} className="p-1 text-muted-foreground hover:text-foreground">
                           <ArrowPathIcon className={cn("w-4 h-4", sourcesLoading && "animate-spin")} />
                         </button>
                       </div>
                       
                       <div className="flex-1 overflow-y-auto space-y-2 pr-2">
                         {sources.map(s => (
                           <div 
                             key={s.id}
                             onClick={() => { setSelectedSourceId(s.id); setScope('source'); }}
                             className={cn(
                               "group flex flex-col p-3 rounded-xl border cursor-pointer transition-all",
                               selectedSourceId === s.id && scope === 'source'
                                 ? "bg-primary/5 border-primary/30 shadow-sm"
                                 : "bg-card border-border hover:bg-zinc-50 hover:border-zinc-300"
                             )}
                           >
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-sm">{s.name}</span>
                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <Toggle enabled={s.enabled} onToggle={(e) => { e.stopPropagation(); handleToggleSource(s.id, !s.enabled); }} />
                                  <button onClick={(e) => { e.stopPropagation(); handleDeleteSource(s.id, s.builtin); }} className="p-1 text-muted-foreground hover:text-red-500">
                                    <TrashIcon className="w-4 h-4" />
                                  </button>
                                </div>
                              </div>
                              <span className="text-xs text-muted-foreground mt-1 truncate">{s.repo_url}</span>
                           </div>
                         ))}
                         
                         {/* Add Source Form */}
                         <div className="mt-4 pt-4 border-t border-border">
                            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">添加新源</span>
                            <form onSubmit={handleAddSource} className="space-y-2">
                              <input 
                                placeholder="仓库地址 (e.g. vercel/skills)" 
                                className="w-full text-xs px-2 py-1.5 rounded border border-border bg-background"
                                value={sourceForm.repo_url}
                                onChange={e => setSourceForm({...sourceForm, repo_url: e.target.value})}
                              />
                              <input 
                                placeholder="名称 (可选)" 
                                className="w-full text-xs px-2 py-1.5 rounded border border-border bg-background"
                                value={sourceForm.name}
                                onChange={e => setSourceForm({...sourceForm, name: e.target.value})}
                              />
                              <button 
                                type="submit" 
                                disabled={addingSource}
                                className="w-full flex items-center justify-center gap-1 text-xs font-medium py-1.5 bg-zinc-900 text-white rounded hover:bg-zinc-800 disabled:opacity-50"
                              >
                                {addingSource ? '添加中...' : '添加源'}
                              </button>
                            </form>
                         </div>
                       </div>
                    </div>
                    
                    {/* Main Skills List */}
                    <div className="lg:col-span-8 flex flex-col h-full pl-2">
                       <div className="flex items-center gap-3 mb-4">
                          <div className="relative flex-1">
                            <input 
                              placeholder="搜索技能..." 
                              className="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-background text-sm focus:ring-1 focus:ring-primary outline-none"
                              value={remoteQuery}
                              onChange={e => setRemoteQuery(e.target.value)}
                            />
                            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                              <CommandLineIcon className="w-4 h-4" />
                            </div>
                          </div>
                          <div className="flex bg-zinc-100 p-1 rounded-lg">
                            <button onClick={() => setScope('source')} className={cn("px-3 py-1 text-xs font-medium rounded-md transition-all", scope === 'source' ? "bg-white shadow-sm" : "text-muted-foreground")}>当前源</button>
                            <button onClick={() => setScope('all')} className={cn("px-3 py-1 text-xs font-medium rounded-md transition-all", scope === 'all' ? "bg-white shadow-sm" : "text-muted-foreground")}>所有源</button>
                          </div>
                          <button onClick={() => loadRemote({ refresh: true })} className="p-2 border border-border rounded-lg hover:bg-zinc-50">
                            <ArrowPathIcon className={cn("w-4 h-4", remoteLoading && "animate-spin")} />
                          </button>
                       </div>

                       <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                          {remoteLoading ? (
                            <div className="flex justify-center py-10"><div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" /></div>
                          ) : filteredRemoteSkills.length === 0 ? (
                            <div className="text-center py-10 text-muted-foreground text-sm">未找到技能</div>
                          ) : (
                            paginatedRemoteSkills.map(s => {
                              const sourceId = s.source_id || selectedSourceId;
                              const key = `${sourceId}:${s.slug}`;
                              const isInstalling = installingKey === key;
                              
                              return (
                                <div key={key} className="flex items-start justify-between p-4 rounded-xl border border-border bg-card hover:border-primary/30 transition-colors">
                                   <div className="min-w-0 pr-4">
                                      <div className="flex items-center gap-2">
                                        <h4 className="font-semibold text-sm">{s.title || s.slug}</h4>
                                        {s.installed && <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-[10px] rounded-full font-medium">已安装</span>}
                                        {scope === 'all' && <span className="px-1.5 py-0.5 bg-zinc-100 text-zinc-600 text-[10px] rounded-full">{s.source_name}</span>}
                                      </div>
                                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{s.description || '暂无描述'}</p>
                                      <div className="mt-2 flex items-center gap-2 text-[10px] text-muted-foreground font-mono">
                                        <CodeBracketIcon className="w-3 h-3" />
                                        {s.slug}
                                      </div>
                                   </div>
                                   <button
                                     onClick={() => handleInstallRemote(s)}
                                     disabled={isInstalling || activeJob?.status === 'running' || (s.installed && !formData.overwrite)}
                                     className={cn(
                                       "px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap",
                                       s.installed 
                                         ? "bg-zinc-100 text-zinc-500"
                                         : "bg-zinc-900 text-white hover:bg-zinc-700 shadow-sm"
                                     )}
                                   >
                                     {isInstalling ? '安装中...' : (s.installed ? '已安装' : '安装')}
                                   </button>
                                </div>
                              );
                            })
                          )}
                       </div>

                       {/* Pagination Controls */}
                       {filteredRemoteSkills.length > 0 && (
                        <div className="mt-2 flex items-center justify-between border-t border-border pt-2">
                          <span className="text-xs text-muted-foreground">
                            {paginatedRemoteSkills.length > 0 ? (page - 1) * pageSize + 1 : 0} - {Math.min(page * pageSize, filteredRemoteSkills.length)} / {filteredRemoteSkills.length}
                          </span>
                          <div className="flex gap-1">
                            <button
                              disabled={page === 1}
                              onClick={() => setPage(p => p - 1)}
                              className="p-1 rounded-md border border-border hover:bg-zinc-50 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <ChevronLeftIcon className="w-4 h-4" />
                            </button>
                            <button
                              disabled={page >= totalPages}
                              onClick={() => setPage(p => p + 1)}
                              className="p-1 rounded-md border border-border hover:bg-zinc-50 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <ChevronRightIcon className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                       )}
                    </div>
                  </div>
                ) : (
                  <div className="max-w-lg mx-auto py-8">
                     {/* Manual Install Form */}
                     <form onSubmit={handleSubmit} className="space-y-4">
                       <div>
                         <label className="block text-sm font-medium mb-1">仓库地址 (Repository URL)</label>
                         <input 
                           required
                           className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20 outline-none transition-all"
                           placeholder="https://github.com/username/repo"
                           value={formData.repo_url}
                           onChange={e => setFormData({...formData, repo_url: e.target.value})}
                         />
                       </div>
                       <div className="grid grid-cols-2 gap-4">
                         <div>
                           <label className="block text-sm font-medium mb-1">技能名称 (Skill Name)</label>
                           <input 
                             required
                             className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20 outline-none transition-all"
                             placeholder="my-skill"
                             value={formData.skill}
                             onChange={e => setFormData({...formData, skill: e.target.value})}
                           />
                         </div>
                         <div>
                           <label className="block text-sm font-medium mb-1">子目录 (Subdirectory)</label>
                           <input 
                             className="w-full px-3 py-2 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20 outline-none transition-all"
                             placeholder="skills"
                             value={formData.subdir}
                             onChange={e => setFormData({...formData, subdir: e.target.value})}
                           />
                         </div>
                       </div>
                       <div className="pt-4">
                         <button 
                           type="submit" 
                           disabled={activeJob?.status === 'running'}
                           className="w-full py-2.5 bg-gradient-to-r from-primary to-secondary text-white rounded-xl font-medium shadow-lg shadow-primary/20 hover:shadow-xl hover:opacity-90 transition-all"
                         >
                           {activeJob?.status === 'running' ? '安装中...' : '安装技能'}
                         </button>
                       </div>
                     </form>
                  </div>
                )}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}