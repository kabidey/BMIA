import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getToken, setToken as storeToken, clearToken, decodeJWT, isTokenExpired } from '../api/client';

interface User {
  email: string;
  name: string;
  department: string;
  designation: string;
  superadmin: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (token: string, user: User) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Check existing session on mount
  useEffect(() => {
    (async () => {
      try {
        const stored = await getToken();
        if (stored && !isTokenExpired(stored)) {
          const payload = decodeJWT(stored);
          if (payload) {
            setTokenState(stored);
            setUser({
              email: payload.sub,
              name: payload.name || '',
              department: payload.department || '',
              designation: payload.designation || '',
              superadmin: payload.superadmin || false,
            });
          }
        } else if (stored) {
          await clearToken();
        }
      } catch (e) {
        console.error('Auth restore error:', e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Auto-check token expiry every 30s
  useEffect(() => {
    if (!token) return;
    const iv = setInterval(async () => {
      if (isTokenExpired(token)) {
        const payload = decodeJWT(token);
        if (payload?.superadmin) return; // Superadmin has long-lived token
        await clearToken();
        setTokenState(null);
        setUser(null);
      }
    }, 30000);
    return () => clearInterval(iv);
  }, [token]);

  const login = useCallback(async (newToken: string, newUser: User) => {
    await storeToken(newToken);
    setTokenState(newToken);
    setUser(newUser);
  }, []);

  const logout = useCallback(async () => {
    await clearToken();
    setTokenState(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
