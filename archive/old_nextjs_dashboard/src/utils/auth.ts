/**
 * Authentication Utilities
 * Secure storage and retrieval of user-specific preferences and dashboard configurations
 * Integrates with AWS Cognito for identity management
 */

import { UserPreferences, WidgetConfig } from '@/types/dashboard';

// AWS Cognito types (simplified)
interface CognitoUser {
  username: string;
  attributes: Record<string, string>;
  signInUserSession: {
    accessToken: {
      jwtToken: string;
    };
    idToken: {
      jwtToken: string;
    };
    refreshToken: {
      token: string;
    };
  };
}

interface CognitoUserPool {
  getCurrentUser(): CognitoUser | null;
  signOut(): void;
}

// Storage types
type StorageType = 'localStorage' | 'sessionStorage' | 'memory' | 'cognito';

// Encryption utilities
class EncryptionUtils {
  private static readonly ALGORITHM = 'AES-GCM';
  private static readonly KEY_LENGTH = 256;
  private static readonly IV_LENGTH = 12;

  /**
   * Generate encryption key from user token
   */
  private static async generateKey(token: string): Promise<CryptoKey> {
    const encoder = new TextEncoder();
    const data = encoder.encode(token);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    return crypto.subtle.importKey(
      'raw',
      hashBuffer,
      { name: this.ALGORITHM },
      false,
      ['encrypt', 'decrypt']
    );
  }

  /**
   * Encrypt data
   */
  public static async encrypt(data: string, token: string): Promise<string> {
    try {
      const key = await this.generateKey(token);
      const iv = crypto.getRandomValues(new Uint8Array(this.IV_LENGTH));
      const encoder = new TextEncoder();
      const dataBuffer = encoder.encode(data);

      const encryptedBuffer = await crypto.subtle.encrypt(
        { name: this.ALGORITHM, iv },
        key,
        dataBuffer
      );

      // Combine IV and encrypted data
      const combined = new Uint8Array(iv.length + encryptedBuffer.byteLength);
      combined.set(iv);
      combined.set(new Uint8Array(encryptedBuffer), iv.length);

      // Convert to base64
      return btoa(String.fromCharCode(...combined));
    } catch (error) {
      console.error('Encryption failed:', error);
      throw new Error('Failed to encrypt data');
    }
  }

  /**
   * Decrypt data
   */
  public static async decrypt(encryptedData: string, token: string): Promise<string> {
    try {
      const key = await this.generateKey(token);
      
      // Convert from base64
      const combined = Uint8Array.from(atob(encryptedData), c => c.charCodeAt(0));
      
      // Extract IV and encrypted data
      const iv = combined.slice(0, this.IV_LENGTH);
      const encrypted = combined.slice(this.IV_LENGTH);

      const decryptedBuffer = await crypto.subtle.decrypt(
        { name: this.ALGORITHM, iv },
        key,
        encrypted
      );

      const decoder = new TextDecoder();
      return decoder.decode(decryptedBuffer);
    } catch (error) {
      console.error('Decryption failed:', error);
      throw new Error('Failed to decrypt data');
    }
  }
}

// Storage interface
interface SecureStorage {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
  clear(): Promise<void>;
}

// Local storage implementation
class LocalSecureStorage implements SecureStorage {
  private prefix: string;

  constructor(prefix: string = 'secureai_dashboard_') {
    this.prefix = prefix;
  }

  private getKey(key: string): string {
    return `${this.prefix}${key}`;
  }

  async getItem(key: string): Promise<string | null> {
    try {
      return localStorage.getItem(this.getKey(key));
    } catch (error) {
      console.error('Failed to get item from localStorage:', error);
      return null;
    }
  }

  async setItem(key: string, value: string): Promise<void> {
    try {
      localStorage.setItem(this.getKey(key), value);
    } catch (error) {
      console.error('Failed to set item in localStorage:', error);
      throw error;
    }
  }

  async removeItem(key: string): Promise<void> {
    try {
      localStorage.removeItem(this.getKey(key));
    } catch (error) {
      console.error('Failed to remove item from localStorage:', error);
    }
  }

