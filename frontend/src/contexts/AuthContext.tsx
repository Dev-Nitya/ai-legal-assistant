import React, { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import type {
  User,
  AuthResponse,
  AuthRequest,
  RegisterRequest,
} from "../types";
import { useToast } from "../components/Toast";
import { cookieUtils } from "../utils/cookies";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: AuthRequest) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
  token: string | null;
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

const API_BASE_URL = "http://localhost:8000/api";

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const toast = useToast();

  const isAuthenticated = !!user && !!token;

  // Save auth data to both localStorage and cookies
  const saveAuthData = (authToken: string, userData: User) => {
    // Save to localStorage
    localStorage.setItem("auth_token", authToken);
    localStorage.setItem("user_data", JSON.stringify(userData));

    // Save to cookies as backup (7 days expiration)
    if (cookieUtils.isEnabled()) {
      cookieUtils.set("auth_token", authToken, 7);
      cookieUtils.set("user_data", JSON.stringify(userData), 7);
    }
  };

  // Remove auth data from both localStorage and cookies
  const clearAuthData = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_data");

    if (cookieUtils.isEnabled()) {
      cookieUtils.remove("auth_token");
      cookieUtils.remove("user_data");
    }
  };

  // Initialize auth state from localStorage or cookies
  useEffect(() => {
    let savedToken = localStorage.getItem("auth_token");
    let savedUser = localStorage.getItem("user_data");

    // Fallback to cookies if localStorage is empty
    if (!savedToken && cookieUtils.isEnabled()) {
      savedToken = cookieUtils.get("auth_token");
      savedUser = cookieUtils.get("user_data");
    }

    if (savedToken && savedUser) {
      try {
        const userData = JSON.parse(savedUser);
        setToken(savedToken);
        setUser(userData);

        // Sync data to both storage methods if missing
        if (localStorage.getItem("auth_token") !== savedToken) {
          saveAuthData(savedToken, userData);
        }
      } catch (error) {
        console.error("Error parsing saved user data:", error);
        clearAuthData();
        toast.error("Session data was corrupted and has been cleared");
      }
    }
    setIsLoading(false);
  }, [toast]);

  const login = async (credentials: AuthRequest): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const errorData = await response.json();
        const errorMessage = errorData.detail || "Login failed";
        toast.error(errorMessage);
        throw new Error(errorMessage);
      }

      const data: AuthResponse = await response.json();

      setToken(data.access_token);
      setUser(data.user);

      // Save auth data to both storage methods
      saveAuthData(data.access_token, data.user);

      toast.success(`Welcome back, ${data.user.full_name}!`);
    } catch (error) {
      console.error("Login error:", error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (userData: RegisterRequest): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        const errorMessage = errorData.detail || "Registration failed";
        toast.error(errorMessage);
        throw new Error(errorMessage);
      }

      const data: AuthResponse = await response.json();

      setToken(data.access_token);
      setUser(data.user);

      // Save auth data to both storage methods
      saveAuthData(data.access_token, data.user);

      toast.success(
        `Welcome to AI Legal Assistant, ${data.user.full_name}! Your account has been created successfully.`
      );
    } catch (error) {
      console.error("Registration error:", error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const refreshProfile = async (): Promise<void> => {
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/auth/profile`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        toast.error("Failed to refresh profile. Please log in again.");
        throw new Error("Failed to fetch profile");
      }

      const userData = await response.json();
      setUser(userData);

      // Update stored user data
      localStorage.setItem("user_data", JSON.stringify(userData));
      if (cookieUtils.isEnabled()) {
        cookieUtils.set("user_data", JSON.stringify(userData), 7);
      }

      toast.success("Profile updated successfully");
    } catch (error) {
      console.error("Profile refresh error:", error);
      // If profile fetch fails, user might need to re-authenticate
      logout();
    }
  };

  const logout = (): void => {
    setUser(null);
    setToken(null);
    clearAuthData();
    toast.info("You have been logged out successfully");
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    refreshProfile,
    token,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
