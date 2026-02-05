import { useEffect, useState } from 'react';
import {
  ArrowPathIcon,
  BoltIcon,
  ChartBarIcon,
  Square3Stack3DIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';
import { getActiveSessions, getMetricsOverview } from '../../api/metrics';

export default function TokenMonitor() {
  const [loading, setLoading] = useState(true);
  const [windowHours, setWindowHours] = useState(24);
  const [metrics, setMetrics] = useState(null);
  const [activeSessions, setActiveSessions] = useState(null);

  useEffect(() => {
    loadData();
  }, [windowHours]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [overviewData, sessionsData] = await Promise.all([
        getMetricsOverview(windowHours),
        getActiveSessions(),
      ]);
      setMetrics(overviewData);
      setActiveSessions(sessionsData);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-';
    return new Intl.NumberFormat('zh-CN').format(Math.round(num));
  };

  const formatDuration = (ms) => {
    if (ms === null || ms === undefined) return '-';
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const MetricCard = ({ title, value, sub, icon: Icon, tone }) => (
    <div className="card p-6">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="text-sm text-text-muted dark:text-text-secondary-dark">{title}</div>
          <div className="mt-2 text-2xl font-heading font-semibold text-text-primary dark:text-text-primary-dark truncate">
            {value}
          </div>
          {sub && (
            <div className="mt-3 text-sm text-text-muted dark:text-text-secondary-dark">
              {sub}
            </div>
          )}
        </div>
        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${tone}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 bg-transparent min-h-full transition-colors duration-300">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-2xl font-heading font-semibold text-text-primary dark:text-text-primary-dark">Token 监控</h1>
            <p className="text-sm text-text-muted dark:text-text-secondary-dark mt-1">
              观察 Token 成本、响应延迟与活跃会话（运维视图）
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={windowHours}
              onChange={(e) => setWindowHours(Number(e.target.value))}
              className="px-3 py-2.5 rounded-xl bg-white dark:bg-bg-input-dark border border-border dark:border-border-dark text-sm text-text-primary dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary/40"
            >
              <option value={1}>最近 1 小时</option>
              <option value={6}>最近 6 小时</option>
              <option value={24}>最近 24 小时</option>
              <option value={72}>最近 3 天</option>
            </select>
            <button
              onClick={loadData}
              className="btn btn-primary rounded-xl"
            >
              <ArrowPathIcon className="w-4 h-4" />
              刷新
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          <MetricCard
            title="Token 使用量"
            value={
              metrics?.token_usage?.sum !== undefined
                ? formatNumber(metrics.token_usage.sum)
                : metrics?.token_usage?.count
                ? formatNumber(metrics.token_usage.count)
                : '0'
            }
            sub={`平均: ${metrics?.token_usage?.avg ? formatNumber(metrics.token_usage.avg) : '0'}`}
            icon={ChartBarIcon}
            tone="bg-primary/10 dark:bg-primary/20 text-primary"
          />
          <MetricCard
            title="响应延迟（P95）"
            value={metrics?.latency?.chat_response?.p95 ? formatDuration(metrics.latency.chat_response.p95) : '-'}
            sub={`平均: ${metrics?.latency?.chat_response?.avg ? formatDuration(metrics.latency.chat_response.avg) : '-'}`}
            icon={BoltIcon}
            tone="bg-secondary/10 dark:bg-secondary/20 text-secondary"
          />
          <MetricCard
            title="上下文构建（P95）"
            value={metrics?.latency?.context_build?.p95 ? formatDuration(metrics.latency.context_build.p95) : '-'}
            sub={`Token预算: ${metrics?.context?.token_budget?.avg ? formatNumber(metrics.context.token_budget.avg) : '0'}`}
            icon={Square3Stack3DIcon}
            tone="bg-slate-900/5 dark:bg-white/5 text-text-secondary dark:text-text-secondary-dark"
          />
          <MetricCard
            title="活跃会话"
            value={activeSessions?.active_sessions || 0}
            sub={`最近用户: ${activeSessions?.recent_users?.length || 0}`}
            icon={UserGroupIcon}
            tone="bg-amber-500/10 dark:bg-amber-500/15 text-amber-600 dark:text-amber-400"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-border/60 dark:border-border-dark/60">
              <h2 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">记忆系统</h2>
            </div>
            <div className="p-6 space-y-4 text-sm">
              <Row
                label="实体提取"
                value={`${metrics?.memory?.entity_extraction?.count ? formatNumber(metrics.memory.entity_extraction.count) : '0'} 次`}
              />
              <Row
                label="记忆检索"
                value={`${metrics?.memory?.retrieval?.count ? formatNumber(metrics.memory.retrieval.count) : '0'} 次`}
              />
              <Row
                label="去重操作"
                value={`${metrics?.memory?.deduplication?.count ? formatNumber(metrics.memory.deduplication.count) : '0'} 次`}
              />
            </div>
          </div>

          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-border/60 dark:border-border-dark/60">
              <h2 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">性能统计</h2>
            </div>
            <div className="p-6 space-y-4 text-sm">
              <Row
                label="最大延迟"
                value={metrics?.latency?.chat_response?.max ? formatDuration(metrics.latency.chat_response.max) : '-'}
              />
              <Row
                label="最小延迟"
                value={metrics?.latency?.chat_response?.min ? formatDuration(metrics.latency.chat_response.min) : '-'}
              />
              <Row
                label="Token 节省率"
                value={metrics?.context?.token_budget?.avg
                  ? `${((1 - metrics.context.token_budget.avg / 30000) * 100).toFixed(1)}%`
                  : '-'}
                valueClassName="text-green-600 dark:text-green-400"
              />
            </div>
          </div>
        </div>

        {activeSessions?.recent_users && activeSessions.recent_users.length > 0 && (
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-border/60 dark:border-border-dark/60 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">最近活跃用户</h2>
              <div className="text-sm text-text-muted dark:text-text-secondary-dark">
                {activeSessions.recent_users.length} 人
              </div>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
                {activeSessions.recent_users.map((user, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-3 p-3 rounded-xl bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark"
                  >
                    <div className="w-8 h-8 bg-gradient-to-br from-primary to-secondary rounded-full p-[1px] flex items-center justify-center">
                      <div className="w-full h-full rounded-full bg-white dark:bg-bg-card-dark flex items-center justify-center">
                        <span className="text-xs font-bold text-text-primary dark:text-text-primary-dark">
                          {String(user.user_id || '?').charAt(0).toUpperCase()}
                        </span>
                      </div>
                    </div>
                    <span className="text-sm text-text-primary dark:text-text-primary-dark truncate">
                      {user.user_id}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value, valueClassName }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-text-muted dark:text-text-secondary-dark">{label}</span>
      <span className={`font-medium text-text-primary dark:text-text-primary-dark ${valueClassName || ''}`}>
        {value}
      </span>
    </div>
  );
}
