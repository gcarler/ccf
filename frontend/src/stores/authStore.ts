import { create } from 'zustand';

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_email_verified?: boolean;
  permissions?: Record<string, string>;
}

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;

  setAuth: (user: User | null, token: string | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
  hasModuleAccess: (module: string, minLevel?: string) => boolean;
  hasPermission: (perm: string) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  loading: true,
  isAuthenticated: false,

  setAuth: (user, token) =>
    set({ user, token, isAuthenticated: !!token, loading: false }),

  setLoading: (loading) => set({ loading }),

  logout: () => {
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('ccf_token');
      sessionStorage.removeItem('ccf_refresh_token');
    }
    set({ user: null, token: null, isAuthenticated: false, loading: false });
  },

  hasModuleAccess: (module: string, minLevel = 'read') => {
    const { user } = get();
    if (!user?.permissions) return false;
    if (user.role === 'admin') return true;
    const permKey = `${module}:${minLevel}`;
    if (user.permissions[permKey] === 'allow') return true;
    if (minLevel === 'read') {
      if (user.permissions[`${module}:edit`] === 'allow') return true;
      if (user.permissions[`${module}:manage`] === 'allow') return true;
      if (user.permissions[`${module}:study`] === 'allow') return true;
    }
    if (minLevel === 'edit') {
      if (user.permissions[`${module}:manage`] === 'allow') return true;
    }
    if (minLevel === 'study') {
      if (user.permissions[`${module}:edit`] === 'allow') return true;
      if (user.permissions[`${module}:manage`] === 'allow') return true;
    }
    return false;
  },

  hasPermission: (perm: string) => {
    const { user } = get();
    if (!user?.permissions) return false;
    if (user.role === 'admin' || user.role === 'administrador') return true;
    const val = user.permissions[perm];
    return val === 'allow' || (Array.isArray(val) && val.length > 0);
  },
}));