  async clear(): Promise<void> {
    try {
      const keys = Object.keys(localStorage).filter(key => key.startsWith(this.prefix));
      keys.forEach(key => localStorage.removeItem(key));
    } catch (error) {
      console.error('Failed to clear localStorage:', error);
    }
  }
}

// Session storage implementation
class SessionSecureStorage implements SecureStorage {
  private prefix: string;

  constructor(prefix: string = 'secureai_dashboard_') {
    this.prefix = prefix;
  }

  private getKey(key: string): string {
    return `${this.prefix}${key}`;
  }

  async getItem(key: string): Promise<string | null> {
    try {
      return sessionStorage.getItem(this.getKey(key));
    } catch (error) {
      console.error('Failed to get item from sessionStorage:', error);
      return null;
    }
  }

  async setItem(key: string, value: string): Promise<void> {
    try {
      sessionStorage.setItem(this.getKey(key), value);
    } catch (error) {
      console.error('Failed to set item in sessionStorage:', error);
      throw error;
    }
  }

  async removeItem(key: string): Promise<void> {
    try {
      sessionStorage.removeItem(this.getKey(key));
    } catch (error) {
      console.error('Failed to remove item from sessionStorage:', error);
    }
  }

  async clear(): Promise<void> {
    try {
      const keys = Object.keys(sessionStorage).filter(key => key.startsWith(this.prefix));
      keys.forEach(key => sessionStorage.removeItem(key));
    } catch (error) {
      console.error('Failed to clear sessionStorage:', error);
    }
  }
}

// Memory storage implementation
class MemorySecureStorage implements SecureStorage {
  private storage = new Map<string, string>();

  async getItem(key: string): Promise<string | null> {
    return this.storage.get(key) || null;
  }

  async setItem(key: string, value: string): Promise<void> {
    this.storage.set(key, value);
  }

  async removeItem(key: string): Promise<void> {
    this.storage.delete(key);
  }

  async clear(): Promise<void> {
    this.storage.clear();
  }
}

// AWS Cognito storage implementation
class CognitoSecureStorage implements SecureStorage {
  private userPool: CognitoUserPool | null = null;

  constructor(userPool?: CognitoUserPool) {
    this.userPool = userPool || null;
  }

  private getCurrentUser(): CognitoUser | null {
    if (!this.userPool) {
      return null;
    }
    return this.userPool.getCurrentUser();
  }

  private async getUserAttribute(key: string): Promise<string | null> {
    const user = this.getCurrentUser();
    if (!user) {
      return null;
    }

    try {
      // In a real implementation, you would call Cognito's getUserAttributes method
      // For now, we'll simulate this with localStorage as a fallback
      const fallbackKey = `cognito_${user.username}_${key}`;
      return localStorage.getItem(fallbackKey);
    } catch (error) {
      console.error('Failed to get Cognito user attribute:', error);
      return null;
    }
  }

  private async setUserAttribute(key: string, value: string): Promise<void> {
    const user = this.getCurrentUser();
    if (!user) {
      throw new Error('No authenticated user');
    }

    try {
      // In a real implementation, you would call Cognito's updateUserAttributes method
      // For now, we'll simulate this with localStorage as a fallback
      const fallbackKey = `cognito_${user.username}_${key}`;
      localStorage.setItem(fallbackKey, value);
    } catch (error) {
      console.error('Failed to set Cognito user attribute:', error);
      throw error;
    }
  }

  async getItem(key: string): Promise<string | null> {
    return this.getUserAttribute(key);
  }

  async setItem(key: string, value: string): Promise<void> {
    await this.setUserAttribute(key, value);
  }

  async removeItem(key: string): Promise<void> {
    const user = this.getCurrentUser();
    if (!user) {
      return;
    }

    try {
      // In a real implementation, you would call Cognito's deleteUserAttribute method
      const fallbackKey = `cognito_${user.username}_${key}`;
      localStorage.removeItem(fallbackKey);
    } catch (error) {
      console.error('Failed to remove Cognito user attribute:', error);
    }
  }

