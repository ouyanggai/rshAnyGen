import { useCallback, useEffect, useMemo, useState } from 'react';
import { Dialog } from '@headlessui/react';
import {
  XMarkIcon,
  ArrowPathIcon,
  PlusIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';

import {
  createSkillSource,
  deleteSkillSource,
  getSkillSources,
  listAllSourceSkills,
  listSourceSkills,
  toggleSkillSource,
} from '../../api/skills';

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

function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}

function Toggle({ enabled, disabled, onToggle }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      disabled={disabled}
      onClick={onToggle}
      className={[
        'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
        enabled ? 'bg-primary' : 'bg-gray-300 dark:bg-gray-600',
        disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer',
      ].join(' ')}
      title={enabled ? '已启用' : '已禁用'}
    >
      <span
        className={[
          'inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform',
          enabled ? 'translate-x-4' : 'translate-x-1',
        ].join(' ')}
      />
    </button>
  );
}

export default function InstallSkillModal({ isOpen, onClose, onInstall, onInstallFromSource }) {
  const [formData, setFormData] = useState(DEFAULT_FORM);
  const [tab, setTab] = useState('market');

  const [sources, setSources] = useState([]);
  const [sourcesLoading, setSourcesLoading] = useState(false);
  const [sourcesError, setSourcesError] = useState(null);
  const [selectedSourceId, setSelectedSourceId] = useState('');
  const [scope, setScope] = useState('source'); // source | all

  const [sourceForm, setSourceForm] = useState(DEFAULT_SOURCE_FORM);
  const [addingSource, setAddingSource] = useState(false);
  const [addSourceError, setAddSourceError] = useState(null);

  const [remoteSkills, setRemoteSkills] = useState([]);
  const [remoteMeta, setRemoteMeta] = useState({ cached: false, source: null });
  const [remoteLoading, setRemoteLoading] = useState(false);
  const [remoteError, setRemoteError] = useState(null);
  const [remoteQuery, setRemoteQuery] = useState('');
  const [installingKey, setInstallingKey] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    setFormData(DEFAULT_FORM);
    setError(null);
    setLoading(false);
    setTab('market');
    setScope('source');
    setRemoteQuery('');
    setRemoteSkills([]);
    setRemoteMeta({ cached: false, source: null });
    setRemoteError(null);
    setInstallingKey(null);
    setSourceForm(DEFAULT_SOURCE_FORM);
    setAddSourceError(null);
    setAddingSource(false);
  }, [isOpen]);

  const loadSources = useCallback(async () => {
    setSourcesLoading(true);
    setSourcesError(null);
    try {
      const data = await getSkillSources();
      const list = data?.sources || [];
      setSources(list);
      setSelectedSourceId((prev) => {
        const stillExists = list.some((s) => s.id === prev);
        if (stillExists) return prev;
        const firstEnabled = list.find((s) => s.enabled);
        return firstEnabled?.id || (list[0]?.id || '');
      });
    } catch (err) {
      setSourcesError(err?.response?.data?.detail || err.message || '加载源失败');
    } finally {
      setSourcesLoading(false);
    }
  }, []);

  const loadRemote = useCallback(async ({ refresh = false } = {}) => {
    setRemoteLoading(true);
    setRemoteError(null);
    try {
      if (scope === 'all') {
        const data = await listAllSourceSkills({ refresh, enabledOnly: true });
        setRemoteSkills(data?.skills || []);
        setRemoteMeta({ cached: false, source: null });
      } else {
        if (!selectedSourceId) {
          setRemoteSkills([]);
          setRemoteMeta({ cached: false, source: null });
          return;
        }
        const data = await listSourceSkills(selectedSourceId, { refresh });
        setRemoteSkills(data?.skills || []);
        setRemoteMeta({ cached: Boolean(data?.cached), source: data?.source || null });
      }
    } catch (err) {
      setRemoteError(err?.response?.data?.detail || err.message || '加载技能列表失败');
      setRemoteSkills([]);
      setRemoteMeta({ cached: false, source: null });
    } finally {
      setRemoteLoading(false);
    }
  }, [scope, selectedSourceId]);

  useEffect(() => {
    if (!isOpen) return;
    loadSources();
  }, [isOpen, loadSources]);

  useEffect(() => {
    if (!isOpen) return;
    if (tab !== 'market') return;
    loadRemote({ refresh: false });
  }, [isOpen, tab, loadRemote]);

  const selectedSource = useMemo(() => sources.find((s) => s.id === selectedSourceId) || null, [sources, selectedSourceId]);

  const filteredRemoteSkills = useMemo(() => {
    const q = remoteQuery.trim().toLowerCase();
    const list = remoteSkills || [];
    if (!q) return list;
    return list.filter((s) => {
      const hay = `${s.title || ''} ${s.id || ''} ${s.slug || ''} ${s.description || ''} ${s.source_name || ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [remoteSkills, remoteQuery]);

  const handleAddSource = useCallback(async (e) => {
    e.preventDefault();
    setAddingSource(true);
    setAddSourceError(null);
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
    } catch (err) {
      setAddSourceError(err?.response?.data?.detail || err.message || '添加源失败');
    } finally {
      setAddingSource(false);
    }
  }, [loadSources, sourceForm]);

  const handleToggleSource = useCallback(async (sourceId, enabled) => {
    try {
      await toggleSkillSource(sourceId, enabled);
      await loadSources();
    } catch (err) {
      setSourcesError(err?.response?.data?.detail || err.message || '更新源状态失败');
    }
  }, [loadSources]);

  const handleDeleteSource = useCallback(async (sourceId, builtin) => {
    const ok = window.confirm(builtin ? '确定要禁用这个默认源吗？' : '确定要删除这个自定义源吗？');
    if (!ok) return;
    try {
      await deleteSkillSource(sourceId);
      await loadSources();
    } catch (err) {
      setSourcesError(err?.response?.data?.detail || err.message || '删除源失败');
    }
  }, [loadSources]);

  const handleInstallRemote = useCallback(async (skill) => {
    if (!onInstallFromSource) return;
    const sourceId = skill.source_id || selectedSourceId;
    const slug = skill.slug;
    if (!sourceId || !slug) return;
    const key = `${sourceId}:${slug}`;
    setInstallingKey(key);
    try {
      await onInstallFromSource(sourceId, slug, { overwrite: Boolean(formData.overwrite) });
      setRemoteSkills((prev) => prev.map((s) => {
        const sid = s.source_id || selectedSourceId;
        const skey = `${sid}:${s.slug}`;
        return skey === key ? { ...s, installed: true } : s;
      }));
    } catch (err) {
      setRemoteError(err?.response?.data?.detail || err.message || '安装失败');
    } finally {
      setInstallingKey(null);
    }
  }, [formData.overwrite, onInstallFromSource, selectedSourceId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = {
        repo_url: formData.repo_url.trim(),
        skill: formData.skill.trim(),
        subdir: (formData.subdir || 'skills').trim(),
        ref: formData.ref.trim() || null,
        overwrite: Boolean(formData.overwrite),
      };
      await onInstall(payload);
      onClose();
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || '安装失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/40" aria-hidden="true" />

      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="mx-auto max-w-5xl w-full rounded-2xl bg-white dark:bg-bg-card-dark p-6 shadow-xl border border-border dark:border-border-dark">
          <div className="flex items-center justify-between mb-4">
            <Dialog.Title className="text-lg font-medium text-text-primary dark:text-text-primary-dark">
              安装技能
            </Dialog.Title>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-text-primary dark:hover:text-text-primary-dark transition-colors"
              aria-label="关闭"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>

          <div className="mb-5">
            <div className="inline-flex rounded-xl bg-bg-tertiary dark:bg-bg-input-dark p-1">
              <button
                type="button"
                onClick={() => setTab('market')}
                className={classNames(
                  'px-3 py-1.5 text-sm rounded-lg transition-colors',
                  tab === 'market'
                    ? 'bg-white dark:bg-bg-card-dark text-text-primary dark:text-text-primary-dark shadow-sm'
                    : 'text-text-muted hover:text-text-primary dark:hover:text-text-primary-dark'
                )}
              >
                从源安装
              </button>
              <button
                type="button"
                onClick={() => setTab('manual')}
                className={classNames(
                  'px-3 py-1.5 text-sm rounded-lg transition-colors',
                  tab === 'manual'
                    ? 'bg-white dark:bg-bg-card-dark text-text-primary dark:text-text-primary-dark shadow-sm'
                    : 'text-text-muted hover:text-text-primary dark:hover:text-text-primary-dark'
                )}
              >
                手动安装
              </button>
            </div>
          </div>

          {tab === 'market' ? (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
              {/* Sources */}
              <div className="lg:col-span-4 rounded-2xl border border-border dark:border-border-dark bg-white dark:bg-bg-card-dark p-4">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div className="text-sm font-medium text-text-primary dark:text-text-primary-dark">技能源</div>
                  <button
                    type="button"
                    onClick={loadSources}
                    disabled={sourcesLoading}
                    className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs border border-border dark:border-border-dark bg-white dark:bg-bg-card-dark hover:bg-bg-tertiary dark:hover:bg-white/5 transition-colors disabled:opacity-60"
                    title="刷新源列表"
                  >
                    <ArrowPathIcon className={classNames('w-4 h-4', sourcesLoading ? 'animate-spin' : '')} />
                    刷新
                  </button>
                </div>

                {sourcesError && (
                  <div className="text-xs text-red-600 dark:text-red-300 bg-red-50 dark:bg-red-900/20 p-2 rounded-lg mb-3">
                    {sourcesError}
                  </div>
                )}

                <div className="space-y-2 max-h-72 overflow-auto pr-1">
                  {sources.length === 0 ? (
                    <div className="text-sm text-text-muted dark:text-text-secondary-dark">暂无源</div>
                  ) : (
                    sources.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => {
                          setSelectedSourceId(s.id);
                          setScope('source');
                        }}
                        className={classNames(
                          'w-full text-left rounded-xl border px-3 py-2 transition-colors',
                          selectedSourceId === s.id && scope === 'source'
                            ? 'border-primary/40 bg-primary/5'
                            : 'border-border dark:border-border-dark bg-white dark:bg-bg-card-dark hover:bg-bg-tertiary dark:hover:bg-white/5'
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <div className="text-sm font-medium text-text-primary dark:text-text-primary-dark truncate">
                                {s.name}
                              </div>
                              {s.builtin && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-200">
                                  默认
                                </span>
                              )}
                            </div>
                            <div className="mt-1 text-[11px] text-text-muted dark:text-text-secondary-dark font-mono truncate">
                              {s.repo_url}
                            </div>
                          </div>

                          <div className="flex items-center gap-2 flex-shrink-0">
                            <Toggle
                              enabled={Boolean(s.enabled)}
                              disabled={sourcesLoading}
                              onToggle={(e) => {
                                e.stopPropagation();
                                handleToggleSource(s.id, !s.enabled);
                              }}
                            />
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteSource(s.id, Boolean(s.builtin));
                              }}
                              className="p-1.5 rounded-lg text-text-muted hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                              title={s.builtin ? '禁用默认源' : '删除源'}
                            >
                              <TrashIcon className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                        {s.description && (
                          <div className="mt-2 text-xs text-text-secondary dark:text-text-secondary-dark line-clamp-2">
                            {s.description}
                          </div>
                        )}
                      </button>
                    ))
                  )}
                </div>

                {/* Add source */}
                <div className="mt-4 pt-4 border-t border-border/60 dark:border-border-dark/60">
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-medium text-text-primary dark:text-text-primary-dark">添加源</div>
                    <button
                      type="button"
                      onClick={() => setScope('all')}
                      className={classNames(
                        'inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs border transition-colors',
                        scope === 'all'
                          ? 'border-primary/40 bg-primary/5 text-text-primary dark:text-text-primary-dark'
                          : 'border-border dark:border-border-dark bg-white dark:bg-bg-card-dark hover:bg-bg-tertiary dark:hover:bg-white/5 text-text-muted'
                      )}
                      title="聚合所有源的技能"
                    >
                      全部源
                    </button>
                  </div>

                  <form onSubmit={handleAddSource} className="mt-3 space-y-2">
                    <input
                      type="text"
                      value={sourceForm.repo_url}
                      onChange={(e) => setSourceForm({ ...sourceForm, repo_url: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark border border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-text-primary dark:text-text-primary-dark text-sm"
                      placeholder="Git 仓库，如 vercel-labs/skills"
                      required
                    />
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <input
                        type="text"
                        value={sourceForm.subdir}
                        onChange={(e) => setSourceForm({ ...sourceForm, subdir: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark border border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-text-primary dark:text-text-primary-dark text-sm"
                        placeholder="子目录（默认 skills）"
                      />
                      <input
                        type="text"
                        value={sourceForm.ref}
                        onChange={(e) => setSourceForm({ ...sourceForm, ref: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark border border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-text-primary dark:text-text-primary-dark text-sm"
                        placeholder="分支/Tag（可选）"
                      />
                    </div>
                    <input
                      type="text"
                      value={sourceForm.name}
                      onChange={(e) => setSourceForm({ ...sourceForm, name: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark border border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-text-primary dark:text-text-primary-dark text-sm"
                      placeholder="显示名称（可选）"
                    />

                    {addSourceError && (
                      <div className="text-xs text-red-600 dark:text-red-300 bg-red-50 dark:bg-red-900/20 p-2 rounded-lg">
                        {addSourceError}
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={addingSource}
                      className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-white bg-primary hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <PlusIcon className="w-4 h-4" />
                      {addingSource ? '添加中...' : '添加源'}
                    </button>
                  </form>
                </div>
              </div>

              {/* Remote skills */}
              <div className="lg:col-span-8 rounded-2xl border border-border dark:border-border-dark bg-white dark:bg-bg-card-dark p-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-text-primary dark:text-text-primary-dark truncate">
                      {scope === 'all' ? '全部源技能' : (selectedSource?.name || '请选择源')}
                    </div>
                    <div className="mt-1 text-xs text-text-muted dark:text-text-secondary-dark">
                      {scope === 'all'
                        ? '会聚合所有已启用的源（首次可能较慢，后续走缓存）'
                        : (remoteMeta?.cached ? '已使用缓存（可手动刷新）' : '首次拉取可能需要几秒')}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <label className="flex items-center gap-2 text-xs text-text-muted dark:text-text-secondary-dark select-none">
                      <input
                        type="checkbox"
                        checked={Boolean(formData.overwrite)}
                        onChange={(e) => setFormData({ ...formData, overwrite: e.target.checked })}
                        className="h-4 w-4 rounded border-border dark:border-border-dark text-primary focus:ring-primary"
                      />
                      覆盖同名
                    </label>
                    <button
                      type="button"
                      onClick={() => loadRemote({ refresh: true })}
                      disabled={remoteLoading || (scope === 'source' && !selectedSourceId)}
                      className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs border border-border dark:border-border-dark bg-white dark:bg-bg-card-dark hover:bg-bg-tertiary dark:hover:bg-white/5 transition-colors disabled:opacity-60"
                      title="刷新技能列表"
                    >
                      <ArrowPathIcon className={classNames('w-4 h-4', remoteLoading ? 'animate-spin' : '')} />
                      刷新
                    </button>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-2 mb-3">
                  <input
                    value={remoteQuery}
                    onChange={(e) => setRemoteQuery(e.target.value)}
                    placeholder="搜索（名称 / ID / slug / 描述 / source）"
                    className="flex-1 px-3 py-2 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark border border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-text-primary dark:text-text-primary-dark text-sm"
                  />
                  <div className="inline-flex rounded-lg border border-border dark:border-border-dark overflow-hidden">
                    <button
                      type="button"
                      onClick={() => setScope('source')}
                      className={classNames(
                        'px-3 py-2 text-sm transition-colors',
                        scope === 'source'
                          ? 'bg-primary text-white'
                          : 'bg-white dark:bg-bg-card-dark text-text-muted hover:text-text-primary dark:hover:text-text-primary-dark'
                      )}
                    >
                      单源
                    </button>
                    <button
                      type="button"
                      onClick={() => setScope('all')}
                      className={classNames(
                        'px-3 py-2 text-sm transition-colors',
                        scope === 'all'
                          ? 'bg-primary text-white'
                          : 'bg-white dark:bg-bg-card-dark text-text-muted hover:text-text-primary dark:hover:text-text-primary-dark'
                      )}
                    >
                      全部
                    </button>
                  </div>
                </div>

                {remoteError && (
                  <div className="text-sm text-red-600 dark:text-red-300 bg-red-50 dark:bg-red-900/20 p-2 rounded-lg mb-3">
                    {remoteError}
                  </div>
                )}

                <div className="max-h-[420px] overflow-auto pr-1 space-y-2">
                  {remoteLoading ? (
                    <div className="py-10 flex items-center justify-center">
                      <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                  ) : filteredRemoteSkills.length === 0 ? (
                    <div className="text-sm text-text-muted dark:text-text-secondary-dark py-10 text-center">
                      {scope === 'source' && !selectedSourceId ? '请先选择一个源' : '没有找到可用技能'}
                    </div>
                  ) : (
                    filteredRemoteSkills.map((s) => {
                      const sourceId = s.source_id || selectedSourceId;
                      const key = `${sourceId}:${s.slug}`;
                      const canInstall = Boolean(onInstallFromSource) && !s.installed && Boolean(sourceId) && Boolean(s.slug);
                      return (
                        <div
                          key={key}
                          className="rounded-xl border border-border dark:border-border-dark bg-white dark:bg-bg-card-dark p-3"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <div className="font-medium text-text-primary dark:text-text-primary-dark truncate">
                                  {s.title || s.id}
                                </div>
                                {s.installed && (
                                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300">
                                    已安装
                                  </span>
                                )}
                                {scope === 'all' && s.source_name && (
                                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-200">
                                    {s.source_name}
                                  </span>
                                )}
                              </div>
                              <div className="mt-1 text-xs text-text-muted dark:text-text-secondary-dark line-clamp-2">
                                {s.description || '（无描述）'}
                              </div>
                              <div className="mt-2 text-[11px] text-text-muted dark:text-text-secondary-dark font-mono truncate">
                                {s.id} · {s.slug}
                              </div>
                            </div>

                            <button
                              type="button"
                              onClick={() => handleInstallRemote(s)}
                              disabled={!canInstall || installingKey === key}
                              className={classNames(
                                'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                                canInstall
                                  ? 'bg-primary text-white hover:bg-primary-600'
                                  : 'bg-gray-100 text-gray-500 dark:bg-white/10 dark:text-slate-300 cursor-not-allowed',
                                installingKey === key ? 'opacity-80' : ''
                              )}
                              title={s.installed ? '已安装' : '安装到项目'}
                            >
                              {installingKey === key ? '安装中...' : (s.installed ? '已安装' : '安装')}
                            </button>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          ) : (
            <>
              <p className="text-sm text-text-muted dark:text-text-secondary-dark mb-5">
                支持输入 GitHub 仓库（如 <span className="font-mono">vercel-labs/skills</span> 或完整 URL），以及技能目录名（如 <span className="font-mono">find-skills</span>）。
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary-dark mb-1">
                    Git 仓库
                  </label>
                  <input
                    type="text"
                    value={formData.repo_url}
                    onChange={(e) => setFormData({ ...formData, repo_url: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark border border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-text-primary dark:text-text-primary-dark"
                    placeholder="vercel-labs/skills"
                    required
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary-dark mb-1">
                      Skill 名称
                    </label>
                    <input
                      type="text"
                      value={formData.skill}
                      onChange={(e) => setFormData({ ...formData, skill: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark border border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-text-primary dark:text-text-primary-dark"
                      placeholder="find-skills"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary-dark mb-1">
                      子目录
                    </label>
                    <input
                      type="text"
                      value={formData.subdir}
                      onChange={(e) => setFormData({ ...formData, subdir: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark border border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-text-primary dark:text-text-primary-dark"
                      placeholder="skills"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary dark:text-text-secondary-dark mb-1">
                    分支/Tag（可选）
                  </label>
                  <input
                    type="text"
                    value={formData.ref}
                    onChange={(e) => setFormData({ ...formData, ref: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-bg-tertiary dark:bg-bg-input-dark border border-transparent focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all text-text-primary dark:text-text-primary-dark"
                    placeholder="main"
                  />
                </div>

                <label className="flex items-center gap-2 text-sm text-text-secondary dark:text-text-secondary-dark select-none">
                  <input
                    type="checkbox"
                    checked={formData.overwrite}
                    onChange={(e) => setFormData({ ...formData, overwrite: e.target.checked })}
                    className="h-4 w-4 rounded border-border dark:border-border-dark text-primary focus:ring-primary"
                  />
                  覆盖同名技能（会先备份到 storage/.deleted）
                </label>

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
                    {loading ? '安装中...' : '安装'}
                  </button>
                </div>
              </form>
            </>
          )}
        </Dialog.Panel>
      </div>
    </Dialog>
  );
}
