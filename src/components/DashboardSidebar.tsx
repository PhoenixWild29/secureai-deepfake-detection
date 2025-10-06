"use client"

import React from 'react';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent } from '@/components/ui/sheet';
import { User } from '@/types/auth';

interface DashboardSidebarProps {
  children: React.ReactNode;
  isOpen: boolean;
  isCollapsed: boolean;
  isMobile: boolean;
  onClose: () => void;
  user: User;
  className?: string;
}

export function DashboardSidebar({
  children,
  isOpen,
  isCollapsed,
  isMobile,
  onClose,
  user,
  className,
}: DashboardSidebarProps) {
  // Mobile sidebar using Sheet component
  if (isMobile) {
    return (
      <Sheet open={isOpen} onOpenChange={onClose}>
        <SheetContent side="left" className="w-80 p-0">
          <div className="flex flex-col h-full">
            {/* Mobile Sidebar Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-full bg-secureai-600 flex items-center justify-center text-white text-sm font-medium">
                  {user.name.charAt(0).toUpperCase()}
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-medium">{user.name}</span>
                  <span className="text-xs text-muted-foreground">{user.email}</span>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="h-8 w-8"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Mobile Sidebar Content */}
            <div className="flex-1 overflow-y-auto">
              {children}
            </div>
          </div>
        </SheetContent>
      </Sheet>
    );
  }

  // Desktop sidebar
  return (
    <aside
      className={cn(
        "dashboard-sidebar fixed left-0 top-0 z-40 h-full transition-all duration-300 ease-in-out",
        isCollapsed ? "w-16" : "w-64",
        "border-r bg-background",
        className
      )}
      aria-label="Dashboard navigation"
      aria-hidden={isMobile && !isOpen}
    >
      <div className="flex flex-col h-full">
        {/* Desktop Sidebar Header */}
        <div className="flex items-center justify-between p-4 border-b">
          {!isCollapsed && (
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-secureai-600 flex items-center justify-center text-white text-sm font-medium">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-medium truncate">{user.name}</span>
                <span className="text-xs text-muted-foreground truncate">{user.email}</span>
              </div>
            </div>
          )}
          
          {isCollapsed && (
            <div className="flex justify-center w-full">
              <div className="h-8 w-8 rounded-full bg-secureai-600 flex items-center justify-center text-white text-sm font-medium">
                {user.name.charAt(0).toUpperCase()}
              </div>
            </div>
          )}
        </div>

        {/* Desktop Sidebar Content */}
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>

        {/* Desktop Sidebar Footer - Collapse Toggle */}
        <div className="p-4 border-t">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              // This will be handled by the parent component
              // The parent should update the collapsed state
            }}
            className="w-full h-8"
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </aside>
  );
}

// Export additional sidebar components for customization
export const DashboardSidebarHeader: React.FC<{
  user: User;
  isCollapsed: boolean;
  className?: string;
}> = ({ user, isCollapsed, className }) => {
  return (
    <div className={cn("flex items-center justify-between p-4 border-b", className)}>
      {!isCollapsed && (
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-secureai-600 flex items-center justify-center text-white text-sm font-medium">
            {user.name.charAt(0).toUpperCase()}
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium truncate">{user.name}</span>
            <span className="text-xs text-muted-foreground truncate">{user.email}</span>
          </div>
        </div>
      )}
      
      {isCollapsed && (
        <div className="flex justify-center w-full">
          <div className="h-8 w-8 rounded-full bg-secureai-600 flex items-center justify-center text-white text-sm font-medium">
            {user.name.charAt(0).toUpperCase()}
          </div>
        </div>
      )}
    </div>
  );
};

export const DashboardSidebarContent: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className }) => {
  return (
    <div className={cn("flex-1 overflow-y-auto", className)}>
      {children}
    </div>
  );
};

export const DashboardSidebarFooter: React.FC<{
  isCollapsed: boolean;
  onToggle: () => void;
  className?: string;
}> = ({ isCollapsed, onToggle, className }) => {
  return (
    <div className={cn("p-4 border-t", className)}>
      <Button
        variant="ghost"
        size="icon"
        onClick={onToggle}
        className="w-full h-8"
        aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {isCollapsed ? (
          <ChevronRight className="h-4 w-4" />
        ) : (
          <ChevronLeft className="h-4 w-4" />
        )}
      </Button>
    </div>
  );
};

// Export sidebar variants for different layouts
export const DashboardSidebarVariants = {
  default: "w-64",
  collapsed: "w-16",
  wide: "w-80",
  compact: "w-48",
};

export const DashboardSidebarThemes = {
  light: "bg-white border-gray-200",
  dark: "bg-gray-900 border-gray-700",
  secureai: "bg-secureai-50 border-secureai-200",
};

export default DashboardSidebar;
