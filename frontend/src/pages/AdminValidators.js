import React, { useState, useEffect } from 'react';
import {
  Container, Paper, Typography, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, IconButton, Chip, Box,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  Select, MenuItem, FormControl, InputLabel, Switch, FormControlLabel,
  Alert, Snackbar, Grid
} from '@mui/material';
import { Add, Edit, Delete, Visibility, VisibilityOff } from '@mui/icons-material';
import axios from 'axios';

const AdminValidators = () => {
  const [validators, setValidators] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingValidator, setEditingValidator] = useState(null);
  const [showApiKey, setShowApiKey] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [validatorTypes, setValidatorTypes] = useState([]);
  const [roles, setRoles] = useState([]);
  const [selectedRole, setSelectedRole] = useState("");



  // Form state
  const [formData, setFormData] = useState({
    validator_type: 'custom',
    display_name: '',
    enabled: true,
    priority: 1,
    api_endpoint: '',
    api_key: '',
    rate_limit: 1,
    timeout_seconds: 10,
    max_retries: 3,
    cost_per_1000: 0,
    monthly_quota: null
  });

  useEffect(() => {
    fetchValidators();
  }, []);

  const fetchValidators = async () => {
    try {
      const response = await axios.get('/api/v1/validators');
      const data = response.data;
      setValidators(data);

      // derive validator types dynamically
      const uniqueTypes = [...new Set(data.map(v => v.validator_type))];
      setValidatorTypes(uniqueTypes);
      setLoading(false);

    } catch (error) {
      console.error('Error fetching validators:', error);
      showSnackbar('Error loading validators', 'error');
      setLoading(false);
    }
  };

  const handleOpenDialog = (validator = null) => {
    if (validator) {
      // Edit mode
      setEditingValidator(validator);
      setFormData({
        validator_type: validator.validator_type,
        display_name: validator.display_name,
        enabled: validator.enabled,
        priority: validator.priority,
        api_endpoint: validator.api_endpoint || '',
        api_key: '',
        rate_limit: validator.rate_limit,
        timeout_seconds: validator.timeout_seconds,
        max_retries: validator.max_retries,
        cost_per_1000: validator.cost_per_1000,
        monthly_quota: validator.monthly_quota
      });
    } else {
      // Create mode
      setEditingValidator(null);
      setFormData({
        validator_type: 'custom',
        display_name: '',
        enabled: true,
        priority: 1,
        api_endpoint: '',
        api_key: '',
        rate_limit: 1,
        timeout_seconds: 10,
        max_retries: 3,
        cost_per_1000: 0,
        monthly_quota: null
      });
    }
    setShowApiKey(false);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingValidator(null);
    setShowApiKey(false);
  };

  const handleSubmit = async () => {
    try {
      if (editingValidator) {
        // Update validator
        const updateData = { ...formData };
        if (!updateData.api_key) {
          delete updateData.api_key;
        }
        await axios.patch(`/api/v1/validators/${editingValidator.config_id}`, updateData);
        showSnackbar('Validator updated successfully', 'success');
      } else {
        // Create validator
        await axios.post('/api/v1/validators', formData);
        showSnackbar('Validator created successfully', 'success');
      }
      fetchValidators();
      handleCloseDialog();
    } catch (error) {
      console.error('Error saving validator:', error);
      showSnackbar(error.response?.data?.detail || 'Error saving validator', 'error');
    }
  };

  const handleDelete = async (configId, displayName) => {
    if (!window.confirm(`Are you sure you want to delete validator "${displayName}"?`)) {
      return;
    }

    try {
      await axios.delete(`/api/v1/validators/${configId}`);
      showSnackbar('Validator deleted successfully', 'success');
      fetchValidators();
    } catch (error) {
      console.error('Error deleting validator:', error);
      showSnackbar(error.response?.data?.detail || 'Error deleting validator', 'error');
    }
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  if (loading) {
    return (
      <Container sx={{ mt: 4 }}>
        <Typography>Loading validators...</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography variant="h5">Validator Configuration</Typography>
            <Typography variant="body2" color="textSecondary">
              Configure validation models that appear in the dropdown
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => handleOpenDialog()}
          >
            Add Validator
          </Button>
        </Box>

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Display Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Priority</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>API Key</TableCell>
                <TableCell>Rate Limit</TableCell>
                <TableCell>Cost/1K</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {validators.map((validator) => (
                <TableRow key={validator.config_id}>
                  <TableCell>
                    <strong>{validator.display_name}</strong>
                  </TableCell>
                  <TableCell>
                    <Chip label={validator.validator_type} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>{validator.priority}</TableCell>
                  <TableCell>
                    <Chip
                      label={validator.enabled ? 'Enabled' : 'Disabled'}
                      color={validator.enabled ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {validator.has_api_key ? (
                      <Chip label="Configured" color="primary" size="small" />
                    ) : (
                      <Chip label="None" size="small" />
                    )}
                  </TableCell>
                  <TableCell>{validator.rate_limit}/sec</TableCell>
                  <TableCell>${validator.cost_per_1000}</TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(validator)}
                      title="Edit validator"
                    >
                      <Edit fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(validator.config_id, validator.display_name)}
                      title="Delete validator"
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
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingValidator ? 'Edit Validator' : 'Add New Validator'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={8}>
                <TextField
                  label="Display Name"
                  value={formData.display_name}
                  onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                  fullWidth
                  required
                  helperText="Name shown in dropdown (e.g., 'My Custom Validator')"
                />
              </Grid>

              <Grid item xs={12} sm={4}>
                <FormControl fullWidth>
                  <InputLabel>Validator Type</InputLabel>
                  <Select
                    value={formData.validator_type}
                    label="Validator Type"
                    onChange={(e) => setFormData({ ...formData, validator_type: e.target.value })}
                  >
                    {validatorTypes.map((type) => (
                    <MenuItem key={type} value={type}>
                      {type}
                    </MenuItem>
                  ))}

                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <TextField
                  label="API Endpoint"
                  value={formData.api_endpoint}
                  onChange={(e) => setFormData({ ...formData, api_endpoint: e.target.value })}
                  fullWidth
                  placeholder="https://api.example.com/validate"
                />
              </Grid>

              <Grid item xs={12}>
                <TextField
                  label="API Key"
                  type={showApiKey ? 'text' : 'password'}
                  value={formData.api_key}
                  onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                  fullWidth
                  placeholder={editingValidator ? "Leave empty to keep existing key" : "Enter API key if required"}
                  InputProps={{
                    endAdornment: (
                      <IconButton
                        onClick={() => setShowApiKey(!showApiKey)}
                        edge="end"
                      >
                        {showApiKey ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    ),
                  }}
                />
              </Grid>

              <Grid item xs={12} sm={3}>
                <TextField
                  label="Priority"
                  type="number"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                  fullWidth
                  helperText="Lower = higher priority"
                />
              </Grid>

              <Grid item xs={12} sm={3}>
                <TextField
                  label="Rate Limit"
                  type="number"
                  value={formData.rate_limit}
                  onChange={(e) => setFormData({ ...formData, rate_limit: parseInt(e.target.value) })}
                  fullWidth
                  helperText="Requests/second"
                />
              </Grid>

              <Grid item xs={12} sm={3}>
                <TextField
                  label="Timeout"
                  type="number"
                  value={formData.timeout_seconds}
                  onChange={(e) => setFormData({ ...formData, timeout_seconds: parseInt(e.target.value) })}
                  fullWidth
                  helperText="Seconds"
                />
              </Grid>

              <Grid item xs={12} sm={3}>
                <TextField
                  label="Max Retries"
                  type="number"
                  value={formData.max_retries}
                  onChange={(e) => setFormData({ ...formData, max_retries: parseInt(e.target.value) })}
                  fullWidth
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  label="Cost per 1000 Requests"
                  type="number"
                  value={formData.cost_per_1000}
                  onChange={(e) => setFormData({ ...formData, cost_per_1000: parseFloat(e.target.value) })}
                  fullWidth
                  InputProps={{
                    startAdornment: '$',
                  }}
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  label="Monthly Quota"
                  type="number"
                  value={formData.monthly_quota || ''}
                  onChange={(e) => setFormData({ ...formData, monthly_quota: e.target.value ? parseInt(e.target.value) : null })}
                  fullWidth
                  placeholder="Optional"
                />
              </Grid>

              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.enabled}
                      onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                    />
                  }
                  label="Enabled (show in dropdown)"
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            disabled={!formData.display_name}
          >
            {editingValidator ? 'Update' : 'Create'}
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

export default AdminValidators;
