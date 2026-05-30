import { useState, useEffect, useCallback } from "react";

export interface NotificationItem {
  id: string;
  title: string;
  body: string;
  timestamp: string;
  severity: "LOW" | "FUTURE_ALERT" | "CRITICAL";
  read: boolean;
}

const LOCAL_STORAGE_KEY = "vitalguard_notifications";

export const useNotifications = (userId?: string) => {
  const [permission, setPermission] = useState<NotificationPermission>("default");
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  // Load notification permission and items from localStorage
  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      setPermission(Notification.permission);
    }
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try {
        setNotifications(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse notifications", e);
      }
    }
  }, []);

  // Request native HTML5 Desktop Push permissions from the browser
  const requestPermission = useCallback(async () => {
    if (typeof window !== "undefined" && "Notification" in window) {
      const state = await Notification.requestPermission();
      setPermission(state);
      
      // Attempt to register FCM token with backend once permission is granted (mock token for browser)
      if (state === "granted" && userId) {
        fetch(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/notifications/register-token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            token: "browser-push-token-" + Math.random().toString(36).substring(2, 10)
          })
        }).catch(err => console.log("Failed to register browser push token:", err));
      }
      return state;
    }
    return "default";
  }, [userId]);

  // Save changes to state & local storage
  const saveNotifications = (items: NotificationItem[]) => {
    setNotifications(items);
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(items));
  };

  // Add dynamic in-app notification & fire native browser desktop push
  const addNotification = useCallback((
    title: string,
    body: string,
    severity: "LOW" | "FUTURE_ALERT" | "CRITICAL"
  ) => {
    const newItem: NotificationItem = {
      id: Math.random().toString(36).substring(2, 9),
      title,
      body,
      timestamp: new Date().toISOString(),
      severity,
      read: false,
    };

    // Keep last 30 items
    setNotifications(prev => {
      const updated = [newItem, ...prev].slice(0, 30);
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });

    // Fire native HTML5 desktop notification
    if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "granted") {
      try {
        new Notification(title, {
          body,
          tag: "vitalguard-alert",
          silent: false
        });
      } catch (e) {
        console.error("Failed to trigger desktop notification", e);
      }
    }

    // Call backend API to record the push trigger
    if (userId) {
      fetch(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/notifications/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          title,
          body,
          severity
        })
      }).catch(() => {});
    }
  }, [userId]);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => {
      const updated = prev.map(n => ({ ...n, read: true }));
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
    localStorage.removeItem(LOCAL_STORAGE_KEY);
  }, []);

  return {
    permission,
    notifications,
    requestPermission,
    addNotification,
    markAllAsRead,
    clearAll
  };
};
