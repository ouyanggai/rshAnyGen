import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/layout/Layout';
import ChatPage from './pages/ChatPage';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';
import AuthDiagnostics from './pages/AuthDiagnostics';
import AdminLayout from './pages/admin/AdminLayout';
import ModelConfig from './pages/admin/ModelConfig';
import SkillsManagement from './pages/admin/SkillsManagement';
import KnowledgeBase from './pages/admin/KnowledgeBase';
import UserManagement from './pages/admin/UserManagement';
import AuthGate from './components/auth/AuthGate';
import AdminGate from './components/auth/AdminGate';

function App() {
  return (
    <Routes>
      <Route path="/diagnostics" element={<AuthDiagnostics />} />
      <Route path="/" element={<AuthGate><Layout /></AuthGate>}>
        <Route index element={<ChatPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="settings" element={<SettingsPage />} />

        {/* 管理员路由 */}
        <Route path="admin" element={<AdminGate><AdminLayout /></AdminGate>}>
          <Route path="models" element={<ModelConfig />} />
          <Route path="users" element={<UserManagement />} />
          <Route path="skills" element={<SkillsManagement />} />
          <Route path="knowledge" element={<KnowledgeBase />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
