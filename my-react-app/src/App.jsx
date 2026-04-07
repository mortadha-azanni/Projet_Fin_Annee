import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ChatPage from './chat/ChatPage';
import AdminPage from './admin/AdminPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </BrowserRouter>
  );
}
