import { useState, useEffect, createContext, useContext } from "react";
import type { ReactNode } from "react";
import type {
  User,
  AuthRequest,
  RegisterRequest,
  AuthResponse,
} from "../types";

const API_BASE_URL = "http://localhost:8000/api";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (credentials: AuthRequest) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
  logout: () => void;
  loading: boolean;
  isLoading: boolean; // Alias for loading for compatibility
  token: string | null;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for stored auth token
    const savedToken = localStorage.getItem("auth_token");
    const userData = localStorage.getItem("user_data");

    if (savedToken && userData) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(userData));
      } catch (error) {
        console.error("Error parsing stored user data:", error);
        localStorage.removeItem("auth_token");
        localStorage.removeItem("user_data");
      }
    }

    setLoading(false);
  }, []);

  const login = async (credentials: AuthRequest): Promise<void> => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Login failed");
      }

      const data: AuthResponse = await response.json();

      localStorage.setItem("auth_token", data.access_token);
      localStorage.setItem("user_data", JSON.stringify(data.user));
      setToken(data.access_token);
      setUser(data.user);
    } catch (error) {
      console.error("Login error:", error);
      throw error;
    }
  };

  const register = async (userData: RegisterRequest): Promise<void> => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "Registration failed");
      }

      const data: AuthResponse = await response.json();

      localStorage.setItem("auth_token", data.access_token);
      localStorage.setItem("user_data", JSON.stringify(data.user));
      setToken(data.access_token);
      setUser(data.user);
    } catch (error) {
      console.error("Registration error:", error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_data");
    setToken(null);
    setUser(null);
  };

  const refreshProfile = async (): Promise<void> => {
    if (!token) {
      throw new Error("No authentication token found");
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/profile`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to refresh profile");
      }

      const userData: User = await response.json();
      setUser(userData);
      localStorage.setItem("user_data", JSON.stringify(userData));
    } catch (error) {
      console.error("Profile refresh error:", error);
      throw error;
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    loading,
    isLoading: loading, // Alias for compatibility
    token,
    refreshProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