  async clear(): Promise<void> {
    const user = this.getCurrentUser();
    if (!user) {
      return;
    }

    try {
      // Clear all user attributes
      const keys = Object.keys(localStorage).filter(key => 
        key.startsWith(`cognito_${user.username}_`)
      );
      keys.forEach(key => localStorage.removeItem(key));
    } catch (error) {
      console.error('Failed to clear Cognito user attributes:', error);
    }
  }
}

// Main auth utilities class
export class AuthUtils {
  private storage: SecureStorage;
  private storageType: StorageType;
  private userToken: string | null = null;
  private userId: string | null = null;

  constructor(storageType: StorageType = 'localStorage') {
    this.storageType = storageType;
    this.storage = this.createStorage(storageType);
  }

  private createStorage(type: StorageType): SecureStorage {
    switch (type) {
      case 'localStorage':
        return new LocalSecureStorage();
      case 'sessionStorage':
        return new SessionSecureStorage();
      case 'memory':
        return new MemorySecureStorage();
      case 'cognito':
        return new CognitoSecureStorage();
      default:
        return new LocalSecureStorage();
    }
  }

  /**
   * Set user authentication token
   */
  public setUserToken(token: string, userId: string): void {
    this.userToken = token;
    this.userId = userId;
  }

  /**
   * Clear user authentication token
   */
  public clearUserToken(): void {
    this.userToken = null;
    this.userId = null;
  }

  /**
   * Get current user ID
   */
  public getCurrentUserId(): string | null {
    return this.userId;
  }

  /**
   * Check if user is authenticated
   */
  public isAuthenticated(): boolean {
    return this.userToken !== null && this.userId !== null;
  }

  /**
   * Store user preferences securely
   */
  public async storeUserPreferences(preferences: UserPreferences): Promise<void> {
    if (!this.isAuthenticated()) {
      throw new Error('User not authenticated');
    }

    try {
      const data = JSON.stringify(preferences);
      const encryptedData = await EncryptionUtils.encrypt(data, this.userToken!);
      await this.storage.setItem(`preferences_${this.userId}`, encryptedData);
    } catch (error) {
      console.error('Failed to store user preferences:', error);
      throw new Error('Failed to store user preferences');
    }
  }

  /**
   * Retrieve user preferences securely
   */
  public async getUserPreferences(): Promise<UserPreferences | null> {
    if (!this.isAuthenticated()) {
      return null;
    }

    try {
      const encryptedData = await this.storage.getItem(`preferences_${this.userId}`);
      if (!encryptedData) {
        return null;
      }

      const decryptedData = await EncryptionUtils.decrypt(encryptedData, this.userToken!);
      return JSON.parse(decryptedData);
    } catch (error) {
      console.error('Failed to retrieve user preferences:', error);
      return null;
    }
  }

  /**
   * Store widget configurations securely
   */
  public async storeWidgetConfigs(widgets: WidgetConfig[]): Promise<void> {
    if (!this.isAuthenticated()) {
      throw new Error('User not authenticated');
    }

    try {
      const data = JSON.stringify(widgets);
      const encryptedData = await EncryptionUtils.encrypt(data, this.userToken!);
      await this.storage.setItem(`widgets_${this.userId}`, encryptedData);
    } catch (error) {
      console.error('Failed to store widget configurations:', error);
      throw new Error('Failed to store widget configurations');
    }
  }

  /**
   * Retrieve widget configurations securely
   */
  public async getWidgetConfigs(): Promise<WidgetConfig[] | null> {
    if (!this.isAuthenticated()) {
      return null;
    }

    try {
      const encryptedData = await this.storage.getItem(`widgets_${this.userId}`);
      if (!encryptedData) {
        return null;
      }

      const decryptedData = await EncryptionUtils.decrypt(encryptedData, this.userToken!);
      return JSON.parse(decryptedData);
    } catch (error) {
      console.error('Failed to retrieve widget configurations:', error);
      return null;
    }
  }

  /**
   * Store dashboard state securely
   */
  public async storeDashboardState(state: Record<string, any>): Promise<void> {
    if (!this.isAuthenticated()) {
      throw new Error('User not authenticated');
    }

    try {
      const data = JSON.stringify(state);
      const encryptedData = await EncryptionUtils.encrypt(data, this.userToken!);
      await this.storage.setItem(`dashboard_state_${this.userId}`, encryptedData);
    } catch (error) {
      console.error('Failed to store dashboard state:', error);
      throw new Error('Failed to store dashboard state');
    }
  }

