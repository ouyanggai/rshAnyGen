import { useEffect, useMemo, useState } from 'react';
import {
  MagnifyingGlassIcon,
  PlusIcon,
  ArrowPathIcon,
  KeyIcon,
  UserMinusIcon,
  UserPlusIcon,
} from '@heroicons/react/24/outline';
import {
  createUser,
  listRoles,
  listUsers,
  resetUserPassword,
  updateUser,
  updateUserRoles,
} from '../../api/adminUsers';

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  const [createOpen, setCreateOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(null);
  const [rolesOpen, setRolesOpen] = useState(null);

  const [error, setError] = useState(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [u, r] = await Promise.all([listUsers({ search }), listRoles()]);
      setUsers(u);
      setRoles(r);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const roleOptions = useMemo(() => {
    return (roles || [])
      .filter((r) => r?.name && !String(r.name).startsWith('default-'))
      .map((r) => r.name)
      .sort();
  }, [roles]);

  const toggleEnabled = async (user) => {
    try {
      await updateUser(user.id, { enabled: !user.enabled });
      await refresh();
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    }
  };

  return (
    <div className="p-6 bg-bg-primary dark:bg-bg-dark min-h-full transition-colors duration-300">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <h2 className="text-2xl font-heading font-semibold text-text-primary dark:text-text-primary-dark">
              用户管理
            </h2>
            <div className="text-sm text-text-muted dark:text-text-secondary-dark mt-1">
              基于 Keycloak 管理用户、重置密码与分配角色
            </div>
          </div>

          <button
            onClick={() => setCreateOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-white font-medium hover:bg-primary-600 transition-colors shadow-glow-sm"
          >
            <PlusIcon className="w-5 h-5" />
            新建用户
          </button>
        </div>

        <div className="flex items-center gap-3 mb-4">
          <div className="relative flex-1">
            <MagnifyingGlassIcon className="w-5 h-5 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索用户名/邮箱..."
              className="w-full pl-10 pr-3 py-2 rounded-xl bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark text-text-primary dark:text-text-primary-dark outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            />
          </div>
          <button
            onClick={refresh}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark text-text-secondary dark:text-text-secondary-dark hover:border-primary/50 transition-colors disabled:opacity-50"
          >
            <ArrowPathIcon className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200/50 dark:border-red-900/30">
            {error}
          </div>
        )}

        <div className="bg-white dark:bg-bg-card-dark rounded-2xl border border-border dark:border-border-dark shadow-elevation-1 overflow-hidden">
          <div className="px-6 py-4 border-b border-border dark:border-border-dark flex items-center justify-between">
            <div className="font-semibold text-text-primary dark:text-text-primary-dark">
              用户列表
            </div>
            <div className="text-sm text-text-muted dark:text-text-secondary-dark">
              {users.length} 人
            </div>
          </div>

          <div className="divide-y divide-border dark:divide-border-dark">
            {users.length === 0 ? (
              <div className="p-10 text-center text-text-muted dark:text-text-secondary-dark">
                暂无数据
              </div>
            ) : (
              users.map((u) => (
                <div key={u.id} className="px-6 py-4 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-3">
                      <div className="font-medium text-text-primary dark:text-text-primary-dark truncate">
                        {u.username || u.email || u.id}
                      </div>
                      <span
                        className={`text-xs font-semibold px-2 py-1 rounded-full ${
                          u.enabled
                            ? 'bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400'
                            : 'bg-gray-100 text-gray-600 dark:bg-white/5 dark:text-text-muted'
                        }`}
                      >
                        {u.enabled ? '启用' : '禁用'}
                      </span>
                    </div>
                    <div className="text-sm text-text-muted dark:text-text-secondary-dark truncate">
                      {u.email || '—'}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => toggleEnabled(u)}
                      className="p-2 rounded-xl border border-border dark:border-border-dark hover:border-primary/50 text-text-secondary dark:text-text-secondary-dark bg-white dark:bg-bg-card-dark transition-colors"
                      title={u.enabled ? '禁用用户' : '启用用户'}
                    >
                      {u.enabled ? <UserMinusIcon className="w-5 h-5" /> : <UserPlusIcon className="w-5 h-5" />}
                    </button>
                    <button
                      onClick={() => setResetOpen(u)}
                      className="p-2 rounded-xl border border-border dark:border-border-dark hover:border-primary/50 text-text-secondary dark:text-text-secondary-dark bg-white dark:bg-bg-card-dark transition-colors"
                      title="重置密码"
                    >
                      <KeyIcon className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => setRolesOpen(u)}
                      className="px-3 py-2 rounded-xl border border-border dark:border-border-dark hover:border-primary/50 text-sm font-medium text-text-secondary dark:text-text-secondary-dark bg-white dark:bg-bg-card-dark transition-colors"
                      title="分配角色"
                    >
                      分配角色
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <CreateUserModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={async () => {
          setCreateOpen(false);
          await refresh();
        }}
      />
      <ResetPasswordModal
        user={resetOpen}
        onClose={() => setResetOpen(null)}
        onDone={async () => {
          setResetOpen(null);
          await refresh();
        }}
      />
      <AssignRoleModal
        user={rolesOpen}
        roles={roleOptions}
        onClose={() => setRolesOpen(null)}
        onDone={async () => {
          setRolesOpen(null);
          await refresh();
        }}
      />
    </div>
  );
}

function ModalShell({ title, children, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md rounded-2xl bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark shadow-xl p-6">
        <div className="text-lg font-semibold text-text-primary dark:text-text-primary-dark mb-4">
          {title}
        </div>
        {children}
      </div>
    </div>
  );
}

function CreateUserModal({ open, onClose, onCreated }) {
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open) {
      setForm({ username: '', email: '', password: '' });
      setError(null);
      setLoading(false);
    }
  }, [open]);

  if (!open) return null;

  const submit = async () => {
    setLoading(true);
    setError(null);
    try {
      await createUser({
        username: form.username,
        email: form.email || null,
        password: form.password || null,
        enabled: true,
        temporary_password: true,
      });
      await onCreated();
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModalShell title="新建用户" onClose={onClose}>
      <div className="space-y-4">
        <FieldInput
          label="用户名"
          value={form.username}
          onChange={(v) => setForm({ ...form, username: v })}
          placeholder="username"
        />
        <FieldInput
          label="邮箱（可选）"
          value={form.email}
          onChange={(v) => setForm({ ...form, email: v })}
          placeholder="user@example.com"
        />
        <FieldInput
          label="初始密码（可选）"
          value={form.password}
          onChange={(v) => setForm({ ...form, password: v })}
          placeholder="留空则不设置"
          type="password"
        />

        {error && (
          <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded-xl">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-text-secondary dark:text-text-secondary-dark hover:bg-bg-tertiary dark:hover:bg-white/5 transition-colors"
          >
            取消
          </button>
          <button
            onClick={submit}
            disabled={loading || !form.username}
            className="px-4 py-2 rounded-xl bg-primary text-white font-medium hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '创建中...' : '创建'}
          </button>
        </div>
      </div>
    </ModalShell>
  );
}

function ResetPasswordModal({ user, onClose, onDone }) {
  const [password, setPassword] = useState('');
  const [temporary, setTemporary] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (user) {
      setPassword('');
      setTemporary(true);
      setLoading(false);
      setError(null);
    }
  }, [user]);

  if (!user) return null;

  const submit = async () => {
    setLoading(true);
    setError(null);
    try {
      await resetUserPassword(user.id, { password, temporary });
      await onDone();
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModalShell title="重置密码" onClose={onClose}>
      <div className="space-y-4">
        <div className="text-sm text-text-muted dark:text-text-secondary-dark">
          用户：{user.username || user.email || user.id}
        </div>
        <FieldInput label="新密码" value={password} onChange={setPassword} type="password" />
        <label className="flex items-center gap-2 text-sm text-text-secondary dark:text-text-secondary-dark">
          <input
            type="checkbox"
            checked={temporary}
            onChange={(e) => setTemporary(e.target.checked)}
          />
          下次登录需要修改密码
        </label>

        {error && (
          <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded-xl">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-text-secondary dark:text-text-secondary-dark hover:bg-bg-tertiary dark:hover:bg-white/5 transition-colors"
          >
            取消
          </button>
          <button
            onClick={submit}
            disabled={loading || password.length < 6}
            className="px-4 py-2 rounded-xl bg-primary text-white font-medium hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '提交中...' : '提交'}
          </button>
        </div>
      </div>
    </ModalShell>
  );
}

function AssignRoleModal({ user, roles, onClose, onDone }) {
  const [selected, setSelected] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (user) {
      setSelected('');
      setLoading(false);
      setError(null);
    }
  }, [user]);

  if (!user) return null;

  const submit = async () => {
    setLoading(true);
    setError(null);
    try {
      await updateUserRoles(user.id, { add: [selected], remove: [] });
      await onDone();
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModalShell title="分配角色" onClose={onClose}>
      <div className="space-y-4">
        <div className="text-sm text-text-muted dark:text-text-secondary-dark">
          用户：{user.username || user.email || user.id}
        </div>
        <div>
          <div className="text-sm font-medium text-text-secondary dark:text-text-secondary-dark mb-1">
            选择角色
          </div>
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="w-full px-3 py-2 rounded-xl bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark text-text-primary dark:text-text-primary-dark outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
          >
            <option value="">请选择</option>
            {roles.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded-xl">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-text-secondary dark:text-text-secondary-dark hover:bg-bg-tertiary dark:hover:bg-white/5 transition-colors"
          >
            取消
          </button>
          <button
            onClick={submit}
            disabled={loading || !selected}
            className="px-4 py-2 rounded-xl bg-primary text-white font-medium hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '提交中...' : '分配'}
          </button>
        </div>
      </div>
    </ModalShell>
  );
}

function FieldInput({ label, value, onChange, placeholder = '', type = 'text' }) {
  return (
    <div>
      <div className="text-sm font-medium text-text-secondary dark:text-text-secondary-dark mb-1">
        {label}
      </div>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        type={type}
        className="w-full px-3 py-2 rounded-xl bg-white dark:bg-bg-card-dark border border-border dark:border-border-dark text-text-primary dark:text-text-primary-dark outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
      />
    </div>
  );
}

