/**
 * Cookie utility functions for secure token storage
 */

export const cookieUtils = {
  // Set a cookie with optional expiration
  set: (name: string, value: string, days?: number): void => {
    let expires = "";
    if (days) {
      const date = new Date();
      date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
      expires = "; expires=" + date.toUTCString();
    }
    document.cookie = `${name}=${value || ""}${expires}; path=/; secure; samesite=strict`;
  },

  // Get a cookie value by name
  get: (name: string): string | null => {
    const nameEQ = name + "=";
    const ca = document.cookie.split(";");
    for (let i = 0; i < ca.length; i++) {
      let c = ca[i];
      while (c.charAt(0) === " ") c = c.substring(1, c.length);
      if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
  },

  // Remove a cookie
  remove: (name: string): void => {
    document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT; secure; samesite=strict`;
  },

  // Check if cookies are enabled
  isEnabled: (): boolean => {
    try {
      document.cookie = "cookietest=1; path=/";
      const enabled = document.cookie.indexOf("cookietest=") !== -1;
      document.cookie = "cookietest=1; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT";
      return enabled;
    } catch (e) {
      return false;
    }
  },
};
