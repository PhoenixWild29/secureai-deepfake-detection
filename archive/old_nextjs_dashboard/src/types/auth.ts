/**
 * Authentication and User Management Types
 * TypeScript interfaces for user authentication, roles, and permissions
 */

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  roles: UserRole[];
  permissions: Permission[];
  preferences: UserPreferences;
  lastLogin?: string;
  createdAt: string;
  updatedAt: string;
  isActive: boolean;
  isEmailVerified: boolean;
  profile?: UserProfile;
}

export interface UserProfile {
  firstName?: string;
  lastName?: string;
  phoneNumber?: string;
  organization?: string;
  department?: string;
  jobTitle?: string;
  timezone?: string;
  language?: string;
  notifications: NotificationPreferences;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  timezone: string;
  dateFormat: string;
  timeFormat: '12h' | '24h';
  notifications: NotificationPreferences;
  dashboard: DashboardPreferences;
  privacy: PrivacyPreferences;
}

export interface NotificationPreferences {
  email: boolean;
  push: boolean;
  sms: boolean;
  inApp: boolean;
  categories: {
    security: boolean;
    system: boolean;
    compliance: boolean;
    performance: boolean;
    maintenance: boolean;
  };
  frequency: 'immediate' | 'daily' | 'weekly';
}

export interface DashboardPreferences {
  defaultView: 'overview' | 'analytics' | 'notifications';
  layout: 'compact' | 'comfortable' | 'spacious';
  showSidebar: boolean;
  sidebarCollapsed: boolean;
  widgets: DashboardWidget[];
  refreshInterval: number;
}

export interface DashboardWidget {
  id: string;
  type: string;
  position: { x: number; y: number };
  size: { width: number; height: number };
  config: Record<string, any>;
}

export interface PrivacyPreferences {
  shareAnalytics: boolean;
  shareUsageData: boolean;
  allowCookies: boolean;
  dataRetention: number; // days
}

export enum UserRole {
  ADMIN = 'admin',
  SYSTEM_ADMIN = 'system_admin',
  SECURITY_OFFICER = 'security_officer',
  COMPLIANCE_MANAGER = 'compliance_manager',
  TECHNICAL_ADMINISTRATOR = 'technical_administrator',
  ANALYST = 'analyst',
  VIEWER = 'viewer',
  GUEST = 'guest'
}

export enum Permission {
  // Dashboard permissions
  DASHBOARD_VIEW = 'dashboard:view',
  DASHBOARD_ADMIN = 'dashboard:admin',
  
  // Analysis permissions
  ANALYSIS_CREATE = 'analysis:create',
  ANALYSIS_VIEW = 'analysis:view',
  ANALYSIS_UPDATE = 'analysis:update',
  ANALYSIS_DELETE = 'analysis:delete',
  ANALYSIS_EXPORT = 'analysis:export',
  
  // User management permissions
  USER_CREATE = 'user:create',
  USER_VIEW = 'user:view',
  USER_UPDATE = 'user:update',
  USER_DELETE = 'user:delete',
  USER_ROLE_ASSIGN = 'user:role_assign',
  
  // System permissions
  SYSTEM_VIEW = 'system:view',
  SYSTEM_CONFIG = 'system:config',
  SYSTEM_MAINTENANCE = 'system:maintenance',
  SYSTEM_BACKUP = 'system:backup',
  
  // Security permissions
  SECURITY_VIEW = 'security:view',
  SECURITY_ALERTS = 'security:alerts',
  SECURITY_INCIDENTS = 'security:incidents',
  SECURITY_AUDIT = 'security:audit',
  
  // Compliance permissions
  COMPLIANCE_VIEW = 'compliance:view',
  COMPLIANCE_REPORTS = 'compliance:reports',
  COMPLIANCE_AUDIT = 'compliance:audit',
  COMPLIANCE_EXPORT = 'compliance:export',
  
  // Analytics permissions
  ANALYTICS_VIEW = 'analytics:view',
  ANALYTICS_EXPORT = 'analytics:export',
  ANALYTICS_ADMIN = 'analytics:admin',
  
  // Notification permissions
  NOTIFICATIONS_VIEW = 'notifications:view',
  NOTIFICATIONS_CREATE = 'notifications:create',
  NOTIFICATIONS_ADMIN = 'notifications:admin'
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (userData: RegisterData) => Promise<void>;
  updateProfile: (profileData: Partial<UserProfile>) => Promise<void>;
  updatePreferences: (preferences: Partial<UserPreferences>) => Promise<void>;
  refreshToken: () => Promise<void>;
  hasPermission: (permission: Permission) => boolean;
  hasRole: (role: UserRole) => boolean;
  hasAnyRole: (roles: UserRole[]) => boolean;
  hasAllRoles: (roles: UserRole[]) => boolean;
}

