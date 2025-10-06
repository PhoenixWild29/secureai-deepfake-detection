"use client"

import React, { useState } from 'react';
import { Menu, Bell, Settings, User, LogOut, Shield, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { User as UserType, UserRole } from '@/types/auth';
import { authManager } from '@/lib/auth';
import NotificationCenter from '@/components/NotificationCenter/NotificationCenter';
import { useNotificationBadge } from '@/hooks/useNotifications';

interface DashboardHeaderProps {
  user: UserType;
  onMenuClick: () => void;
  sidebarCollapsed: boolean;
  isMobile: boolean;
  className?: string;
}

export function DashboardHeader({
  user,
  onMenuClick,
  sidebarCollapsed,
  isMobile,
  className,
}: DashboardHeaderProps) {
  const [isNotificationCenterOpen, setIsNotificationCenterOpen] = useState(false);
  const { unreadCount, hasUnread, isConnected } = useNotificationBadge(user.id);

  const handleLogout = async () => {
    try {
      await authManager.logout();
      window.location.href = '/auth/login';
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const handleNotificationClick = () => {
    setIsNotificationCenterOpen(true);
  };

  const getRoleDisplayName = (role: UserRole): string => {
    switch (role) {
      case UserRole.ADMIN:
        return 'Administrator';
      case UserRole.SYSTEM_ADMIN:
        return 'System Administrator';
      case UserRole.SECURITY_OFFICER:
        return 'Security Officer';
      case UserRole.COMPLIANCE_MANAGER:
        return 'Compliance Manager';
      case UserRole.TECHNICAL_ADMINISTRATOR:
        return 'Technical Administrator';
      case UserRole.ANALYST:
        return 'Analyst';
      case UserRole.VIEWER:
        return 'Viewer';
      case UserRole.GUEST:
        return 'Guest';
      default:
        return role;
    }
  };

  const getRoleColor = (role: UserRole): string => {
    switch (role) {
      case UserRole.ADMIN:
        return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/20';
      case UserRole.SYSTEM_ADMIN:
        return 'text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-900/20';
      case UserRole.SECURITY_OFFICER:
        return 'text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/20';
      case UserRole.COMPLIANCE_MANAGER:
        return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/20';
      case UserRole.TECHNICAL_ADMINISTRATOR:
        return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/20';
      case UserRole.ANALYST:
        return 'text-indigo-600 bg-indigo-100 dark:text-indigo-400 dark:bg-indigo-900/20';
      case UserRole.VIEWER:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/20';
      case UserRole.GUEST:
        return 'text-gray-500 bg-gray-100 dark:text-gray-500 dark:bg-gray-900/20';
      default:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/20';
    }
  };

  const primaryRole = user.roles[0] || UserRole.VIEWER;

  return (
    <header className={cn("dashboard-header flex h-16 items-center justify-between px-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60", className)} role="banner" aria-label="Dashboard header">
      {/* Left Section - Menu Button and Branding */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={onMenuClick}
          className="md:hidden mobile-only"
          aria-label="Toggle sidebar"
        >
          <Menu className="h-5 w-5" />
        </Button>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-secureai-600" />
            <span className="font-bold text-lg secureai-gradient-text">
              SecureAI
            </span>
          </div>
          
          {!isMobile && (
            <div className="hidden md:flex items-center gap-2 ml-4 pl-4 border-l">
              <span className="text-sm text-muted-foreground">Dashboard</span>
              <span className="text-sm text-muted-foreground">•</span>
              <span className={cn("text-xs px-2 py-1 rounded-full font-medium", getRoleColor(primaryRole))}>
                {getRoleDisplayName(primaryRole)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Right Section - Actions and User Menu */}
      <div className="flex items-center gap-2">
        {/* Notifications */}
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label="Notifications"
          onClick={handleNotificationClick}
        >
          <Bell className="h-5 w-5" />
          {/* Notification badge */}
          {hasUnread && (
            <span className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full text-xs text-white flex items-center justify-center">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
          {/* Connection indicator */}
          {!isConnected && (
            <span className="absolute -bottom-1 -right-1 h-2 w-2 bg-gray-400 rounded-full" />
          )}
        </Button>

        {/* Settings */}
        <Button
          variant="ghost"
          size="icon"
          aria-label="Settings"
        >
          <Settings className="h-5 w-5" />
        </Button>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="flex items-center gap-2 px-3 py-2 h-auto"
            >
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-secureai-600 flex items-center justify-center text-white text-sm font-medium">
                  {user.name.charAt(0).toUpperCase()}
                </div>
                {!isMobile && (
                  <div className="flex flex-col items-start">
                    <span className="text-sm font-medium">{user.name}</span>
                    <span className="text-xs text-muted-foreground">{user.email}</span>
                  </div>
                )}
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              </div>
            </Button>
          </DropdownMenuTrigger>
          
          <DropdownMenuContent align="end" className="w-64">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">{user.name}</p>
                <p className="text-xs leading-none text-muted-foreground">
                  {user.email}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <span className={cn("text-xs px-2 py-1 rounded-full font-medium", getRoleColor(primaryRole))}>
                    {getRoleDisplayName(primaryRole)}
                  </span>
                  {user.roles.length > 1 && (
                    <span className="text-xs text-muted-foreground">
                      +{user.roles.length - 1} more
                    </span>
                  )}
                </div>
              </div>
            </DropdownMenuLabel>
            
            <DropdownMenuSeparator />
            
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              <span>Profile</span>
            </DropdownMenuItem>
            
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              <span>Settings</span>
            </DropdownMenuItem>
            
            <DropdownMenuItem onClick={handleNotificationClick}>
              <Bell className="mr-2 h-4 w-4" />
              <span>Notifications</span>
              {hasUnread && (
                <span className="ml-auto text-xs bg-red-500 text-white px-1.5 py-0.5 rounded-full">
                  {unreadCount}
                </span>
              )}
            </DropdownMenuItem>
            
            <DropdownMenuSeparator />
            
            <DropdownMenuItem onClick={handleLogout} className="text-red-600 focus:text-red-600">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Notification Center */}
      <NotificationCenter
        isOpen={isNotificationCenterOpen}
        onClose={() => setIsNotificationCenterOpen(false)}
        userId={user.id}
      />
    </header>
  );
}

// Export additional header components for customization
export const DashboardHeaderBrand: React.FC<{
  className?: string;
  showRole?: boolean;
  user?: UserType;
}> = ({ className, showRole = false, user }) => {
  if (!user) return null;

  const primaryRole = user.roles[0] || UserRole.VIEWER;
  
  const getRoleDisplayName = (role: UserRole): string => {
    switch (role) {
      case UserRole.ADMIN:
        return 'Administrator';
      case UserRole.SYSTEM_ADMIN:
        return 'System Administrator';
      case UserRole.SECURITY_OFFICER:
        return 'Security Officer';
      case UserRole.COMPLIANCE_MANAGER:
        return 'Compliance Manager';
      case UserRole.TECHNICAL_ADMINISTRATOR:
        return 'Technical Administrator';
      case UserRole.ANALYST:
        return 'Analyst';
      case UserRole.VIEWER:
        return 'Viewer';
      case UserRole.GUEST:
        return 'Guest';
      default:
        return role;
    }
  };

  const getRoleColor = (role: UserRole): string => {
    switch (role) {
      case UserRole.ADMIN:
        return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/20';
      case UserRole.SYSTEM_ADMIN:
        return 'text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-900/20';
      case UserRole.SECURITY_OFFICER:
        return 'text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/20';
      case UserRole.COMPLIANCE_MANAGER:
        return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/20';
      case UserRole.TECHNICAL_ADMINISTRATOR:
        return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/20';
      case UserRole.ANALYST:
        return 'text-indigo-600 bg-indigo-100 dark:text-indigo-400 dark:bg-indigo-900/20';
      case UserRole.VIEWER:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/20';
      case UserRole.GUEST:
        return 'text-gray-500 bg-gray-100 dark:text-gray-500 dark:bg-gray-900/20';
      default:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/20';
    }
  };

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="flex items-center gap-2">
        <Shield className="h-6 w-6 text-secureai-600" />
        <span className="font-bold text-lg secureai-gradient-text">
          SecureAI
        </span>
      </div>
      
      {showRole && (
        <div className="flex items-center gap-2 ml-4 pl-4 border-l">
          <span className="text-sm text-muted-foreground">Dashboard</span>
          <span className="text-sm text-muted-foreground">•</span>
          <span className={cn("text-xs px-2 py-1 rounded-full font-medium", getRoleColor(primaryRole))}>
            {getRoleDisplayName(primaryRole)}
          </span>
        </div>
      )}
    </div>
  );
};

export const DashboardHeaderActions: React.FC<{
  className?: string;
  showNotifications?: boolean;
  showSettings?: boolean;
  userId?: string;
  onNotificationClick?: () => void;
}> = ({ className, showNotifications = true, showSettings = true, userId, onNotificationClick }) => {
  const { unreadCount, hasUnread, isConnected } = useNotificationBadge(userId || '');

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {showNotifications && (
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label="Notifications"
          onClick={onNotificationClick}
        >
          <Bell className="h-5 w-5" />
          {hasUnread && (
            <span className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full text-xs text-white flex items-center justify-center">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
          {!isConnected && (
            <span className="absolute -bottom-1 -right-1 h-2 w-2 bg-gray-400 rounded-full" />
          )}
        </Button>
      )}

      {showSettings && (
        <Button
          variant="ghost"
          size="icon"
          aria-label="Settings"
        >
          <Settings className="h-5 w-5" />
        </Button>
      )}
    </div>
  );
};

export default DashboardHeader;
