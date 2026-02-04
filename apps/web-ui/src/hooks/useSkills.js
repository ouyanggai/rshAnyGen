import { useState, useEffect, useCallback } from 'react';
import {
  getSkills,
  toggleSkill as toggleSkillApi,
  installSkill as installSkillApi,
  installFromSource as installFromSourceApi,
  deleteSkill as deleteSkillApi,
} from '../api/skills';

export function useSkills() {
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mutating, setMutating] = useState(false);

  // 加载技能列表
  const loadSkills = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSkills();
      setSkills(data.skills || []);
    } catch (err) {
      setError(err.message || '加载技能列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // 切换技能状态
  const toggleSkill = useCallback(async (skillId) => {
    const skill = skills.find(s => s.id === skillId);
    if (!skill) return;

    // 乐观更新
    setSkills(prev => prev.map(s =>
      s.id === skillId ? { ...s, enabled: !s.enabled } : s
    ));

    try {
      const result = await toggleSkillApi(skillId, !skill.enabled);
      // 服务器返回的结果更新
      setSkills(prev => prev.map(s =>
        s.id === skillId ? result : s
      ));
    } catch (err) {
      // 失败时回滚
      setSkills(prev => prev.map(s =>
        s.id === skillId ? { ...s, enabled: skill.enabled } : s
      ));
      setError(err.message || '切换技能状态失败');
    }
  }, [skills]);

  const installSkill = useCallback(async (payload) => {
    setError(null);
    setMutating(true);
    try {
      const installed = await installSkillApi(payload);
      // 安装成功后刷新列表（避免本地猜测数据结构）
      await loadSkills();
      return installed;
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || '安装技能失败');
      throw err;
    } finally {
      setMutating(false);
    }
  }, [loadSkills]);

  const installSkillFromSource = useCallback(async (sourceId, slug, { overwrite = false } = {}) => {
    setError(null);
    setMutating(true);
    try {
      const installed = await installFromSourceApi(sourceId, { slug, overwrite: Boolean(overwrite) });
      await loadSkills();
      return installed;
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || '安装技能失败');
      throw err;
    } finally {
      setMutating(false);
    }
  }, [loadSkills]);

  const deleteSkill = useCallback(async (skillId) => {
    setError(null);
    setMutating(true);
    try {
      await deleteSkillApi(skillId);
      setSkills(prev => prev.filter(s => s.id !== skillId));
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || '卸载技能失败');
      throw err;
    } finally {
      setMutating(false);
    }
  }, []);

  // 获取已启用的技能
  const enabledSkills = skills.filter(s => s.enabled);

  // 按分类获取技能
  const getSkillsByCategory = useCallback((category) => {
    return skills.filter(s => s.category === category);
  }, [skills]);

  useEffect(() => {
    loadSkills();
  }, [loadSkills]);

  return {
    skills,
    enabledSkills,
    loading,
    error,
    mutating,
    toggleSkill,
    loadSkills,
    getSkillsByCategory,
    installSkill,
    installSkillFromSource,
    deleteSkill,
  };
}
