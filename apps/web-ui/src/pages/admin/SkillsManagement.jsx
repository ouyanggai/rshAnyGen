import { useSkills } from '../../hooks/useSkills';
import { CubeIcon, CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';

// 技能分类配置
const skillCategories = {
  search: { label: '搜索', color: 'bg-blue-500' },
  knowledge: { label: '知识库', color: 'bg-green-500' },
  tools: { label: '工具', color: 'bg-purple-500' },
  chat: { label: '对话', color: 'bg-orange-500' },
};

export default function SkillsManagement() {
  const { skills, loading, error, toggleSkill, loadSkills } = useSkills();

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
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

  // 按分类分组
  const groupedSkills = skills.reduce((groups, skill) => {
    const category = skill.category || 'other';
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(skill);
    return groups;
  }, {});

  return (
    <div className="p-6 bg-bg-primary dark:bg-bg-dark min-h-full transition-colors duration-300">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-heading font-semibold text-text-primary dark:text-text-primary-dark">技能管理</h2>
          <div className="text-sm text-text-muted dark:text-text-secondary-dark">
            已启用 {skills.filter(s => s.enabled).length} / {skills.length} 个技能
          </div>
        </div>

        {/* 技能列表 */}
        <div className="space-y-6">
          {Object.entries(groupedSkills).map(([category, categorySkills]) => {
            const categoryInfo = skillCategories[category] || {
              label: category,
              color: 'bg-gray-500',
            };

            return (
              <div key={category}>
                <h3 className="text-sm font-semibold text-text-muted dark:text-text-secondary-dark uppercase tracking-wider mb-3">
                  {categoryInfo.label}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {categorySkills.map((skill) => (
                    <SkillCard
                      key={skill.id}
                      skill={skill}
                      onToggle={() => toggleSkill(skill.id)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {skills.length === 0 && (
          <div className="text-center py-12">
            <CubeIcon className="w-16 h-16 text-text-muted dark:text-text-muted/30 mx-auto mb-4" />
            <p className="text-text-muted dark:text-text-secondary-dark">暂无可用技能</p>
          </div>
        )}
      </div>
    </div>
  );
}

function SkillCard({ skill, onToggle }) {
  return (
    <div
      className={`
        card p-4 transition-all duration-200 bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark rounded-xl shadow-elevation-1
        ${skill.enabled ? 'border-primary/50 dark:border-primary/50 ring-1 ring-primary/20' : 'opacity-75 hover:opacity-100'}
      `}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h4 className="font-semibold text-text-primary dark:text-text-primary-dark">{skill.name}</h4>
            {skill.enabled && (
              <span className="px-2 py-0.5 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full">
                已启用
              </span>
            )}
          </div>
          <p className="text-sm text-text-secondary dark:text-text-secondary-dark">{skill.description}</p>
        </div>

        {/* 切换开关 */}
        <button
          onClick={onToggle}
          className={`
            relative w-12 h-6 rounded-full transition-colors duration-200 flex-shrink-0 ml-4
            ${skill.enabled ? 'bg-primary' : 'bg-gray-300 dark:bg-gray-600'}
          `}
        >
          <div
            className={`
              absolute top-1 w-4 h-4 bg-white rounded-full shadow-sm transition-transform duration-200
              ${skill.enabled ? 'left-7' : 'left-1'}
            `}
          >
            {skill.enabled ? (
              <CheckIcon className="w-3 h-3 text-primary mt-0.5 ml-0.5" />
            ) : (
              <XMarkIcon className="w-3 h-3 text-gray-400 mt-0.5 ml-0.5" />
            )}
          </div>
        </button>
      </div>
    </div>
  );
}
