import { useState } from 'react';
import { useApp } from '../context/AppContext';
import { useTheme } from '../hooks/useTheme';
import {
  UserIcon,
  PaintBrushIcon,
  BellIcon,
  ShieldCheckIcon,
  GlobeAltIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';

export default function SettingsPage() {
  const { user, updateUser } = useApp();
  const { theme, setTheme } = useTheme();
  const [userName, setUserName] = useState(user?.name || '');

  const handleSaveName = () => {
    if (userName.trim()) {
      updateUser({ name: userName.trim() });
    }
  };

  const settingsSections = [
    {
      title: '个人设置',
      icon: UserIcon,
      items: [
        {
          label: '用户名',
          type: 'input',
          value: userName,
          onChange: setUserName,
          onSave: handleSaveName,
        },
      ],
    },
    {
      title: '主题设置',
      icon: PaintBrushIcon,
      items: [
        {
          label: '外观模式',
          type: 'theme',
          value: theme,
          onChange: setTheme,
        },
      ],
    },
    {
      title: '通知设置',
      icon: BellIcon,
      items: [
        { label: '消息通知', type: 'toggle', default: true },
        { label: '声音提示', type: 'toggle', default: false },
      ],
    },
    {
      title: '语言与地区',
      icon: GlobeAltIcon,
      items: [
        {
          label: '语言',
          type: 'select',
          options: [
            { label: '简体中文', value: 'zh-CN' },
            { label: 'English', value: 'en' },
          ],
          default: 'zh-CN',
        },
      ],
    },
    {
      title: '隐私与安全',
      icon: ShieldCheckIcon,
      items: [
        { label: '清除聊天记录', type: 'danger' },
        { label: '退出登录', type: 'danger' },
      ],
    },
  ];

  return (
    <div className="h-full p-6 overflow-y-auto bg-bg-primary dark:bg-bg-dark transition-colors duration-300">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-heading font-semibold mb-6 text-text-primary dark:text-text-primary-dark">设置</h2>

        {/* 当前用户信息 */}
        <div className="card p-6 mb-6 bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark shadow-elevation-1 rounded-2xl">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary-light to-primary flex items-center justify-center text-white font-bold text-2xl shadow-glow-sm">
              {user?.name?.charAt(0) || 'U'}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-text-primary dark:text-text-primary-dark">{user?.name || '用户'}</h3>
              <p className="text-text-muted dark:text-text-secondary-dark">
                {user?.isAdmin ? '管理员' : '普通用户'}
              </p>
            </div>
          </div>
        </div>

        {/* 设置分组 */}
        {settingsSections.map((section) => (
          <div key={section.title} className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <section.icon className="w-5 h-5 text-text-muted dark:text-text-secondary-dark" />
              <h3 className="font-semibold text-text-primary dark:text-text-primary-dark">{section.title}</h3>
            </div>
            <div className="bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark rounded-2xl divide-y divide-border dark:divide-border-dark shadow-elevation-1 overflow-hidden">
              {section.items.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-4 hover:bg-bg-tertiary dark:hover:bg-white/5 transition-colors"
                >
                  <span className="font-medium text-text-primary dark:text-text-primary-dark">{item.label}</span>

                  {item.type === 'input' && (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={item.value}
                        onChange={(e) => item.onChange(e.target.value)}
                        className="w-40 px-3 py-1.5 bg-bg-tertiary dark:bg-bg-input-dark border border-border dark:border-border-dark rounded-lg text-sm text-text-primary dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary/50"
                      />
                      <button
                        onClick={item.onSave}
                        className="px-3 py-1.5 bg-primary text-white text-sm rounded-lg hover:bg-primary-dark transition-colors"
                      >
                        保存
                      </button>
                    </div>
                  )}

                  {item.type === 'theme' && (
                    <div className="flex items-center gap-2 bg-bg-tertiary dark:bg-bg-input-dark p-1 rounded-lg">
                      <button
                        onClick={() => item.onChange('light')}
                        className={`
                          px-3 py-1.5 text-sm rounded-md transition-all duration-200
                          ${item.value === 'light'
                            ? 'bg-white text-primary shadow-sm'
                            : 'text-text-secondary dark:text-text-secondary-dark hover:text-text-primary'
                          }
                        `}
                      >
                        浅色
                      </button>
                      <button
                        onClick={() => item.onChange('dark')}
                        className={`
                          px-3 py-1.5 text-sm rounded-md transition-all duration-200
                          ${item.value === 'dark'
                            ? 'bg-bg-card-dark text-primary shadow-sm'
                            : 'text-text-secondary dark:text-text-secondary-dark hover:text-text-primary'
                          }
                        `}
                      >
                        深色
                      </button>
                    </div>
                  )}

                  {item.type === 'toggle' && (
                    <button
                      className={`w-12 h-6 rounded-full transition-colors relative ${
                        item.default ? 'bg-primary' : 'bg-gray-300 dark:bg-gray-600'
                      }`}
                      onClick={() => {}}
                    >
                      <div
                        className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-sm transition-transform duration-200 ${
                          item.default ? 'translate-x-6' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  )}

                  {item.type === 'select' && (
                    <select className="px-3 py-1.5 bg-bg-tertiary dark:bg-bg-input-dark border border-border dark:border-border-dark rounded-lg text-sm text-text-primary dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary/50">
                      {item.options.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  )}

                  {item.type === 'danger' && (
                    <button className="px-3 py-1.5 text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors">
                      {item.label}
                    </button>
                  )}

                  {!item.type && <ChevronRightIcon className="w-5 h-5 text-text-muted dark:text-text-secondary-dark" />}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
