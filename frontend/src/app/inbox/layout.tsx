import WorkspaceLayout from '@/components/WorkspaceLayout';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function InboxLayout({ children }: { children: React.ReactNode }) {
    return (
        <ProtectedRoute>
            <WorkspaceLayout sidebarTitle="Bandeja de Entrada">
                <div className="bg-[#f8f9fb] dark:bg-[#141517] min-h-screen">
                    {children}
                </div>
            </WorkspaceLayout>
        </ProtectedRoute>
    );
}
