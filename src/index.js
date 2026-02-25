/**
 * Service Worker Registration
 * Registers Service Worker for offline capabilities and caching
 */

// Service Worker registration configuration
const SW_CONFIG = {
  scope: '/',
  updateViaCache: 'none',
  registrationOptions: {
    scope: '/',
    updateViaCache: 'none',
  },
};

// Service Worker registration class
export class ServiceWorkerManager {
  private registration: ServiceWorkerRegistration | null = null;
  private isSupported: boolean = false;
  private isRegistered: boolean = false;

  constructor() {
    this.isSupported = 'serviceWorker' in navigator;
  }

  /**
   * Register Service Worker
   */
  public async register(): Promise<ServiceWorkerRegistration | null> {
    if (!this.isSupported) {
      console.warn('Service Worker not supported in this browser');
      return null;
    }

    try {
      this.registration = await navigator.serviceWorker.register('/service-worker.js', SW_CONFIG.registrationOptions);
      
      console.log('Service Worker registered successfully:', this.registration);
      
      // Handle updates
      this.handleUpdates();
      
      // Handle messages
      this.handleMessages();
      
      this.isRegistered = true;
      return this.registration;
    } catch (error) {
      console.error('Service Worker registration failed:', error);
      return null;
    }
  }

  /**
   * Unregister Service Worker
   */
  public async unregister(): Promise<boolean> {
    if (!this.registration) {
      return false;
    }

    try {
      const result = await this.registration.unregister();
      console.log('Service Worker unregistered:', result);
      
      this.registration = null;
      this.isRegistered = false;
      return result;
    } catch (error) {
      console.error('Service Worker unregistration failed:', error);
      return false;
    }
  }

  /**
   * Check if Service Worker is registered
   */
  public isServiceWorkerRegistered(): boolean {
    return this.isRegistered && this.registration !== null;
  }

  /**
   * Get Service Worker registration
   */
  public getRegistration(): ServiceWorkerRegistration | null {
    return this.registration;
  }

  /**
   * Update Service Worker
   */
  public async update(): Promise<void> {
    if (!this.registration) {
      return;
    }

    try {
      await this.registration.update();
      console.log('Service Worker update triggered');
    } catch (error) {
      console.error('Service Worker update failed:', error);
    }
  }

  /**
   * Send message to Service Worker
   */
  public async sendMessage(type: string, data?: any): Promise<any> {
    if (!this.registration || !this.registration.active) {
      throw new Error('Service Worker not active');
    }

    return new Promise((resolve, reject) => {
      const messageChannel = new MessageChannel();
      
      messageChannel.port1.onmessage = (event) => {
        resolve(event.data);
      };

      this.registration!.active!.postMessage(
        { type, data },
        [messageChannel.port2]
      );

      // Timeout after 5 seconds
      setTimeout(() => {
        reject(new Error('Message timeout'));
      }, 5000);
    });
  }

  /**
   * Cache URLs
   */
  public async cacheUrls(urls: string[]): Promise<void> {
    try {
      await this.sendMessage('CACHE_URLS', { urls });
      console.log('URLs cached successfully');
    } catch (error) {
      console.error('Failed to cache URLs:', error);
    }
  }

  /**
   * Clear cache
   */
  public async clearCache(cacheName?: string): Promise<void> {
    try {
      await this.sendMessage('CLEAR_CACHE', { cacheName });
      console.log('Cache cleared successfully');
    } catch (error) {
      console.error('Failed to clear cache:', error);
    }
  }

  /**
   * Get cache statistics
   */
  public async getCacheStats(): Promise<any> {
    try {
      return await this.sendMessage('GET_CACHE_STATS');
    } catch (error) {
      console.error('Failed to get cache stats:', error);
      return null;
    }
  }

  /**
   * Handle Service Worker updates
   */
  private handleUpdates(): void {
    if (!this.registration) {
      return;
    }

    // Handle waiting Service Worker
    this.registration.addEventListener('updatefound', () => {
      const newWorker = this.registration!.installing;
      
      if (newWorker) {
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // New Service Worker is available
            this.notifyUpdateAvailable();
          }
        });
      }
    });

    // Handle controller change
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      console.log('Service Worker controller changed');
      window.location.reload();
    });
  }

  /**
   * Handle messages from Service Worker
   */
  private handleMessages(): void {
    navigator.serviceWorker.addEventListener('message', (event) => {
      const { type, data } = event.data;
      
      switch (type) {
        case 'CACHE_UPDATED':
          console.log('Cache updated:', data);
          break;
        
        case 'OFFLINE_MODE':
          console.log('Offline mode activated');
          this.notifyOfflineMode();
          break;
        
        case 'ONLINE_MODE':
          console.log('Online mode activated');
          this.notifyOnlineMode();
          break;
        
        case 'SYNC_COMPLETED':
          console.log('Background sync completed:', data);
          break;
        
        case 'SYNC_FAILED':
          console.error('Background sync failed:', data);
          break;
      }
    });
  }

  /**
   * Notify that Service Worker update is available
   */
  private notifyUpdateAvailable(): void {
    // Dispatch custom event
    const event = new CustomEvent('sw-update-available', {
      detail: { registration: this.registration }
    });
    window.dispatchEvent(event);
  }

  /**
   * Notify offline mode
   */
  private notifyOfflineMode(): void {
    const event = new CustomEvent('sw-offline-mode');
    window.dispatchEvent(event);
  }

  /**
   * Notify online mode
   */
  private notifyOnlineMode(): void {
    const event = new CustomEvent('sw-online-mode');
    window.dispatchEvent(event);
  }
}

