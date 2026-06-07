import { useAuth } from '@/context/AuthContext';

export function useCrmAccess() {
    const { hasModuleAccess } = useAuth();

    const canReadCrm = hasModuleAccess('crm', 'read');
    const canEditCrm = hasModuleAccess('crm', 'edit');
    const canManageCrm = hasModuleAccess('crm', 'manage');

    return {
        canReadCrm,
        canEditCrm,
        canManageCrm,
        canWriteCrm: canEditCrm || canManageCrm,
    };
}
