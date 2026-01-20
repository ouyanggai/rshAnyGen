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

export default {
  getSkills,
  getSkill,
  toggleSkill,
};
