# Overview

Activity Tracker is a comprehensive web application for monitoring and managing user activities with real-time statistics. The system features a React frontend with a Flask backend, providing user activity tracking, tag management, department organization, and JWT-based authentication. The application includes a dashboard with real-time statistics, activity management with tags and categories, user management, dark/light theme support, and a desktop agent for Windows activity monitoring.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: React 18 with Vite as the build tool
- **Styling**: Tailwind CSS for responsive design with dark/light theme support
- **UI Components**: Heroicons for icons, Recharts for data visualization
- **HTTP Client**: Axios with interceptors for automatic token management and error handling
- **State Management**: React Context for authentication state
- **Routing**: Client-side routing for single-page application experience

## Backend Architecture
- **Framework**: Flask with Blueprint-based modular routing
- **Authentication**: JWT tokens with bcrypt for password hashing
- **Database Layer**: PostgreSQL with connection pooling using psycopg2
- **API Design**: RESTful endpoints organized by feature (auth, activities, users, departments, tags, categories)
- **Security**: Token-based authentication with automatic token validation middleware
- **Error Handling**: Centralized error handling with proper HTTP status codes

## Data Storage
- **Primary Database**: PostgreSQL with UUID primary keys
- **Connection Management**: Thread-safe connection pooling for scalability
- **Schema Design**: Relational model with departments, users, monitored users, activities, tags, and categories
- **Data Integrity**: Foreign key constraints and proper indexing

## Desktop Agent
- **Platform**: Windows-specific agent using win32gui and psutil
- **Functionality**: Monitors active windows and system idle time
- **Communication**: HTTP API calls to the backend for activity reporting
- **Authentication**: JWT token-based authentication with the main system

# External Dependencies

## Frontend Dependencies
- **React Ecosystem**: React 18, React DOM for UI framework
- **Build Tools**: Vite for development and building, PostCSS and Autoprefixer for CSS processing
- **UI/UX**: Tailwind CSS for styling, @headlessui/react for accessible components, @heroicons/react for icons
- **Data Visualization**: Recharts for charts and graphs
- **HTTP Client**: Axios for API communication
- **Date Handling**: date-fns for date formatting and manipulation

## Backend Dependencies
- **Web Framework**: Flask 2.3.3 with flask-cors for cross-origin support
- **Database**: psycopg2-binary for PostgreSQL connectivity
- **Security**: bcrypt for password hashing, PyJWT for token management
- **Configuration**: python-dotenv for environment variable management
- **HTTP Client**: requests for external API calls

## Database
- **PostgreSQL**: Primary database for all application data
- **Connection Pooling**: Built-in support for Neon.tech connection pooler
- **Environment Configuration**: Supports both DATABASE_URL and individual connection parameters

## Development Tools
- **TypeScript Support**: Type definitions for React components
- **Development Server**: Vite dev server with hot reload and CORS configuration
- **Environment Management**: .env file support for configuration management
- **Database Initialization**: Custom scripts for schema setup and data seeding