import { useCallback, useMemo, useState } from 'react';
import { useSkills } from '../../hooks/useSkills';
import InstallSkillModal from '../../components/admin/InstallSkillModal';
import {
  CubeIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  ArrowPathIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';

const CATEGORY_META = {
  search: { label: '搜索', tone: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
  knowledge: { label: '知识库', tone: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' },
  tools: { label: '工具', tone: 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300' },
  chat: { label: '对话', tone: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' },
  text_processing: { label: '文本', tone: 'bg-slate-50 text-slate-700 dark:bg-white/5 dark:text-slate-200' },
};

const EXEC_TYPE_META = {
  function: { label: '函数', tone: 'bg-slate-50 text-slate-700 dark:bg-white/5 dark:text-slate-200' },
  mcp_tool: { label: 'MCP', tone: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300' },
  http_api: { label: 'HTTP', tone: 'bg-cyan-50 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300' },
  prompt: { label: 'Prompt', tone: 'bg-fuchsia-50 text-fuchsia-700 dark:bg-fuchsia-900/30 dark:text-fuchsia-300' },
};

function Pill({ children, tone }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${tone}`}>
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
      className={[
        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
        enabled ? 'bg-primary' : 'bg-gray-300 dark:bg-gray-600',
        disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer',
      ].join(' ')}
      title={enabled ? '已启用' : '已禁用'}
    >
      <span
        className={[
          'inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform',
          enabled ? 'translate-x-5' : 'translate-x-1',
        ].join(' ')}
      />
    </button>
  );
}

export default function SkillsManagement() {
  const { skills, loading, error, mutating, toggleSkill, deleteSkill, installSkill, installSkillFromSource, loadSkills } = useSkills();
  const [searchQuery, setSearchQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [installOpen, setInstallOpen] = useState(false);

  const enabledCount = useMemo(() => skills.filter(s => s.enabled).length, [skills]);

  const categoryOptions = useMemo(() => {
    const counts = new Map();
    for (const s of skills) {
      const key = s.category || 'other';
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([key, count]) => ({ key, count }));
  }, [skills]);

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

  const onInstall = useCallback(async (payload) => {
    await installSkill(payload);
  }, [installSkill]);

  const onDelete = useCallback(async (skill) => {
    const ok = window.confirm(`确定要卸载技能「${skill.name || skill.id}」吗？\n\n卸载后会移动到 storage/.deleted。`);
    if (!ok) return;
    try {
      await deleteSkill(skill.id);
    } catch {
      // 错误信息由 useSkills 的 error 状态统一呈现
    }
  }, [deleteSkill]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error && skills.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center max-w-md">
          <p className="text-text-muted mb-4">{error}</p>
          <button
            onClick={loadSkills}
            className="px-4 py-2 bg-primary text-white rounded-lg"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-transparent transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-2xl font-heading font-semibold text-text-primary dark:text-text-primary-dark">技能</h2>
            <p className="text-sm text-text-muted dark:text-text-secondary-dark mt-1">
              管理已安装的技能，并支持从 Git 仓库一键安装。
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadSkills}
              disabled={mutating}
              className="btn btn-secondary"
              title="刷新"
            >
              <ArrowPathIcon className="w-4 h-4" />
              刷新
            </button>
            <button
              onClick={() => setInstallOpen(true)}
              className="btn btn-primary"
            >
              <PlusIcon className="w-4 h-4" />
              安装技能
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-2xl border border-red-200/70 dark:border-red-900/40 bg-red-50/80 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        {/* Controls */}
        <div className="mt-6 card p-4">
          <div className="flex flex-col lg:flex-row lg:items-center gap-3">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="w-5 h-5 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索技能名称 / ID / 描述…"
                className="input pl-10"
              />
            </div>

            <div className="flex items-center justify-between lg:justify-start gap-3">
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="px-3 py-2.5 rounded-xl bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark text-sm text-text-primary dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="all">全部分类</option>
                {categoryOptions.map(({ key, count }) => (
                  <option key={key} value={key}>{(CATEGORY_META[key]?.label || key)}（{count}）</option>
                ))}
              </select>

              <div className="text-sm text-text-muted dark:text-text-secondary-dark">
                已启用 <span className="font-medium text-text-primary dark:text-text-primary-dark">{enabledCount}</span> / {skills.length}
              </div>
            </div>
          </div>
        </div>

        {/* List */}
        {skills.length === 0 ? (
          <div className="text-center py-16">
            <CubeIcon className="w-14 h-14 text-text-muted dark:text-text-muted/30 mx-auto mb-4" />
            <p className="text-text-muted dark:text-text-secondary-dark">暂无可用技能</p>
            <button
              onClick={() => setInstallOpen(true)}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-white hover:bg-primary-600 transition-colors text-sm"
            >
              <PlusIcon className="w-4 h-4" />
              立即安装
            </button>
          </div>
        ) : filteredSkills.length === 0 ? (
          <div className="text-center py-16">
            <CubeIcon className="w-14 h-14 text-text-muted dark:text-text-muted/30 mx-auto mb-4" />
            <p className="text-text-muted dark:text-text-secondary-dark">没有匹配的技能</p>
          </div>
        ) : (
          <div className="mt-6 columns-1 md:columns-2 xl:columns-3 2xl:columns-4 gap-5">
            {filteredSkills.map((skill) => (
              <div key={skill.id} className="mb-4 break-inside-avoid">
                <div
                  className={[
                    'group rounded-2xl border bg-white dark:bg-bg-card-dark border-border dark:border-border-dark transition-colors',
                    skill.enabled ? 'border-primary/35' : 'hover:border-primary/25',
                  ].join(' ')}
                >
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-semibold text-text-primary dark:text-text-primary-dark truncate">
                            {skill.name || skill.id}
                          </h3>
                          {skill.enabled ? (
                            <Pill tone="bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300">启用</Pill>
                          ) : (
                            <Pill tone="bg-gray-100 text-gray-700 dark:bg-white/5 dark:text-slate-200">禁用</Pill>
                          )}
                        </div>
                        <p className="mt-2 text-sm text-text-secondary dark:text-text-secondary-dark leading-relaxed">
                          {skill.description || '（无描述）'}
                        </p>

                        <div className="mt-3 flex flex-wrap gap-2">
                          <Pill tone={(CATEGORY_META[skill.category || 'other']?.tone) || 'bg-gray-100 text-gray-700 dark:bg-white/5 dark:text-slate-200'}>
                            {(CATEGORY_META[skill.category || 'other']?.label) || (skill.category || 'other')}
                          </Pill>
                          {skill.execution_type && (
                            <Pill tone={(EXEC_TYPE_META[skill.execution_type]?.tone) || 'bg-gray-100 text-gray-700 dark:bg-white/5 dark:text-slate-200'}>
                              {(EXEC_TYPE_META[skill.execution_type]?.label) || skill.execution_type}
                            </Pill>
                          )}
                          {skill.version && (
                            <Pill tone="bg-gray-100 text-gray-700 dark:bg-white/5 dark:text-slate-200">
                              v{skill.version}
                            </Pill>
                          )}
                        </div>
                      </div>

                      <div className="flex flex-col items-end gap-3 flex-shrink-0">
                        <Toggle
                          enabled={Boolean(skill.enabled)}
                          disabled={mutating}
                          onToggle={() => toggleSkill(skill.id)}
                        />
                        <button
                          type="button"
                          onClick={() => onDelete(skill)}
                          disabled={mutating}
                          className="inline-flex items-center justify-center p-2 rounded-xl text-text-muted hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                          title="卸载技能"
                        >
                          <TrashIcon className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="px-4 py-3 border-t border-border/60 dark:border-border-dark/60 flex items-center justify-between text-xs text-text-muted dark:text-text-secondary-dark">
                    <span className="font-mono truncate">{skill.id}</span>
                    <span className="opacity-80">用于工具增强调用</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <InstallSkillModal
        isOpen={installOpen}
        onClose={() => setInstallOpen(false)}
        onInstall={onInstall}
        onInstallFromSource={installSkillFromSource}
      />
    </div>
  );
}