export interface LoginData {
  email: string;
  password: string;
  rememberMe?: boolean;
  twoFactorCode?: string;
}

export interface RegisterData {
  email: string;
  password: string;
  name: string;
  organization?: string;
  department?: string;
  jobTitle?: string;
  phoneNumber?: string;
}

export interface AuthResponse {
  user: User;
  token: string;
  refreshToken: string;
  expiresAt: string;
}

export interface TokenPayload {
  sub: string; // user ID
  email: string;
  roles: UserRole[];
  permissions: Permission[];
  iat: number;
  exp: number;
  iss: string;
  aud: string;
}

export interface AuthError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

export interface TwoFactorSetup {
  qrCode: string;
  secret: string;
  backupCodes: string[];
}

export interface PasswordResetData {
  email: string;
}

export interface PasswordResetConfirmData {
  token: string;
  password: string;
  confirmPassword: string;
}

export interface EmailVerificationData {
  token: string;
}

export interface ChangePasswordData {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

// Role-based access control types
export interface RolePermissions {
  [UserRole.ADMIN]: Permission[];
  [UserRole.SYSTEM_ADMIN]: Permission[];
  [UserRole.SECURITY_OFFICER]: Permission[];
  [UserRole.COMPLIANCE_MANAGER]: Permission[];
  [UserRole.TECHNICAL_ADMINISTRATOR]: Permission[];
  [UserRole.ANALYST]: Permission[];
  [UserRole.VIEWER]: Permission[];
  [UserRole.GUEST]: Permission[];
}

export interface NavigationItem {
  id: string;
  label: string;
  href: string;
  icon: string;
  description?: string;
  permissions: Permission[];
  roles: UserRole[];
  children?: NavigationItem[];
  badge?: {
    text: string;
    variant: 'default' | 'destructive' | 'secondary' | 'success' | 'warning' | 'info';
  };
  isExternal?: boolean;
  isActive?: boolean;
}

export interface MenuSection {
  id: string;
  label: string;
  items: NavigationItem[];
  permissions: Permission[];
  roles: UserRole[];
  order: number;
}

// AWS Cognito integration types
export interface CognitoUser {
  username: string;
  attributes: {
    email: string;
    name?: string;
    phone_number?: string;
    email_verified?: string;
    'custom:roles'?: string;
    'custom:permissions'?: string;
    'custom:organization'?: string;
    'custom:department'?: string;
  };
  groups?: string[];
}

export interface CognitoAuthConfig {
  region: string;
  userPoolId: string;
  userPoolWebClientId: string;
  identityPoolId?: string;
  oauth?: {
    domain: string;
    scope: string[];
    redirectSignIn: string;
    redirectSignOut: string;
    responseType: 'code' | 'token';
  };
}

export interface CognitoAuthError {
  code: string;
  name: string;
  message: string;
}

// Session management types
export interface SessionData {
  user: User;
  token: string;
  refreshToken: string;
  expiresAt: number;
  lastActivity: number;
  deviceInfo: DeviceInfo;
}

export interface DeviceInfo {
  userAgent: string;
  platform: string;
  browser: string;
  version: string;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
}

// API response types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  meta?: {
    page?: number;
    limit?: number;
    total?: number;
    totalPages?: number;
  };
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  meta: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

// Form validation types
export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

export interface FormState<T> {
  data: T;
  errors: ValidationError[];
  isSubmitting: boolean;
  isDirty: boolean;
  isValid: boolean;
}

// Hook return types
export interface UseAuthReturn extends AuthContextType {
  error: AuthError | null;
  clearError: () => void;
}

export interface UsePermissionsReturn {
  hasPermission: (permission: Permission) => boolean;
  hasRole: (role: UserRole) => boolean;
  hasAnyRole: (roles: UserRole[]) => boolean;
  hasAllRoles: (roles: UserRole[]) => boolean;
  userPermissions: Permission[];
  userRoles: UserRole[];
}

export interface UseNavigationReturn {
  navigationItems: NavigationItem[];
  menuSections: MenuSection[];
  activeItem: NavigationItem | null;
  setActiveItem: (item: NavigationItem | null) => void;
  isItemVisible: (item: NavigationItem) => boolean;
}

// Utility types
export type UserRoleKey = keyof typeof UserRole;
export type PermissionKey = keyof typeof Permission;

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type RequireAtLeastOne<T, Keys extends keyof T = keyof T> = Pick<T, Exclude<keyof T, Keys>> &
  {
    [K in Keys]-?: Required<Pick<T, K>> & Partial<Pick<T, Exclude<Keys, K>>>;
  }[Keys];

