import React, { useState } from 'react';
import {
  Container, Paper, TextField, Button, Typography, Box, Alert,
  InputAdornment, IconButton, Grid
} from '@mui/material';
import { Visibility, VisibilityOff, Lock, Person, CheckCircle, Speed, Security } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await axios.post('/api/v1/auth/login', {
        username,
        password
      });

      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`;

      navigate('/dashboard');
    } catch (err) {
      console.error('Login error:', err);
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2
      }}
    >
      <Container maxWidth="lg">
        <Paper
          elevation={24}
          sx={{
            borderRadius: 4,
            overflow: 'hidden',
            background: '#fff'
          }}
        >
          <Grid container>
            {/* Left Side - Branding (2/3) */}
            <Grid
              item
              xs={12}
              md={8}
              sx={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                p: 6,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center'
              }}
            >
              <Typography
                variant="h2"
                sx={{
                  fontWeight: 800,
                  mb: 2,
                  fontSize: { xs: '2.5rem', md: '3.5rem' }
                }}
              >
                AddrAI
              </Typography>
              
              <Typography
                variant="h5"
                sx={{
                  mb: 4,
                  opacity: 0.95,
                  fontWeight: 300
                }}
              >
                AI-Powered Address Validation Platform
              </Typography>

              <Typography variant="body1" sx={{ mb: 4, opacity: 0.9, fontSize: '1.1rem' }}>
                Transform your Address data with intelligent address validation,
                geocoding, and Oracle Fusion integration.
              </Typography>

              <Box sx={{ mt: 4 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <CheckCircle sx={{ mr: 2, fontSize: 28 }} />
                  <Typography variant="body1">
                    Automated address standardization & validation
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Speed sx={{ mr: 2, fontSize: 28 }} />
                  <Typography variant="body1">
                    Real-time geocoding with OpenStreetMap
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Security sx={{ mr: 2, fontSize: 28 }} />
                  <Typography variant="body1">
                    Oracle Fusion ready format with USPS standards
                  </Typography>
                </Box>
              </Box>

              <Box sx={{ mt: 6, p: 3, background: 'rgba(255,255,255,0.1)', borderRadius: 2 }}>
                <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
                  Data Quality Journey
                </Typography>
                <Typography variant="body2" sx={{ opacity: 0.9 }}>
                  Original Data → OSM Validation → Oracle Transformation → Export
                </Typography>
                <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
                  <Box>
                    <Typography variant="h4" sx={{ fontWeight: 700 }}>95%+</Typography>
                    <Typography variant="caption">Validation Rate</Typography>
                  </Box>
                  <Box>
                    <Typography variant="h4" sx={{ fontWeight: 700 }}>100%</Typography>
                    <Typography variant="caption">USPS Standard</Typography>
                  </Box>
                  <Box>
                    <Typography variant="h4" sx={{ fontWeight: 700 }}>5000+</Typography>
                    <Typography variant="caption">Records/Hour</Typography>
                  </Box>
                </Box>
              </Box>
            </Grid>

            {/* Right Side - Login Form (1/3) */}
            <Grid
              item
              xs={12}
              md={4}
              sx={{
                p: 6,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                minHeight: { xs: 'auto', md: '600px' }
              }}
            >
              <Box sx={{ textAlign: 'center', mb: 4 }}>
                <Typography variant="h4" gutterBottom sx={{ fontWeight: 700, color: '#667eea' }}>
                  Welcome Back
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Sign in to continue to AddrAI
                </Typography>
              </Box>

              {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  {error}
                </Alert>
              )}

              <form onSubmit={handleSubmit}>
                <TextField
                  fullWidth
                  label="Username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  margin="normal"
                  required
                  autoFocus
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Person color="action" />
                      </InputAdornment>
                    ),
                  }}
                  sx={{ mb: 2 }}
                />

                <TextField
                  fullWidth
                  label="Password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  margin="normal"
                  required
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Lock color="action" />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowPassword(!showPassword)}
                          edge="end"
                        >
                          {showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={{ mb: 3 }}
                />

                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  size="large"
                  disabled={loading}
                  sx={{
                    py: 1.5,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    '&:hover': {
                      background: 'linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%)',
                    }
                  }}
                >
                  {loading ? 'Signing in...' : 'Sign In'}
                </Button>
              </form>

              <Box sx={{ mt: 4, textAlign: 'center' }}>
                <Typography variant="caption" color="textSecondary">
                  © 2024 AddrAI. All rights reserved.
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Paper>
      </Container>
    </Box>
  );
};

export default Login;
