import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

export function AppLayout() {
    return (
        <div className="flex h-screen w-full overflow-hidden bg-background">
            <Sidebar className="hidden md:flex" />
            <div className="flex flex-1 flex-col overflow-hidden">
                <Topbar />
                <main className="flex-1 overflow-auto p-4 md:p-6">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
