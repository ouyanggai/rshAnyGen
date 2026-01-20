import { useState, useEffect, useCallback } from 'react';
import { getSkills, toggleSkill as toggleSkillApi } from '../api/skills';

export function useSkills() {
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
        s.id === skillId ? { ...s, enabled: s.enabled } : s
      ));
      setError(err.message || '切换技能状态失败');
    }
  }, [skills]);

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
    toggleSkill,
    loadSkills,
    getSkillsByCategory,
  };
}
