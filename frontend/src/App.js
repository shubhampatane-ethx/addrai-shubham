import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar, Toolbar, Typography, Button, Box, IconButton, Menu, MenuItem, Chip
} from '@mui/material';
import { Home, ExitToApp, Person, SupervisorAccount, Settings } from '@mui/icons-material';
import Dashboard from './components/Dashboard';
import Login from './pages/Login';
import AdminUsers from './pages/AdminUsers';
import AdminValidators from './pages/AdminValidators';
import ProtectedRoute from './components/ProtectedRoute';
import authService from './utils/authService';

const { isAuthenticated, getCurrentUser, logout, setupAxiosInterceptor } = authService;

function Navigation() {
  const navigate = useNavigate();
  const location = useLocation();
  const [anchorEl, setAnchorEl] = React.useState(null);
  const user = getCurrentUser();
  const isAdmin = user?.role === 'admin';

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleHome = () => {
    navigate('/dashboard');
  };

  // Don't show navigation on login page
  if (location.pathname === '/login') {
    return null;
  }

  return (
    <AppBar
      position="sticky"
      elevation={2}
      sx={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Toolbar>
        {/* Logo and Home Button */}
        <IconButton
          color="inherit"
          onClick={handleHome}
          sx={{ mr: 2 }}
          title="Go to Dashboard"
        >
          <Home />
        </IconButton>

        <Typography
          variant="h6"
          sx={{
            flexGrow: 1,
            fontWeight: 700,
            cursor: 'pointer'
          }}
          onClick={handleHome}
        >
          AddrAI
        </Typography>

        {/* Current Page Indicator */}
        {location.pathname === '/dashboard' && (
          <Chip
            label="Dashboard"
            size="small"
            sx={{ mr: 2, bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }}
          />
        )}
        {location.pathname === '/admin/users' && (
          <Chip
            label="User Management"
            size="small"
            sx={{ mr: 2, bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }}
          />
        )}
        {location.pathname === '/admin/validators' && (
          <Chip
            label="Validator Config"
            size="small"
            sx={{ mr: 2, bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }}
          />
        )}

        {/* User Info */}
        {user && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" sx={{ mr: 1 }}>
              {user.full_name || user.username}
            </Typography>
            {isAdmin && (
              <Chip
                label="Admin"
                size="small"
                color="warning"
                sx={{ fontWeight: 600 }}
              />
            )}
          </Box>
        )}

        {/* Admin Menu Button (if admin) */}
        {isAdmin && (
          <>
            <IconButton
              color="inherit"
              onClick={handleMenuOpen}
              sx={{ ml: 2 }}
              title="Admin Settings"
            >
              <Settings />
            </IconButton>
            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleMenuClose}
              anchorOrigin={{
                vertical: 'bottom',
                horizontal: 'right',
              }}
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
            >
              <MenuItem onClick={() => { navigate('/admin/users'); handleMenuClose(); }}>
                <SupervisorAccount sx={{ mr: 1 }} fontSize="small" />
                User Management
              </MenuItem>
              <MenuItem onClick={() => { navigate('/admin/validators'); handleMenuClose(); }}>
                <Settings sx={{ mr: 1 }} fontSize="small" />
                Validator Config
              </MenuItem>
            </Menu>
          </>
        )}

        {/* Logout Button */}
        <IconButton
          color="inherit"
          onClick={handleLogout}
          sx={{ ml: 2 }}
          title="Logout"
        >
          <ExitToApp />
        </IconButton>
      </Toolbar>
    </AppBar>
  );
}

function App() {
  useEffect(() => {
    setupAxiosInterceptor();
  }, []);

  return (
    <Router>
      <Box sx={{ minHeight: '100vh', bgcolor: '#f5f5f5' }}>
        <Navigation />
        <Routes>
          {/* Login Route */}
          <Route
            path="/login"
            element={
              isAuthenticated() ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <Login />
              )
            }
          />

          {/* Dashboard Route */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          {/* Admin Routes */}
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute requireAdmin>
                <AdminUsers />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/validators"
            element={
              <ProtectedRoute requireAdmin>
                <AdminValidators />
              </ProtectedRoute>
            }
          />

          {/* Default Route */}
          <Route
            path="/"
            element={
              isAuthenticated() ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          {/* 404 - Redirect to Dashboard or Login */}
          <Route
            path="*"
            element={
              isAuthenticated() ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
        </Routes>
      </Box>
    </Router>
  );
}

export default App;
