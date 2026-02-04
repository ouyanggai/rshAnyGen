/**
 * 技能 API
 */
import api from './client';

// 获取所有技能列表
export const getSkills = async () => {
  const response = await api.get('/v1/skills');
  return response.data;
};

// 获取单个技能详情
export const getSkill = async (skillId) => {
  const response = await api.get(`/v1/skills/${skillId}`);
  return response.data;
};

// 切换技能启用状态
export const toggleSkill = async (skillId, enabled) => {
  const response = await api.post(`/v1/skills/${skillId}/toggle`, { enabled });
  return response.data;
};

// 安装技能（从 Git 仓库）
export const installSkill = async (payload) => {
  const response = await api.post('/v1/skills/install', payload);
  return response.data;
};

// 删除/卸载技能
export const deleteSkill = async (skillId) => {
  const response = await api.delete(`/v1/skills/${skillId}`);
  return response.data;
};

// === Skill Sources ===

export const getSkillSources = async () => {
  const response = await api.get('/v1/skill-sources');
  return response.data;
};

export const createSkillSource = async (payload) => {
  const response = await api.post('/v1/skill-sources', payload);
  return response.data;
};

export const toggleSkillSource = async (sourceId, enabled) => {
  const response = await api.post(`/v1/skill-sources/${sourceId}/toggle`, { enabled });
  return response.data;
};

export const deleteSkillSource = async (sourceId) => {
  const response = await api.delete(`/v1/skill-sources/${sourceId}`);
  return response.data;
};

export const listSourceSkills = async (sourceId, { refresh = false } = {}) => {
  const response = await api.get(`/v1/skill-sources/${sourceId}/skills`, {
    params: { refresh: refresh ? 1 : 0 },
  });
  return response.data;
};

export const listAllSourceSkills = async ({ refresh = false, enabledOnly = true } = {}) => {
  const response = await api.get('/v1/skill-sources/skills', {
    params: { refresh: refresh ? 1 : 0, enabled_only: enabledOnly ? 1 : 0 },
  });
  return response.data;
};

export const installFromSource = async (sourceId, payload) => {
  const response = await api.post(`/v1/skill-sources/${sourceId}/install`, payload);
  return response.data;
};

export default {
  getSkills,
  getSkill,
  toggleSkill,
  installSkill,
  deleteSkill,
  getSkillSources,
  createSkillSource,
  toggleSkillSource,
  deleteSkillSource,
  listSourceSkills,
  listAllSourceSkills,
  installFromSource,
};
