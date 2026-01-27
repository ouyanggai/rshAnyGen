<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import axios from 'axios'

const isAuthenticated = ref(false)
const user = ref(null)
const loading = ref(true)
const error = ref(null)
const tokenExpiration = ref(null)
const timeLeft = ref('')
const userList = ref([])
const showUsers = ref(false)
const fetchingUsers = ref(false)
let timer = null

const api = axios.create({
  baseURL: '/api/auth'
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

const isTokenExpired = computed(() => timeLeft.value === 'Expired')

const formatTimeLeft = (ms) => {
  if (ms <= 0) return 'Expired'
  const seconds = Math.floor((ms / 1000) % 60)
  const minutes = Math.floor((ms / 1000 / 60) % 60)
  const hours = Math.floor((ms / 1000 / 60 / 60))
  return `${hours}h ${minutes}m ${seconds}s`
}

const updateTimer = () => {
  if (!tokenExpiration.value) return
  const now = Date.now()
  const diff = tokenExpiration.value - now
  timeLeft.value = formatTimeLeft(diff)
  if (diff <= 0 && timer) clearInterval(timer)
}

const fetchUsers = async () => {
  fetchingUsers.value = true
  try {
    const { data } = await api.get('/users')
    userList.value = data
    showUsers.value = true
  } catch (e) {
    console.error(e)
    alert("Failed to fetch users: " + e.message)
  } finally {
    fetchingUsers.value = false
  }
}

const login = async () => {
  try {
    const { data } = await api.get('/login-url')
    if (data.login_url) window.location.href = data.login_url
  } catch (e) {
    error.value = "无法获取登录地址: " + e.message
  }
}

const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('token_expiration')
  isAuthenticated.value = false
  user.value = null
  tokenExpiration.value = null
  if (timer) clearInterval(timer)
  window.location.href = '/'
}

const fetchUserInfo = async () => {
  try {
    loading.value = true
    const { data } = await api.get('/userinfo')
    user.value = data
  } catch (e) {
    if (e.response && e.response.status === 401) logout()
    error.value = "无法加载用户信息"
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  timer = setInterval(updateTimer, 1000)
  const urlParams = new URLSearchParams(window.location.search)
  const code = urlParams.get('code')

  if (code) {
    try {
      loading.value = true
      const { data } = await api.post('/token', { code })
      if (data.access_token) {
        localStorage.setItem('access_token', data.access_token)
        if (data.expires_in) {
          const exp = Date.now() + (data.expires_in * 1000)
          localStorage.setItem('token_expiration', exp)
          tokenExpiration.value = exp
          updateTimer()
        }
        window.history.replaceState({}, document.title, "/")
        isAuthenticated.value = true
        await fetchUserInfo()
      }
    } catch (e) {
      error.value = "登录失败: " + e.message
      loading.value = false
    }
  } else {
    const token = localStorage.getItem('access_token')
    const exp = localStorage.getItem('token_expiration')
    if (token) {
      if (exp) {
        tokenExpiration.value = parseInt(exp)
        updateTimer()
      }
      isAuthenticated.value = true
      await fetchUserInfo()
    } else {
      loading.value = false
    }
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="logo">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="logo-icon">
          <path fill-rule="evenodd" d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.25 9.75c0 5.942 4.064 10.933 9.563 12.348a.749.749 0 00.374 0c5.499-1.415 9.563-6.406 9.563-12.348 0-1.352-.272-2.636-.759-3.804a.75.75 0 00-.724-.516l-.143.001c-2.996 0-5.717-1.17-7.734-3.08zm3.094 8.016a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clip-rule="evenodd" />
        </svg>
        <span>润世华统一认证演示</span>
      </div>
      <button v-if="isAuthenticated" @click="logout" class="btn btn-text">退出登录</button>
    </header>

    <main class="main-content">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>正在连接认证中心...</p>
      </div>

      <div v-else-if="isAuthenticated && user" class="dashboard-grid">
        <!-- 用户信息卡片 -->
        <div class="card profile-card">
          <div class="card-header">
            <div class="avatar">
              <img v-if="user.avatar" :src="user.avatar" alt="Avatar" />
              <span v-else>{{ user.name?.charAt(0).toUpperCase() }}</span>
            </div>
            <div class="user-meta">
              <h2>{{ user.displayName || user.name }}</h2>
              <p>{{ user.email }}</p>
              <span class="role-badge" v-if="user.roles?.[0]">{{ user.roles[0].name }}</span>
            </div>
          </div>
          
          <div class="token-status" :class="{ expired: isTokenExpired }">
            <div class="status-icon">
              <svg v-if="!isTokenExpired" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm13.36-1.814a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clip-rule="evenodd" /></svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z" clip-rule="evenodd" /></svg>
            </div>
            <div class="status-info">
              <span class="label">会话状态</span>
              <span class="value">{{ isTokenExpired ? '已过期' : '活跃中' }}</span>
              <span class="timer">{{ timeLeft }}</span>
            </div>
          </div>

          <div class="json-preview">
            <h3>身份凭证详情</h3>
            <pre>{{ JSON.stringify(user, null, 2) }}</pre>
          </div>
        </div>

        <!-- SDK 功能演示卡片 -->
        <div class="card sdk-card">
          <div class="card-header-simple">
            <h3>组织架构管理</h3>
            <p>通过 Java SDK 实时获取</p>
          </div>
          
          <div class="sdk-actions">
            <button @click="fetchUsers" class="btn btn-primary" :disabled="fetchingUsers">
              <span v-if="fetchingUsers" class="spinner-sm"></span>
              同步组织用户列表
            </button>
          </div>

          <div v-if="showUsers" class="user-list-container">
            <div v-if="userList.length === 0" class="empty-state">暂无数据</div>
            <ul v-else class="user-list">
              <li v-for="u in userList" :key="u.id" class="user-item">
                <img :src="u.avatar" class="mini-avatar" v-if="u.avatar" />
                <div class="mini-avatar-placeholder" v-else>{{ u.name.charAt(0).toUpperCase() }}</div>
                <div class="user-info">
                  <span class="name">{{ u.displayName || u.name }}</span>
                  <span class="email">{{ u.email }}</span>
                </div>
                <span class="role-tag" v-if="u.roles?.[0]">{{ u.roles[0].name }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div v-else class="login-container">
        <div class="login-card">
          <div class="login-header">
            <div class="logo-large">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M12.516 2.17a.75.75 0 00-1.032 0 11.209 11.209 0 01-7.877 3.08.75.75 0 00-.722.515A12.74 12.74 0 002.25 9.75c0 5.942 4.064 10.933 9.563 12.348a.749.749 0 00.374 0c5.499-1.415 9.563-6.406 9.563-12.348 0-1.352-.272-2.636-.759-3.804a.75.75 0 00-.724-.516l-.143.001c-2.996 0-5.717-1.17-7.734-3.08zm3.094 8.016a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clip-rule="evenodd" /></svg>
            </div>
            <h1>欢迎访问</h1>
            <p>润世华统一认证演示系统</p>
          </div>
          <div v-if="error" class="error-banner">{{ error }}</div>
          <button @click="login" class="btn btn-primary btn-block">
            登录统一认证平台
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
  background-color: var(--background-color);
}

.app-header {
  background: var(--surface-color);
  border-bottom: 1px solid var(--border-color);
  padding: 0 2rem;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: var(--shadow-sm);
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 600;
  color: var(--text-primary);
  font-size: 1.1rem;
}

.logo-icon {
  width: 24px;
  height: 24px;
  color: var(--primary-color);
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  width: 100%;
}

/* Cards */
.card {
  background: var(--surface-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
}

@media (min-width: 768px) {
  .dashboard-grid {
    grid-template-columns: 350px 1fr;
    align-items: start;
  }
}

/* Profile Card */
.profile-card .card-header {
  padding: 2rem;
  text-align: center;
  border-bottom: 1px solid var(--border-color);
}

.avatar {
  width: 80px;
  height: 80px;
  background: var(--primary-color);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  margin: 0 auto 1rem;
  overflow: hidden;
  border: 4px solid var(--surface-color);
  box-shadow: var(--shadow-sm);
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-meta h2 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--text-primary);
}

.user-meta p {
  margin: 0.25rem 0 0.75rem;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.role-badge {
  background: #e0f2fe;
  color: #0369a1;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.token-status {
  padding: 1rem;
  margin: 1rem;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: 1rem;
}

.token-status.expired {
  background: #fef2f2;
  border-color: #fecaca;
}

.status-icon {
  width: 40px;
  height: 40px;
  background: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--success-color);
}

.expired .status-icon {
  color: var(--danger-color);
}

.status-icon svg {
  width: 24px;
  height: 24px;
}

.status-info {
  display: flex;
  flex-direction: column;
}

.status-info .label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.status-info .value {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-primary);
}

.status-info .timer {
  font-size: 0.75rem;
  font-family: monospace;
  color: var(--text-secondary);
}

.json-preview {
  padding: 1rem;
  background: #1e293b;
  margin: 0;
  overflow-x: auto;
}

.json-preview h3 {
  color: #94a3b8;
  font-size: 0.75rem;
  text-transform: uppercase;
  margin: 0 0 0.5rem;
  letter-spacing: 0.05em;
}

.json-preview pre {
  color: #e2e8f0;
  font-size: 0.75rem;
  margin: 0;
  font-family: 'Fira Code', monospace;
}

/* SDK Card */
.sdk-card {
  padding: 2rem;
  min-height: 400px;
}

.card-header-simple h3 {
  margin: 0;
  color: var(--text-primary);
}

.card-header-simple p {
  margin: 0.5rem 0 0;
  color: var(--text-secondary);
}

.sdk-actions {
  margin: 1.5rem 0;
}

.user-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.user-item {
  display: flex;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.2s;
}

.user-item:hover {
  background: #f8fafc;
}

.mini-avatar, .mini-avatar-placeholder {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  margin-right: 1rem;
  object-fit: cover;
}

.mini-avatar-placeholder {
  background: #cbd5e1;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.user-info .name {
  font-weight: 500;
  color: var(--text-primary);
}

.user-info .email {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.role-tag {
  background: #f1f5f9;
  color: #475569;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
}

/* Login Page */
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
}

.login-card {
  background: var(--surface-color);
  padding: 3rem;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.login-header {
  margin-bottom: 2rem;
}

.logo-large {
  width: 64px;
  height: 64px;
  background: #eff6ff;
  color: var(--primary-color);
  border-radius: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.5rem;
}

.logo-large svg {
  width: 32px;
  height: 32px;
}

.login-header h1 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--text-primary);
}

.login-header p {
  color: var(--text-secondary);
  margin-top: 0.5rem;
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem 1.5rem;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  font-size: 0.875rem;
  gap: 0.5rem;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background: var(--primary-hover);
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.btn-text {
  background: transparent;
  color: var(--text-secondary);
  padding: 0.5rem 1rem;
}

.btn-text:hover {
  background: #f1f5f9;
  color: var(--text-primary);
}

.btn-block {
  width: 100%;
}

.error-banner {
  background: #fef2f2;
  color: var(--danger-color);
  padding: 0.75rem;
  border-radius: var(--radius-md);
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state {
  text-align: center;
  padding: 4rem;
  color: var(--text-secondary);
}
</style>
