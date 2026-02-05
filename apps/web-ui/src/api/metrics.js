/**
 * 监控指标 API
 */
import api from './client';

// Token使用统计
export async function getTokenUsageStats(windowHours = 24) {
  const response = await api.get(`/v1/metrics/token-usage`, {
    params: { window_hours: windowHours }
  });
  return response.data;
}

// 延迟统计
export async function getLatencyStats(operation = null, windowHours = 24) {
  const params = { window_hours: windowHours };
  if (operation) params.operation = operation;

  const response = await api.get(`/v1/metrics/latency`, { params });
  return response.data;
}

// 上下文构建统计
export async function getContextStats(windowHours = 24) {
  const response = await api.get(`/v1/metrics/context-stats`, {
    params: { window_hours: windowHours }
  });
  return response.data;
}

// 记忆系统统计
export async function getMemoryStats(windowHours = 24) {
  const response = await api.get(`/v1/metrics/memory-stats`, {
    params: { window_hours: windowHours }
  });
  return response.data;
}

// 指标概览
export async function getMetricsOverview(windowHours = 24) {
  const response = await api.get(`/v1/metrics/overview`, {
    params: { window_hours: windowHours }
  });
  return response.data;
}

// 活跃会话统计
export async function getActiveSessions() {
  const response = await api.get('/v1/metrics/sessions/active');
  return response.data;
}

export default {
  getTokenUsageStats,
  getLatencyStats,
  getContextStats,
  getMemoryStats,
  getMetricsOverview,
  getActiveSessions
};
