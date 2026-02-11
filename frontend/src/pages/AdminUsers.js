import React, { useState, useEffect } from 'react';
import {
  Container, Paper, Typography, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, IconButton, Chip, Box,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  Select, MenuItem, FormControl, InputLabel, Switch, FormControlLabel,
  Alert, Snackbar
} from '@mui/material';
import { Add, Edit, Delete, Lock } from '@mui/icons-material';
import axios from 'axios';

const AdminUsers = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [validators, setValidators] = useState([]);

  // Form state
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    role_name: 'user',
    is_active: true,
    assigned_validator: ''
  });

  useEffect(() => {
    fetchUsers();
    fetchValidators();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axios.get('/api/v1/users');
      setUsers(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching users:', error);
      showSnackbar('Error loading users', 'error');
      setLoading(false);
    }
  };


  const fetchValidators = async () => {
    try {
      const response = await axios.get('/api/v1/admin/validators');
      const validatorList = response.data.validators || [];
      const activeValidators = validatorList
        .filter((validator) => validator.enabled)
        .map((validator) => ({
          value: validator.validator_type === 'osm_nominatim' ? 'openstreetmap' : validator.validator_type,
          label: validator.validator_type === 'osm_nominatim'
            ? 'OpenStreetMap'
            : validator.validator_type.replace(/_/g, ' ').toUpperCase()
        }));
      const hasOpenAI = activeValidators.some(
          (v) => v.value === 'openai'
        );

        if (!hasOpenAI) {
          activeValidators.push({
            value: 'openai',
            label: 'OpenAI'
          });
        }

      setValidators(activeValidators);
    } catch (error) {
      console.error('Error fetching validators:', error);
      setValidators([
        { value: 'openstreetmap', label: 'OpenStreetMap' },
        { value: 'openai', label: 'OPENAI' }
      ]);
    }
  };

  const handleOpenDialog = (user = null) => {
    if (user) {
      // Edit mode
      setEditingUser(user);
      setFormData({
        username: user.username,
        email: user.email || '',
        password: '',
        full_name: user.full_name || '',
        role_name: user.role,
        is_active: user.is_active,
        assigned_validator: user.assigned_validator || ''
      });
    } else {
      // Create mode
      setEditingUser(null);
      setFormData({
        username: '',
        email: '',
        password: '',
        full_name: '',
        role_name: 'user',
        is_active: true,
        assigned_validator: ''
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingUser(null);
    setFormData({
      username: '',
      email: '',
      password: '',
      full_name: '',
      role_name: 'user',
      is_active: true,
      assigned_validator: ''
    });
  };

  const handleSubmit = async () => {
    try {
      if (editingUser) {
        // Update user
        await axios.patch(`/api/v1/users/${editingUser.user_id}`, {
          email: formData.email,
          full_name: formData.full_name,
          role_name: formData.role_name,
          is_active: formData.is_active,
          assigned_validator: formData.assigned_validator || null
        });
        showSnackbar('User updated successfully', 'success');
      } else {
        // Create user
        await axios.post('/api/v1/users', formData);
        showSnackbar('User created successfully', 'success');
      }
      fetchUsers();
      handleCloseDialog();
    } catch (error) {
      console.error('Error saving user:', error);
      showSnackbar(error.response?.data?.detail || 'Error saving user', 'error');
    }
  };

  const handleDelete = async (userId, username) => {
    if (!window.confirm(`Are you sure you want to delete user "${username}"?`)) {
      return;
    }

    try {
      await axios.delete(`/api/v1/users/${userId}`);
      showSnackbar('User deleted successfully', 'success');
      fetchUsers();
    } catch (error) {
      console.error('Error deleting user:', error);
      showSnackbar(error.response?.data?.detail || 'Error deleting user', 'error');
    }
  };

  const handleResetPassword = async (userId, username) => {
    const newPassword = prompt(`Enter new password for "${username}":`);
    if (!newPassword) return;

    try {
      await axios.post(`/api/v1/users/${userId}/reset-password`, null, {
        params: { new_password: newPassword }
      });
      showSnackbar('Password reset successfully', 'success');
    } catch (error) {
      console.error('Error resetting password:', error);
      showSnackbar(error.response?.data?.detail || 'Error resetting password', 'error');
    }
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const getRoleColor = (role) => {
    return role === 'admin' ? 'error' : 'default';
  };

  if (loading) {
    return (
      <Container sx={{ mt: 4 }}>
        <Typography>Loading users...</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h5">User Management</Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => handleOpenDialog()}
          >
            Add User
          </Button>
        </Box>

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Username</TableCell>
                <TableCell>Full Name</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Assigned Validator</TableCell>
                <TableCell>Last Login</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.user_id}>
                  <TableCell>
                    <strong>{user.username}</strong>
                  </TableCell>
                  <TableCell>{user.full_name || '-'}</TableCell>
                  <TableCell>{user.email || '-'}</TableCell>
                  <TableCell>
                    <Chip
                      label={user.role.toUpperCase()}
                      color={getRoleColor(user.role)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={user.is_active ? 'Active' : 'Inactive'}
                      color={user.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{user.assigned_validator || '-'}</TableCell>
                  <TableCell>
                    {user.last_login
                      ? new Date(user.last_login).toLocaleString()
                      : 'Never'}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(user)}
                      title="Edit user"
                    >
                      <Edit fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleResetPassword(user.user_id, user.username)}
                      title="Reset password"
                    >
                      <Lock fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(user.user_id, user.username)}
                      title="Delete user"
                      disabled={user.username === 'admin'}
                    >
                      <Delete fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingUser ? 'Edit User' : 'Add New User'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Username"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              fullWidth
              required
              disabled={!!editingUser}
            />

            <TextField
              label="Email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              fullWidth
            />

            {!editingUser && (
              <TextField
                label="Password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                fullWidth
                required
              />
            )}

            <TextField
              label="Full Name"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              fullWidth
            />

            <FormControl fullWidth>
              <InputLabel>Role</InputLabel>
              <Select
                value={formData.role_name}
                label="Role"
                onChange={(e) => setFormData({ ...formData, role_name: e.target.value })}
              >
                <MenuItem value="user">User</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
              </Select>
            </FormControl>


            <FormControl fullWidth>
              <InputLabel>Assigned Validator</InputLabel>
              <Select
                value={formData.assigned_validator}
                label="Assigned Validator"
                onChange={(e) => setFormData({ ...formData, assigned_validator: e.target.value })}
              >
                <MenuItem value="">All Validators</MenuItem>
                {validators.map((validator) => (
                  <MenuItem key={validator.value} value={validator.value}>
                    {validator.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControlLabel
              control={
                <Switch
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
              }
              label="Active"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            disabled={!formData.username || (!editingUser && !formData.password)}
          >
            {editingUser ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default AdminUsers;
