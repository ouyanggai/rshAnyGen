import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/layout/Layout';
import ChatPage from './pages/ChatPage';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';
import AdminLayout from './pages/admin/AdminLayout';
import ModelConfig from './pages/admin/ModelConfig';
import SkillsManagement from './pages/admin/SkillsManagement';
import KnowledgeBase from './pages/admin/KnowledgeBase';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<ChatPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="settings" element={<SettingsPage />} />

        {/* 管理员路由 */}
        <Route path="admin" element={<AdminLayout />}>
          <Route path="models" element={<ModelConfig />} />
          <Route path="skills" element={<SkillsManagement />} />
          <Route path="knowledge" element={<KnowledgeBase />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
