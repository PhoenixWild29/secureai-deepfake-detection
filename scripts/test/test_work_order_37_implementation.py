#!/usr/bin/env python3
"""
Test suite for Work Order #37: Dashboard Layout Component Implementation
Tests the React/Next.js dashboard layout components with TypeScript and shadcn/ui
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

class WorkOrder37Validator:
    def __init__(self):
        self.project_root = Path(".")
        self.src_dir = self.project_root / "src"
        self.components_dir = self.src_dir / "components"
        self.ui_dir = self.components_dir / "ui"
        self.types_dir = self.src_dir / "types"
        self.lib_dir = self.src_dir / "lib"
        self.styles_dir = self.src_dir / "styles"
        self.app_dir = self.src_dir / "app"
        
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_tests = 0

    def log_error(self, test_name: str, message: str):
        """Log an error for a test"""
        self.errors.append(f"❌ {test_name}: {message}")
        print(f"❌ {test_name}: {message}")

    def log_success(self, test_name: str, message: str):
        """Log a success for a test"""
        self.success_count += 1
        print(f"✅ {test_name}: {message}")

    def log_warning(self, test_name: str, message: str):
        """Log a warning for a test"""
        self.warnings.append(f"⚠️  {test_name}: {message}")
        print(f"⚠️  {test_name}: {message}")

    def check_file_exists(self, file_path: Path, test_name: str) -> bool:
        """Check if a file exists"""
        self.total_tests += 1
        if file_path.exists():
            self.log_success(test_name, f"File exists: {file_path}")
            return True
        else:
            self.log_error(test_name, f"File missing: {file_path}")
            return False

    def check_file_content(self, file_path: Path, test_name: str, required_content: List[str]) -> bool:
        """Check if file contains required content"""
        self.total_tests += 1
        if not file_path.exists():
            self.log_error(test_name, f"File missing: {file_path}")
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            missing_content = []
            for required in required_content:
                if required not in content:
                    missing_content.append(required)
            
            if missing_content:
                self.log_error(test_name, f"Missing content: {missing_content}")
                return False
            else:
                self.log_success(test_name, f"All required content found in {file_path}")
                return True
        except Exception as e:
            self.log_error(test_name, f"Error reading file: {e}")
            return False

    def test_package_json_configuration(self):
        """Test package.json configuration"""
        print("\n🧪 Testing package.json configuration...")
        
        if not self.check_file_exists(self.project_root / "package.json", "Package.json exists"):
            return False
        
        required_dependencies = [
            '"next":',
            '"react":',
            '"typescript":',
            '"tailwindcss":',
            '"@radix-ui/',
            '"lucide-react":',
            '"class-variance-authority":',
            '"clsx":',
            '"tailwind-merge":'
        ]
        
        return self.check_file_content(
            self.project_root / "package.json",
            "Package.json dependencies",
            required_dependencies
        )

    def test_typescript_configuration(self):
        """Test TypeScript configuration"""
        print("\n🧪 Testing TypeScript configuration...")
        
        if not self.check_file_exists(self.project_root / "tsconfig.json", "tsconfig.json exists"):
            return False
        
        required_config = [
            '"target": "ES2020"',
            '"strict": true',
            '"jsx": "preserve"',
            '"baseUrl": "."',
            '"paths": {',
            '"@/*": ["./src/*"]'
        ]
        
        return self.check_file_content(
            self.project_root / "tsconfig.json",
            "TypeScript configuration",
            required_config
        )

    def test_tailwind_configuration(self):
        """Test Tailwind CSS configuration"""
        print("\n🧪 Testing Tailwind CSS configuration...")
        
        if not self.check_file_exists(self.project_root / "tailwind.config.js", "tailwind.config.js exists"):
            return False
        
        required_config = [
            'darkMode: ["class"]',
            'content: [',
            'shadcn/ui',
            'extend: {',
            'colors: {',
            'secureai: {'
        ]
        
        return self.check_file_content(
            self.project_root / "tailwind.config.js",
            "Tailwind configuration",
            required_config
        )

    def test_authentication_types(self):
        """Test authentication type definitions"""
        print("\n🧪 Testing authentication types...")
        
        if not self.check_file_exists(self.types_dir / "auth.ts", "auth.ts exists"):
            return False
        
        required_types = [
            'interface User {',
            'enum UserRole {',
            'enum Permission {',
            'interface AuthContextType {',
            'interface NavigationItem {',
            'interface MenuSection {',
            'ROLE_PERMISSIONS:'
        ]
        
        return self.check_file_content(
            self.types_dir / "auth.ts",
            "Authentication types",
            required_types
        )

    def test_authentication_utilities(self):
        """Test authentication utilities"""
        print("\n🧪 Testing authentication utilities...")
        
        if not self.check_file_exists(self.lib_dir / "auth.ts", "auth.ts exists"):
            return False
        
        required_functions = [
            'class AuthManager {',
            'login(',
            'logout(',
            'register(',
            'hasPermission(',
            'hasRole(',
            'getCurrentUser(',
            'isAuthenticated('
        ]
        
        return self.check_file_content(
            self.lib_dir / "auth.ts",
            "Authentication utilities",
            required_functions
        )

    def test_ui_components(self):
        """Test shadcn/ui components"""
        print("\n🧪 Testing UI components...")
        
        ui_components = [
            ("button.tsx", ["buttonVariants", "ButtonProps", "Button = React.forwardRef"]),
            ("sheet.tsx", ["Sheet = SheetPrimitive.Root", "SheetContent", "SheetTrigger"]),
            ("dropdown-menu.tsx", ["DropdownMenu = DropdownMenuPrimitive.Root", "DropdownMenuContent", "DropdownMenuItem"]),
            ("card.tsx", ["Card = React.forwardRef", "CardHeader", "CardContent"]),
            ("badge.tsx", ["badgeVariants", "BadgeProps", "Badge("])
        ]
        
        all_passed = True
        for component_file, required_content in ui_components:
            component_path = self.ui_dir / component_file
            if not self.check_file_exists(component_path, f"{component_file} exists"):
                all_passed = False
                continue
            
            if not self.check_file_content(component_path, f"{component_file} content", required_content):
                all_passed = False
        
        return all_passed

    def test_dashboard_layout_component(self):
        """Test main dashboard layout component"""
        print("\n🧪 Testing dashboard layout component...")
        
        if not self.check_file_exists(self.components_dir / "DashboardLayout.tsx", "DashboardLayout.tsx exists"):
            return False
        
        required_content = [
            'interface DashboardLayoutProps {',
            'export function DashboardLayout(',
            'DashboardHeader',
            'DashboardSidebar',
            'DashboardNavigation',
            'useState(',
            'useEffect(',
            'responsive',
            'mobile',
            'sidebarOpen',
            'sidebarCollapsed'
        ]
        
        return self.check_file_content(
            self.components_dir / "DashboardLayout.tsx",
            "Dashboard layout component",
            required_content
        )

    def test_dashboard_header_component(self):
        """Test dashboard header component"""
        print("\n🧪 Testing dashboard header component...")
        
        if not self.check_file_exists(self.components_dir / "DashboardHeader.tsx", "DashboardHeader.tsx exists"):
            return False
        
        required_content = [
            'interface DashboardHeaderProps {',
            'export function DashboardHeader(',
            'Menu,',
            'Bell,',
            'Settings,',
            'User,',
            'LogOut',
            'DropdownMenu',
            'getRoleDisplayName',
            'getRoleColor'
        ]
        
        return self.check_file_content(
            self.components_dir / "DashboardHeader.tsx",
            "Dashboard header component",
            required_content
        )

    def test_dashboard_sidebar_component(self):
        """Test dashboard sidebar component"""
        print("\n🧪 Testing dashboard sidebar component...")
        
        if not self.check_file_exists(self.components_dir / "DashboardSidebar.tsx", "DashboardSidebar.tsx exists"):
            return False
        
        required_content = [
            'interface DashboardSidebarProps {',
            'export function DashboardSidebar(',
            'Sheet,',
            'SheetContent',
            'isMobile',
            'isCollapsed',
            'ChevronLeft',
            'ChevronRight'
        ]
        
        return self.check_file_content(
            self.components_dir / "DashboardSidebar.tsx",
            "Dashboard sidebar component",
            required_content
        )

    def test_dashboard_navigation_component(self):
        """Test dashboard navigation component"""
        print("\n🧪 Testing dashboard navigation component...")
        
        if not self.check_file_exists(self.components_dir / "DashboardNavigation.tsx", "DashboardNavigation.tsx exists"):
            return False
        
        required_content = [
            'interface DashboardNavigationProps {',
            'export function DashboardNavigation(',
            'UserRole,',
            'Permission,',
            'NavigationItem,',
            'MenuSection',
            'role-based',
            'getVisibleSections',
            'isItemVisible',
            'isItemActive'
        ]
        
        return self.check_file_content(
            self.components_dir / "DashboardNavigation.tsx",
            "Dashboard navigation component",
            required_content
        )

    def test_app_layout(self):
        """Test Next.js app layout"""
        print("\n🧪 Testing app layout...")
        
        if not self.check_file_exists(self.app_dir / "layout.tsx", "layout.tsx exists"):
            return False
        
        required_content = [
            'export const metadata: Metadata',
            'SecureAI Dashboard',
            'Inter({ subsets: [\'latin\'] })',
            'export default function RootLayout(',
            'html lang="en"',
            'suppressHydrationWarning'
        ]
        
        return self.check_file_content(
            self.app_dir / "layout.tsx",
            "App layout",
            required_content
        )

    def test_dashboard_page(self):
        """Test dashboard page implementation"""
        print("\n🧪 Testing dashboard page...")
        
        dashboard_page = self.app_dir / "dashboard" / "page.tsx"
        if not self.check_file_exists(dashboard_page, "dashboard page exists"):
            return False
        
        required_content = [
            'export default function DashboardPage(',
            'DashboardLayout',
            'Card,',
            'CardContent,',
            'CardHeader,',
            'CardTitle',
            'Button',
            'Badge',
            'Shield,',
            'Activity,',
            'TrendingUp'
        ]
        
        return self.check_file_content(
            dashboard_page,
            "Dashboard page",
            required_content
        )

    def test_global_styles(self):
        """Test global styles configuration"""
        print("\n🧪 Testing global styles...")
        
        if not self.check_file_exists(self.styles_dir / "globals.css", "globals.css exists"):
            return False
        
        required_content = [
            '@tailwind base;',
            '@tailwind components;',
            '@tailwind utilities;',
            ':root {',
            '--background:',
            '--foreground:',
            '.dark {',
            'dashboard-layout',
            'dashboard-header',
            'dashboard-sidebar',
            'nav-item',
            'secureai-gradient'
        ]
        
        return self.check_file_content(
            self.styles_dir / "globals.css",
            "Global styles",
            required_content
        )

    def test_utility_functions(self):
        """Test utility functions"""
        print("\n🧪 Testing utility functions...")
        
        if not self.check_file_exists(self.lib_dir / "utils.ts", "utils.ts exists"):
            return False
        
        required_content = [
            'import { type ClassValue, clsx } from "clsx"',
            'import { twMerge } from "tailwind-merge"',
            'export function cn(',
            'return twMerge(clsx(inputs))'
        ]
        
        return self.check_file_content(
            self.lib_dir / "utils.ts",
            "Utility functions",
            required_content
        )

    def test_responsive_design(self):
        """Test responsive design implementation"""
        print("\n🧪 Testing responsive design...")
        
        # Check for responsive classes in components
        responsive_checks = [
            (self.components_dir / "DashboardLayout.tsx", ["isMobile", "md:hidden", "responsive"]),
            (self.components_dir / "DashboardHeader.tsx", ["md:hidden", "hidden md:flex", "mobile"]),
            (self.components_dir / "DashboardSidebar.tsx", ["isMobile", "w-64", "w-16", "transition-all"]),
            (self.app_dir / "dashboard" / "page.tsx", ["md:grid-cols-2", "lg:grid-cols-4", "grid gap-4"])
        ]
        
        all_passed = True
        for file_path, required_content in responsive_checks:
            if file_path.exists():
                if not self.check_file_content(file_path, f"Responsive design in {file_path.name}", required_content):
                    all_passed = False
            else:
                self.log_error(f"Responsive design check for {file_path.name}", f"File missing: {file_path}")
                all_passed = False
        
        return all_passed

    def test_accessibility_features(self):
        """Test accessibility features"""
        print("\n🧪 Testing accessibility features...")
        
        # Check for accessibility attributes and ARIA labels
        accessibility_checks = [
            (self.components_dir / "DashboardLayout.tsx", ["aria-label", "aria-hidden"]),
            (self.components_dir / "DashboardHeader.tsx", ["aria-label", "aria-hidden"]),
            (self.components_dir / "DashboardSidebar.tsx", ["aria-label", "aria-hidden"]),
            (self.components_dir / "DashboardNavigation.tsx", ["aria-label", "aria-hidden"]),
            (self.components_dir / "ui" / "button.tsx", ["aria-label", "aria-hidden"]),
            (self.components_dir / "ui" / "dropdown-menu.tsx", ["aria-label", "aria-hidden"])
        ]
        
        all_passed = True
        for file_path, required_content in accessibility_checks:
            if file_path.exists():
                if not self.check_file_content(file_path, f"Accessibility in {file_path.name}", required_content):
                    all_passed = False
            else:
                self.log_error(f"Accessibility check for {file_path.name}", f"File missing: {file_path}")
                all_passed = False
        
        return all_passed

    def test_role_based_access(self):
        """Test role-based access control"""
        print("\n🧪 Testing role-based access control...")
        
        # Check for role-based logic in navigation
        role_based_checks = [
            (self.types_dir / "auth.ts", ["UserRole", "Permission", "ROLE_PERMISSIONS", "SECURITY_OFFICER", "COMPLIANCE_MANAGER"]),
            (self.components_dir / "DashboardNavigation.tsx", ["UserRole", "Permission", "hasRequiredRole", "hasRequiredPermission", "getVisibleSections"]),
            (self.lib_dir / "auth.ts", ["hasPermission", "hasRole", "hasAnyRole", "hasAllRoles"])
        ]
        
        all_passed = True
        for file_path, required_content in role_based_checks:
            if file_path.exists():
                if not self.check_file_content(file_path, f"Role-based access in {file_path.name}", required_content):
                    all_passed = False
            else:
                self.log_error(f"Role-based access check for {file_path.name}", f"File missing: {file_path}")
                all_passed = False
        
        return all_passed

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Work Order #37 Implementation Tests")
        print("=" * 60)
        
        tests = [
            self.test_package_json_configuration,
            self.test_typescript_configuration,
            self.test_tailwind_configuration,
            self.test_authentication_types,
            self.test_authentication_utilities,
            self.test_ui_components,
            self.test_dashboard_layout_component,
            self.test_dashboard_header_component,
            self.test_dashboard_sidebar_component,
            self.test_dashboard_navigation_component,
            self.test_app_layout,
            self.test_dashboard_page,
            self.test_global_styles,
            self.test_utility_functions,
            self.test_responsive_design,
            self.test_accessibility_features,
            self.test_role_based_access,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_error(f"Test {test.__name__}", f"Unexpected error: {e}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.success_count}")
        print(f"❌ Failed: {len(self.errors)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"📈 Total Tests: {self.total_tests}")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        success_rate = (self.success_count / self.total_tests * 100) if self.total_tests > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT! Implementation meets all requirements.")
        elif success_rate >= 80:
            print("👍 GOOD! Implementation meets most requirements.")
        elif success_rate >= 70:
            print("⚠️  FAIR! Implementation needs some improvements.")
        else:
            print("❌ POOR! Implementation needs significant improvements.")
        
        return success_rate >= 80

def main():
    """Main function"""
    validator = WorkOrder37Validator()
    success = validator.run_all_tests()
    
    if success:
        print("\n✅ Work Order #37 implementation validation PASSED!")
        sys.exit(0)
    else:
        print("\n❌ Work Order #37 implementation validation FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
