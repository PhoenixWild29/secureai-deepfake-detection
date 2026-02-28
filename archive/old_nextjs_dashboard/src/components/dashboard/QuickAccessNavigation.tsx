"use client"

import React from 'react';
import { 
  Shield, 
  BarChart3, 
  FileText, 
  Settings, 
  History, 
  Users, 
  Database, 
  Bell,
  Zap,
  Eye,
  Download,
  Upload,
  Activity
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface QuickAccessNavigationProps {
  onNavigate?: (path: string) => void;
  className?: string;
}

interface QuickAccessItem {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  path: string;
  badge?: string;
  badgeVariant?: 'default' | 'secondary' | 'destructive' | 'outline';
  isPrimary?: boolean;
}

const quickAccessItems: QuickAccessItem[] = [
  {
    id: 'upload',
    title: 'Upload Video',
    description: 'Start a new deepfake analysis',
    icon: Upload,
    path: '/upload',
    isPrimary: true,
  },
  {
    id: 'analytics',
    title: 'Analytics Dashboard',
    description: 'View detailed analytics and reports',
    icon: BarChart3,
    path: '/analytics',
    badge: 'New',
    badgeVariant: 'secondary',
  },
  {
    id: 'history',
    title: 'Analysis History',
    description: 'Browse previous analysis results',
    icon: History,
    path: '/history',
  },
  {
    id: 'results',
    title: 'View Results',
    description: 'Check latest detection results',
    icon: Eye,
    path: '/results',
  },
  {
    id: 'export',
    title: 'Export Data',
    description: 'Download reports and data',
    icon: Download,
    path: '/export',
  },
  {
    id: 'settings',
    title: 'Settings',
    description: 'Configure system preferences',
    icon: Settings,
    path: '/settings',
  },
  {
    id: 'users',
    title: 'User Management',
    description: 'Manage user accounts and permissions',
    icon: Users,
    path: '/users',
  },
  {
    id: 'storage',
    title: 'Data Storage',
    description: 'Monitor storage and blockchain status',
    icon: Database,
    path: '/storage',
  },
  {
    id: 'notifications',
    title: 'Notifications',
    description: 'View alerts and system notifications',
    icon: Bell,
    path: '/notifications',
    badge: '3',
    badgeVariant: 'destructive',
  },
];

export function QuickAccessNavigation({
  onNavigate,
  className,
}: QuickAccessNavigationProps) {
  
  const handleNavigation = (path: string) => {
    if (onNavigate) {
      onNavigate(path);
    } else {
      // Default navigation behavior
      window.location.href = path;
    }
  };

  // Group items by category
  const primaryItems = quickAccessItems.filter(item => item.isPrimary);
  const regularItems = quickAccessItems.filter(item => !item.isPrimary);

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="h-5 w-5" />
          Quick Access
        </CardTitle>
        <CardDescription>
          One-click access to key features and functions
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Primary Actions */}
        {primaryItems.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground">Primary Actions</h4>
            {primaryItems.map((item) => {
              const Icon = item.icon;
              return (
                <Button
                  key={item.id}
                  variant="default"
                  className="w-full justify-start h-auto p-4"
                  onClick={() => handleNavigation(item.path)}
                >
                  <div className="flex items-center gap-3 w-full">
                    <Icon className="h-5 w-5 flex-shrink-0" />
                    <div className="flex-1 text-left">
                      <div className="font-medium">{item.title}</div>
                      <div className="text-xs text-muted-foreground">
                        {item.description}
                      </div>
                    </div>
                    {item.badge && (
                      <Badge variant={item.badgeVariant || 'secondary'} className="ml-2">
                        {item.badge}
                      </Badge>
                    )}
                  </div>
                </Button>
              );
            })}
          </div>
        )}

        {/* Regular Actions */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Quick Links</h4>
          <div className="grid grid-cols-1 gap-2">
            {regularItems.map((item) => {
              const Icon = item.icon;
              return (
                <Button
                  key={item.id}
                  variant="outline"
                  className="w-full justify-start h-auto p-3"
                  onClick={() => handleNavigation(item.path)}
                >
                  <div className="flex items-center gap-3 w-full">
                    <Icon className="h-4 w-4 flex-shrink-0" />
                    <div className="flex-1 text-left">
                      <div className="text-sm font-medium">{item.title}</div>
                      <div className="text-xs text-muted-foreground">
                        {item.description}
                      </div>
                    </div>
                    {item.badge && (
                      <Badge 
                        variant={item.badgeVariant || 'secondary'} 
                        className="ml-2 text-xs"
                      >
                        {item.badge}
                      </Badge>
                    )}
                  </div>
                </Button>
              );
            })}
          </div>
        </div>

        {/* System Status Quick View */}
        <div className="pt-4 border-t">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-green-600" />
              <span className="text-sm font-medium">System Status</span>
            </div>
            <Badge variant="outline" className="text-green-600">
              All Systems Operational
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Last check: {new Date().toLocaleTimeString()}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export default QuickAccessNavigation;
