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
    <div className="h-full p-6 overflow-y-auto">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-heading font-semibold mb-6">设置</h2>

        {/* 当前用户信息 */}
        <div className="card p-6 mb-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary-light to-primary flex items-center justify-center text-white font-bold text-2xl">
              {user?.name?.charAt(0) || 'U'}
            </div>
            <div>
              <h3 className="text-lg font-semibold">{user?.name || '用户'}</h3>
              <p className="text-text-muted">
                {user?.isAdmin ? '管理员' : '普通用户'}
              </p>
            </div>
          </div>
        </div>

        {/* 设置分组 */}
        {settingsSections.map((section) => (
          <div key={section.title} className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <section.icon className="w-5 h-5 text-text-muted" />
              <h3 className="font-semibold text-text-primary">{section.title}</h3>
            </div>
            <div className="card divide-y divide-border">
              {section.items.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-4 hover:bg-bg-tertiary transition-colors"
                >
                  <span className="font-medium text-text-primary">{item.label}</span>

                  {item.type === 'input' && (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={item.value}
                        onChange={(e) => item.onChange(e.target.value)}
                        className="w-40 px-3 py-1.5 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                      />
                      <button
                        onClick={item.onSave}
                        className="px-3 py-1.5 bg-primary text-white text-sm rounded-md hover:bg-primary-dark transition-colors"
                      >
                        保存
                      </button>
                    </div>
                  )}

                  {item.type === 'theme' && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => item.onChange('light')}
                        className={`
                          px-3 py-1.5 text-sm rounded-md transition-colors
                          ${item.value === 'light'
                            ? 'bg-primary text-white'
                            : 'bg-bg-tertiary text-text-secondary hover:bg-gray-200'
                          }
                        `}
                      >
                        浅色
                      </button>
                      <button
                        onClick={() => item.onChange('dark')}
                        className={`
                          px-3 py-1.5 text-sm rounded-md transition-colors
                          ${item.value === 'dark'
                            ? 'bg-primary text-white'
                            : 'bg-bg-tertiary text-text-secondary hover:bg-gray-200'
                          }
                        `}
                      >
                        深色
                      </button>
                    </div>
                  )}

                  {item.type === 'toggle' && (
                    <button
                      className={`w-12 h-6 rounded-full transition-colors ${
                        item.default ? 'bg-primary' : 'bg-gray-300'
                      }`}
                      onClick={() => {}}
                    >
                      <div
                        className={`w-5 h-5 bg-white rounded-full shadow-sm transition-transform ${
                          item.default ? 'translate-x-6' : 'translate-x-0.5'
                        }`}
                      />
                    </button>
                  )}

                  {item.type === 'select' && (
                    <select className="px-3 py-1.5 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/50">
                      {item.options.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  )}

                  {item.type === 'danger' && (
                    <button className="px-3 py-1.5 text-sm text-red-500 hover:bg-red-50 rounded-md transition-colors">
                      {item.label}
                    </button>
                  )}

                  {!item.type && <ChevronRightIcon className="w-5 h-5 text-text-muted" />}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
