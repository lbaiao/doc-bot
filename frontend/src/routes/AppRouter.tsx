import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';
import { useAuthStore } from '@/store/auth-store';

// Placeholder components (to be implemented)
import { LoginForm } from '@/features/auth/LoginForm';
import { SignupForm } from '@/features/auth/SignupForm';
import { AppLayout } from '@/components/layout/AppLayout';
import { HomeView } from '@/features/home/HomeView';
import { ChatView } from '@/features/chat/ChatView';

// Auth Guard
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
    const token = useAuthStore((state) => state.token);
    if (!token) {
        return <Navigate to="/login" replace />;
    }
    return <>{children}</>;
};

const router = createBrowserRouter([
    {
        path: '/login',
        element: <LoginForm />,
    },
    {
        path: '/signup',
        element: <SignupForm />,
    },
    {
        path: '/app',
        element: (
            <ProtectedRoute>
                <AppLayout />
            </ProtectedRoute>
        ),
        children: [
            {
                path: 'home',
                element: <HomeView />,
            },
            {
                path: 's/:sessionId',
                element: <ChatView />,
            },
            {
                index: true,
                element: <Navigate to="home" replace />,
            },
        ],
    },
    {
        path: '/',
        element: <Navigate to="/app/home" replace />,
    },
]);

export function AppRouter() {
    return <RouterProvider router={router} />;
}
