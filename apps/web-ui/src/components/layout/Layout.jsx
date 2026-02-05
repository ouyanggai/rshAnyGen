import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout() {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground selection:bg-primary/20">
      <Sidebar />
      <main className="flex-1 relative flex flex-col min-w-0 overflow-hidden bg-background/50">
        {/* Subtle top border for separation if needed, or just clean */}
        <div className="flex-1 h-full w-full relative">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