// Event types for authentication
export interface AuthEvent {
  type: 'login' | 'logout' | 'register' | 'profile_update' | 'password_change';
  user?: User;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface AuthEventListener {
  (event: AuthEvent): void;
}

// Constants
export const DEFAULT_USER_PREFERENCES: UserPreferences = {
  theme: 'system',
  language: 'en',
  timezone: 'UTC',
  dateFormat: 'YYYY-MM-DD',
  timeFormat: '24h',
  notifications: {
    email: true,
    push: true,
    sms: false,
    inApp: true,
    categories: {
      security: true,
      system: true,
      compliance: true,
      performance: true,
      maintenance: true,
    },
    frequency: 'immediate',
  },
  dashboard: {
    defaultView: 'overview',
    layout: 'comfortable',
    showSidebar: true,
    sidebarCollapsed: false,
    widgets: [],
    refreshInterval: 30000,
  },
  privacy: {
    shareAnalytics: false,
    shareUsageData: false,
    allowCookies: true,
    dataRetention: 365,
  },
};

export const ROLE_PERMISSIONS: RolePermissions = {
  [UserRole.ADMIN]: [
    Permission.DASHBOARD_ADMIN,
    Permission.USER_CREATE,
    Permission.USER_VIEW,
    Permission.USER_UPDATE,
    Permission.USER_DELETE,
    Permission.USER_ROLE_ASSIGN,
    Permission.SYSTEM_VIEW,
    Permission.SYSTEM_CONFIG,
    Permission.SYSTEM_MAINTENANCE,
    Permission.SECURITY_VIEW,
    Permission.SECURITY_ALERTS,
    Permission.SECURITY_INCIDENTS,
    Permission.SECURITY_AUDIT,
    Permission.COMPLIANCE_VIEW,
    Permission.COMPLIANCE_REPORTS,
    Permission.COMPLIANCE_AUDIT,
    Permission.ANALYTICS_ADMIN,
    Permission.NOTIFICATIONS_ADMIN,
  ],
  [UserRole.SYSTEM_ADMIN]: [
    Permission.DASHBOARD_VIEW,
    Permission.USER_VIEW,
    Permission.USER_UPDATE,
    Permission.SYSTEM_VIEW,
    Permission.SYSTEM_CONFIG,
    Permission.SYSTEM_MAINTENANCE,
    Permission.SYSTEM_BACKUP,
    Permission.SECURITY_VIEW,
    Permission.SECURITY_ALERTS,
    Permission.ANALYTICS_VIEW,
    Permission.NOTIFICATIONS_VIEW,
  ],
  [UserRole.SECURITY_OFFICER]: [
    Permission.DASHBOARD_VIEW,
    Permission.ANALYSIS_VIEW,
    Permission.ANALYSIS_CREATE,
    Permission.SECURITY_VIEW,
    Permission.SECURITY_ALERTS,
    Permission.SECURITY_INCIDENTS,
    Permission.SECURITY_AUDIT,
    Permission.ANALYTICS_VIEW,
    Permission.NOTIFICATIONS_VIEW,
    Permission.NOTIFICATIONS_CREATE,
  ],
  [UserRole.COMPLIANCE_MANAGER]: [
    Permission.DASHBOARD_VIEW,
    Permission.ANALYSIS_VIEW,
    Permission.COMPLIANCE_VIEW,
    Permission.COMPLIANCE_REPORTS,
    Permission.COMPLIANCE_AUDIT,
    Permission.COMPLIANCE_EXPORT,
    Permission.ANALYTICS_VIEW,
    Permission.ANALYTICS_EXPORT,
    Permission.NOTIFICATIONS_VIEW,
  ],
  [UserRole.TECHNICAL_ADMINISTRATOR]: [
    Permission.DASHBOARD_VIEW,
    Permission.USER_VIEW,
    Permission.SYSTEM_VIEW,
    Permission.SYSTEM_CONFIG,
    Permission.SECURITY_VIEW,
    Permission.ANALYTICS_VIEW,
    Permission.NOTIFICATIONS_VIEW,
  ],
  [UserRole.ANALYST]: [
    Permission.DASHBOARD_VIEW,
    Permission.ANALYSIS_VIEW,
    Permission.ANALYSIS_CREATE,
    Permission.ANALYSIS_EXPORT,
    Permission.SECURITY_VIEW,
    Permission.ANALYTICS_VIEW,
    Permission.NOTIFICATIONS_VIEW,
  ],
  [UserRole.VIEWER]: [
    Permission.DASHBOARD_VIEW,
    Permission.ANALYSIS_VIEW,
    Permission.SECURITY_VIEW,
    Permission.ANALYTICS_VIEW,
    Permission.NOTIFICATIONS_VIEW,
  ],
  [UserRole.GUEST]: [
    Permission.DASHBOARD_VIEW,
  ],
};
