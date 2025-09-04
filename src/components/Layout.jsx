import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";
import {
  ChartBarIcon,
  ClipboardDocumentListIcon,
  Cog6ToothIcon,
  MoonIcon,
  SunIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  XMarkIcon,
  ClockIcon,
} from "@heroicons/react/24/outline";
import Dashboard from "./Dashboard";
import ActivityManagement from "./ActivityManagement";
import TagManagement from "./TagManagement";
import UserManagement from "./UserManagement";
import Settings from "./Settings";
import WorkScheduleManagement from "./WorkScheduleManagement";

const navigation = [
  { name: "Dashboard", icon: ChartBarIcon, component: "dashboard" },
  {
    name: "Gerenciamento",
    icon: ClipboardDocumentListIcon,
    component: "management",
  },
  { name: "Tags", icon: ClipboardDocumentListIcon, component: "tags" },
  { name: "Usuários", icon: ClipboardDocumentListIcon, component: "users" },
  { name: "Escalas", icon: ClockIcon, component: "schedules" },
  { name: "Configurações", icon: Cog6ToothIcon, component: "settings" },
];

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentView, setCurrentView] = useState("dashboard");
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();

  const renderCurrentView = () => {
    switch (currentView) {
      case "dashboard":
        return <Dashboard />;
      case "management":
        return <ActivityManagement />;
      case "tags":
        return <TagManagement />;
      case "users":
        return <UserManagement />;
      case "schedules":
        return <WorkScheduleManagement />;
      case "settings":
        return <Settings />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="h-screen flex bg-gray-100 dark:bg-gray-900">
      {/* Mobile sidebar */}
      <div
        className={`fixed inset-0 flex z-40 md:hidden ${sidebarOpen ? "" : "hidden"}`}
      >
        <div
          className="fixed inset-0 bg-gray-600 bg-opacity-75"
          onClick={() => setSidebarOpen(false)}
        />
        <div className="relative flex-1 flex flex-col max-w-xs w-full bg-white dark:bg-gray-800">
          <div className="absolute top-0 right-0 -mr-12 pt-2">
            <button
              type="button"
              className="ml-1 flex items-center justify-center h-10 w-10 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
              onClick={() => setSidebarOpen(false)}
            >
              <XMarkIcon className="h-6 w-6 text-white" />
            </button>
          </div>
          <div className="flex-1 h-0 pt-5 pb-4 overflow-y-auto">
            <div className="flex-shrink-0 flex items-center px-4">
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                Activity Tracker
              </h1>
            </div>
            <nav className="mt-5 px-2 space-y-1">
              {navigation.map((item) => (
                <button
                  key={item.name}
                  onClick={() => {
                    setCurrentView(item.component);
                    setSidebarOpen(false);
                  }}
                  className={`w-full group flex items-center px-2 py-2 text-base font-medium rounded-md ${
                    currentView === item.component
                      ? "bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white"
                      : "text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                  }`}
                >
                  <item.icon className="mr-4 flex-shrink-0 h-6 w-6" />
                  {item.name}
                </button>
              ))}
            </nav>
          </div>
          <div className="flex-shrink-0 flex border-t border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center">
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
                    {user?.usuario}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={toggleTheme}
                  className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  {isDark ? (
                    <SunIcon className="h-5 w-5" />
                  ) : (
                    <MoonIcon className="h-5 w-5" />
                  )}
                </button>
                <button
                  onClick={logout}
                  className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <ArrowRightOnRectangleIcon className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Static sidebar for desktop */}
      <div className="hidden md:flex md:flex-shrink-0">
        <div className="flex flex-col w-64">
          <div className="flex flex-col h-0 flex-1 bg-white dark:bg-gray-800">
            <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
              <div className="flex items-center flex-shrink-0 px-4">
                <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Activity Tracker
                </h1>
              </div>
              <nav className="mt-5 px-2 space-y-1">
                {navigation.map((item) => (
                  <button
                    key={item.name}
                    onClick={() => setCurrentView(item.component)}
                    className={`w-full group flex items-center px-2 py-2 text-sm font-medium rounded-md ${
                      currentView === item.component
                        ? "bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white"
                        : "text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                    }`}
                  >
                    <item.icon className="mr-3 flex-shrink-0 h-6 w-6" />
                    {item.name}
                  </button>
                ))}
              </nav>
            </div>
            <div className="flex-shrink-0 flex border-t border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center">
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
                      {user?.usuario}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={toggleTheme}
                    className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    {isDark ? (
                      <SunIcon className="h-5 w-5" />
                    ) : (
                      <MoonIcon className="h-5 w-5" />
                    )}
                  </button>
                  <button
                    onClick={logout}
                    className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <ArrowRightOnRectangleIcon className="h-5 w-5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col w-0 flex-1 overflow-hidden">
        <div className="md:hidden pl-1 pt-1 sm:pl-3 sm:pt-3">
          <button
            type="button"
            className="-ml-0.5 -mt-0.5 h-12 w-12 inline-flex items-center justify-center rounded-md text-gray-500 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
            onClick={() => setSidebarOpen(true)}
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
        </div>
        <main className="flex-1 relative z-0 overflow-y-auto focus:outline-none">
          <div className="py-6">
            <div className="max-w-8xl mx-auto px-4 sm:px-6 md:px-8">
              {currentView === "dashboard" && <Dashboard />}
              {currentView === "management" && <ActivityManagement />}
              {currentView === "tags" && <TagManagement />}
              {currentView === "users" && <UserManagement />}
              {currentView === "schedules" && <WorkScheduleManagement />}
              {currentView === "settings" && <Settings />}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}