// Singleton instance
let serviceWorkerManagerInstance: ServiceWorkerManager | null = null;

/**
 * Get Service Worker manager singleton instance
 */
export const getServiceWorkerManager = (): ServiceWorkerManager => {
  if (!serviceWorkerManagerInstance) {
    serviceWorkerManagerInstance = new ServiceWorkerManager();
  }
  return serviceWorkerManagerInstance;
};

/**
 * Initialize Service Worker
 */
export const initializeServiceWorker = async (): Promise<ServiceWorkerRegistration | null> => {
  const manager = getServiceWorkerManager();
  return await manager.register();
};

/**
 * Register Service Worker with error handling
 */
export const registerServiceWorker = async (): Promise<void> => {
  try {
    const registration = await initializeServiceWorker();
    
    if (registration) {
      console.log('Service Worker registered successfully');
      
      // Cache essential assets
      await manager.cacheUrls([
        '/',
        '/dashboard/',
        '/manifest.json',
        '/favicon.ico',
      ]);
    } else {
      console.warn('Service Worker registration failed');
    }
  } catch (error) {
    console.error('Service Worker registration error:', error);
  }
};

/**
 * Handle Service Worker update
 */
export const handleServiceWorkerUpdate = (): void => {
  window.addEventListener('sw-update-available', (event: any) => {
    const { registration } = event.detail;
    
    if (confirm('A new version of the app is available. Update now?')) {
      if (registration.waiting) {
        registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      }
    }
  });
};

/**
 * Handle offline/online mode
 */
export const handleOfflineMode = (): void => {
  window.addEventListener('sw-offline-mode', () => {
    // Show offline indicator
    const offlineIndicator = document.createElement('div');
    offlineIndicator.id = 'offline-indicator';
    offlineIndicator.textContent = 'You are offline';
    offlineIndicator.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      background: #f59e0b;
      color: white;
      text-align: center;
      padding: 8px;
      z-index: 9999;
    `;
    document.body.appendChild(offlineIndicator);
  });

  window.addEventListener('sw-online-mode', () => {
    // Hide offline indicator
    const offlineIndicator = document.getElementById('offline-indicator');
    if (offlineIndicator) {
      offlineIndicator.remove();
    }
  });
};

/**
 * Check if Service Worker is supported
 */
export const isServiceWorkerSupported = (): boolean => {
  return 'serviceWorker' in navigator;
};

/**
 * Check if Service Worker is registered
 */
export const isServiceWorkerRegistered = (): boolean => {
  const manager = getServiceWorkerManager();
  return manager.isServiceWorkerRegistered();
};

/**
 * Get Service Worker registration
 */
export const getServiceWorkerRegistration = (): ServiceWorkerRegistration | null => {
  const manager = getServiceWorkerManager();
  return manager.getRegistration();
};

/**
 * Update Service Worker
 */
export const updateServiceWorker = async (): Promise<void> => {
  const manager = getServiceWorkerManager();
  await manager.update();
};

/**
 * Clear Service Worker cache
 */
export const clearServiceWorkerCache = async (cacheName?: string): Promise<void> => {
  const manager = getServiceWorkerManager();
  await manager.clearCache(cacheName);
};

/**
 * Get Service Worker cache statistics
 */
export const getServiceWorkerCacheStats = async (): Promise<any> => {
  const manager = getServiceWorkerManager();
  return await manager.getCacheStats();
};

// Auto-initialize Service Worker when module is imported
if (typeof window !== 'undefined' && isServiceWorkerSupported()) {
  // Register Service Worker after DOM is loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      registerServiceWorker();
      handleServiceWorkerUpdate();
      handleOfflineMode();
    });
  } else {
    registerServiceWorker();
    handleServiceWorkerUpdate();
    handleOfflineMode();
  }
}

export default ServiceWorkerManager;