  /**
   * Retrieve dashboard state securely
   */
  public async getDashboardState(): Promise<Record<string, any> | null> {
    if (!this.isAuthenticated()) {
      return null;
    }

    try {
      const encryptedData = await this.storage.getItem(`dashboard_state_${this.userId}`);
      if (!encryptedData) {
        return null;
      }

      const decryptedData = await EncryptionUtils.decrypt(encryptedData, this.userToken!);
      return JSON.parse(decryptedData);
    } catch (error) {
      console.error('Failed to retrieve dashboard state:', error);
      return null;
    }
  }

  /**
   * Clear all user data
   */
  public async clearUserData(): Promise<void> {
    if (!this.isAuthenticated()) {
      return;
    }

    try {
      await this.storage.removeItem(`preferences_${this.userId}`);
      await this.storage.removeItem(`widgets_${this.userId}`);
      await this.storage.removeItem(`dashboard_state_${this.userId}`);
    } catch (error) {
      console.error('Failed to clear user data:', error);
    }
  }

  /**
   * Clear all data
   */
  public async clearAllData(): Promise<void> {
    try {
      await this.storage.clear();
    } catch (error) {
      console.error('Failed to clear all data:', error);
    }
  }

  /**
   * Change storage type
   */
  public changeStorageType(newType: StorageType): void {
    this.storageType = newType;
    this.storage = this.createStorage(newType);
  }

  /**
   * Get storage statistics
   */
  public async getStorageStats(): Promise<{
    type: StorageType;
    authenticated: boolean;
    userId: string | null;
    dataKeys: string[];
  }> {
    const dataKeys: string[] = [];
    
    if (this.isAuthenticated()) {
      // Get all keys for current user
      const prefix = this.storageType === 'cognito' ? `cognito_${this.userId}_` : `secureai_dashboard_`;
      // This is a simplified implementation - in reality you'd need to enumerate storage
      dataKeys.push(`preferences_${this.userId}`, `widgets_${this.userId}`, `dashboard_state_${this.userId}`);
    }

    return {
      type: this.storageType,
      authenticated: this.isAuthenticated(),
      userId: this.userId,
      dataKeys,
    };
  }
}

// Singleton instance
let authUtilsInstance: AuthUtils | null = null;

/**
 * Get auth utils singleton instance
 */
export const getAuthUtils = (storageType?: StorageType): AuthUtils => {
  if (!authUtilsInstance) {
    authUtilsInstance = new AuthUtils(storageType);
  }
  return authUtilsInstance;
};

/**
 * Create new auth utils instance
 */
export const createAuthUtils = (storageType?: StorageType): AuthUtils => {
  return new AuthUtils(storageType);
};

/**
 * Destroy auth utils singleton
 */
export const destroyAuthUtils = (): void => {
  authUtilsInstance = null;
};

// Utility functions

/**
 * Initialize auth utils with AWS Cognito
 */
export const initializeWithCognito = (userPool: CognitoUserPool): AuthUtils => {
  const authUtils = getAuthUtils('cognito');
  // In a real implementation, you would set up the Cognito user pool
  return authUtils;
};

/**
 * Check if encryption is supported
 */
export const isEncryptionSupported = (): boolean => {
  return typeof crypto !== 'undefined' && 
         typeof crypto.subtle !== 'undefined' &&
         typeof crypto.getRandomValues !== 'undefined';
};

/**
 * Get available storage types
 */
export const getAvailableStorageTypes = (): StorageType[] => {
  const types: StorageType[] = ['memory'];
  
  if (typeof localStorage !== 'undefined') {
    types.push('localStorage');
  }
  
  if (typeof sessionStorage !== 'undefined') {
    types.push('sessionStorage');
  }
  
  if (typeof window !== 'undefined' && (window as any).AWS?.Cognito) {
    types.push('cognito');
  }
  
  return types;
};

export default AuthUtils;
