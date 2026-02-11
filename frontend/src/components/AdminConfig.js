import React, { useState, useEffect } from 'react';
import {
  Box, Paper, Typography, TextField, Button, Switch, FormControlLabel,
  Grid, Divider, Alert, Snackbar, Chip, Card, CardContent, Tab, Tabs,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Dialog, DialogTitle, DialogContent, DialogActions, CircularProgress
} from '@mui/material';
import { Settings, CheckCircle, Error as ErrorIcon, Warning, Info } from '@mui/icons-material';
import axios from 'axios';

const AdminConfig = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  
  // Validators state
  const [validators, setValidators] = useState([]);
  
  // Configuration state
  const [config, setConfig] = useState({
    openai_api_key: '',
    auto_approve_threshold: 90,
    manual_review_threshold: 70,
    enable_chatgpt_enhancement: false,
    chatgpt_enhancement_threshold: 90
  });
  
  // Test results
  const [testResults, setTestResults] = useState({});
  const [costEstimate, setCostEstimate] = useState(null);
  
  useEffect(() => {
    loadValidators();
    loadThresholds();
  }, []);
  
  const loadValidators = async () => {
    try {
      const response = await axios.get('/api/v1/admin/validators');
      setValidators(response.data.validators || []);
    } catch (error) {
      showSnackbar('Error loading validators', 'error');
    }
  };
  
  const loadThresholds = async () => {
    try {
      const response = await axios.get('/api/v1/admin/thresholds');
      setConfig(prev => ({
        ...prev,
        ...response.data
      }));
    } catch (error) {
      showSnackbar('Error loading thresholds', 'error');
    }
  };
  
  const showSnackbar = (message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
  };
  
  const handleSaveOpenAI = async () => {
    if (!config.openai_api_key) {
      showSnackbar('Please enter an API key', 'error');
      return;
    }
    
    setLoading(true);
    try {
      // Create or update ChatGPT validator
      await axios.post('/api/v1/admin/validators', {
        validator_type: 'chatgpt_gpt4',
        enabled: config.enable_chatgpt_enhancement,
        api_key: config.openai_api_key,
        priority: 2,  // Secondary validator (after OSM)
        rate_limit: 60  // 60 requests per minute
      });
      
      showSnackbar('OpenAI API key saved successfully!', 'success');
      loadValidators();
    } catch (error) {
      showSnackbar('Error saving API key: ' + (error.response?.data?.detail || error.message), 'error');
    }
    setLoading(false);
  };
  
  const handleTestConnection = async (validatorType) => {
    setLoading(true);
    try {
      const response = await axios.post('/api/v1/admin/validators/test', null, {
        params: {
          validator_type: validatorType,
          api_key: validatorType === 'chatgpt_gpt4' ? config.openai_api_key : undefined
        }
      });
      
      setTestResults(prev => ({
        ...prev,
        [validatorType]: response.data
      }));
      
      showSnackbar(
        `${validatorType}: ${response.data.message}`,
        response.data.status === 'healthy' ? 'success' : 'error'
      );
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        [validatorType]: { status: 'error', message: error.response?.data?.detail || error.message }
      }));
      showSnackbar('Connection test failed', 'error');
    }
    setLoading(false);
  };
  
  const handleToggleValidator = async (validatorType, enabled) => {
    try {
      await axios.put(`/api/v1/admin/validators/${validatorType}/toggle`, null, {
        params: { enabled }
      });
      showSnackbar(`${validatorType} ${enabled ? 'enabled' : 'disabled'}`, 'success');
      loadValidators();
    } catch (error) {
      showSnackbar('Error toggling validator', 'error');
    }
  };
  
  const handleSaveThresholds = async () => {
    setLoading(true);
    try {
      await axios.put('/api/v1/admin/thresholds', {
        auto_approve_threshold: parseFloat(config.auto_approve_threshold),
        manual_review_threshold: parseFloat(config.manual_review_threshold),
        enable_chatgpt_enhancement: config.enable_chatgpt_enhancement,
        chatgpt_enhancement_threshold: parseFloat(config.chatgpt_enhancement_threshold)
      });
      
      showSnackbar('Thresholds updated successfully!', 'success');
    } catch (error) {
      showSnackbar('Error saving thresholds: ' + (error.response?.data?.detail || error.message), 'error');
    }
    setLoading(false);
  };
  
  const handleEstimateCost = async () => {
    try {
      const response = await axios.get('/api/v1/admin/cost-estimate', {
        params: {
          num_addresses: 1000,
          use_chatgpt: config.enable_chatgpt_enhancement,
          chatgpt_percentage: 30  // Assume 30% need enhancement
        }
      });
      setCostEstimate(response.data);
    } catch (error) {
      showSnackbar('Error calculating cost estimate', 'error');
    }
  };
  
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        <Settings sx={{ mr: 1, verticalAlign: 'middle' }} />
        Admin Configuration
      </Typography>
      
      <Paper sx={{ mt: 3 }}>
        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
          <Tab label="API Configuration" />
          <Tab label="Validation Thresholds" />
          <Tab label="Validators Status" />
          <Tab label="Cost Estimate" />
        </Tabs>
        
        {/* Tab 1: API Configuration */}
        {activeTab === 0 && (
          <Box sx={{ p: 3 }}>
            <Alert severity="info" sx={{ mb: 3 }}>
              Configure your OpenAI API key to enable ChatGPT enhancement for low-confidence addresses.
              This will boost accuracy by 15-25% for problematic records.
            </Alert>
            
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      OpenAI API Configuration
                    </Typography>
                    
                    <TextField
                      fullWidth
                      label="OpenAI API Key"
                      type="password"
                      value={config.openai_api_key}
                      onChange={(e) => setConfig({...config, openai_api_key: e.target.value})}
                      placeholder="sk-..."
                      helperText="Get your API key from: https://platform.openai.com/api-keys"
                      sx={{ mb: 2 }}
                    />
                    
                    <FormControlLabel
                      control={
                        <Switch
                          checked={config.enable_chatgpt_enhancement}
                          onChange={(e) => setConfig({...config, enable_chatgpt_enhancement: e.target.checked})}
                        />
                      }
                      label="Enable ChatGPT Enhancement"
                    />
                    
                    <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
                      <Button
                        variant="contained"
                        onClick={handleSaveOpenAI}
                        disabled={loading}
                      >
                        {loading ? <CircularProgress size={24} /> : 'Save API Key'}
                      </Button>
                      
                      <Button
                        variant="outlined"
                        onClick={() => handleTestConnection('chatgpt_gpt4')}
                        disabled={!config.openai_api_key || loading}
                      >
                        Test Connection
                      </Button>
                    </Box>
                    
                    {testResults.chatgpt_gpt4 && (
                      <Alert 
                        severity={testResults.chatgpt_gpt4.status === 'healthy' ? 'success' : 'error'}
                        sx={{ mt: 2 }}
                      >
                        {testResults.chatgpt_gpt4.message}
                      </Alert>
                    )}
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12}>
                <Alert severity="warning">
                  <strong>Cost Information:</strong> ChatGPT uses GPT-4 which costs approximately $0.024 per address.
                  It will only be used for addresses below the enhancement threshold (typically 10-30% of records).
                </Alert>
              </Grid>
            </Grid>
          </Box>
        )}
        
        {/* Tab 2: Validation Thresholds */}
        {activeTab === 1 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Confidence Thresholds
            </Typography>
            
            <Alert severity="info" sx={{ mb: 3 }}>
              These thresholds determine which records are auto-approved, need review, or get enhanced with ChatGPT.
            </Alert>
            
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Auto-Approve Threshold (%)"
                  value={config.auto_approve_threshold}
                  onChange={(e) => setConfig({...config, auto_approve_threshold: e.target.value})}
                  inputProps={{ min: 0, max: 100, step: 1 }}
                  helperText="Records with ≥ this confidence are automatically approved"
                />
              </Grid>
              
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Manual Review Threshold (%)"
                  value={config.manual_review_threshold}
                  onChange={(e) => setConfig({...config, manual_review_threshold: e.target.value})}
                  inputProps={{ min: 0, max: 100, step: 1 }}
                  helperText="Records below this confidence need manual review"
                />
              </Grid>
              
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="ChatGPT Enhancement Threshold (%)"
                  value={config.chatgpt_enhancement_threshold}
                  onChange={(e) => setConfig({...config, chatgpt_enhancement_threshold: e.target.value})}
                  inputProps={{ min: 0, max: 100, step: 1 }}
                  helperText="Records below this will be enhanced with ChatGPT"
                  disabled={!config.enable_chatgpt_enhancement}
                />
              </Grid>
              
              <Grid item xs={12}>
                <Button
                  variant="contained"
                  onClick={handleSaveThresholds}
                  disabled={loading}
                >
                  {loading ? <CircularProgress size={24} /> : 'Save Thresholds'}
                </Button>
              </Grid>
              
              <Grid item xs={12}>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" gutterBottom>
                  Validation Flow:
                </Typography>
                <Box sx={{ pl: 2 }}>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    1. <strong>OpenStreetMap</strong> validates all addresses (FREE)
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    2. If confidence &lt; {config.chatgpt_enhancement_threshold}% and ChatGPT enabled → <strong>ChatGPT Enhancement</strong> (PAID)
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    3. If final confidence ≥ {config.auto_approve_threshold}% → <strong>AUTO APPROVED</strong>
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    4. If final confidence &lt; {config.manual_review_threshold}% → <strong>MANUAL REVIEW</strong>
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Box>
        )}
        
        {/* Tab 3: Validators Status */}
        {activeTab === 2 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Active Validators
            </Typography>
            
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Validator</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Priority</TableCell>
                    <TableCell>Cost</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {validators.map((validator) => (
                    <TableRow key={validator.config_id}>
                      <TableCell>
                        <Typography variant="body1">
                          {validator.validator_type.replace('_', ' ').toUpperCase()}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {validator.enabled ? (
                          <Chip label="Enabled" color="success" size="small" icon={<CheckCircle />} />
                        ) : (
                          <Chip label="Disabled" size="small" />
                        )}
                      </TableCell>
                      <TableCell>{validator.priority}</TableCell>
                      <TableCell>
                        {validator.cost_per_1000 > 0 
                          ? `$${validator.cost_per_1000.toFixed(2)}/1000`
                          : 'FREE'
                        }
                      </TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          onClick={() => handleTestConnection(validator.validator_type)}
                        >
                          Test
                        </Button>
                        <Switch
                          checked={validator.enabled}
                          onChange={(e) => handleToggleValidator(validator.validator_type, e.target.checked)}
                          size="small"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}
        
        {/* Tab 4: Cost Estimate */}
        {activeTab === 3 && (
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Cost Estimate Calculator
            </Typography>
            
            <Button variant="contained" onClick={handleEstimateCost} sx={{ mb: 3 }}>
              Calculate Cost for 1,000 Addresses
            </Button>
            
            {costEstimate && (
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" gutterBottom>
                        OpenStreetMap Nominatim
                      </Typography>
                      <Typography variant="h4" color="success.main">
                        FREE
                      </Typography>
                      <Typography variant="body2">
                        {costEstimate.breakdown.osm_nominatim.addresses} addresses
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardContent>
                      <Typography color="textSecondary" gutterBottom>
                        ChatGPT GPT-4 Enhancement
                      </Typography>
                      <Typography variant="h4" color="primary.main">
                        ${costEstimate.breakdown.chatgpt_gpt4.cost_usd.toFixed(2)}
                      </Typography>
                      <Typography variant="body2">
                        {costEstimate.breakdown.chatgpt_gpt4.addresses} addresses ({costEstimate.breakdown.chatgpt_gpt4.percentage_enhanced}%)
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid item xs={12}>
                  <Alert severity="info">
                    <strong>Total Cost:</strong> ${costEstimate.total_cost_usd} for {costEstimate.num_addresses} addresses
                    <br />
                    <strong>Per Address:</strong> ${costEstimate.cost_per_address}
                  </Alert>
                </Grid>
              </Grid>
            )}
          </Box>
        )}
      </Paper>
      
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({...snackbar, open: false})}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({...snackbar, open: false})}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default AdminConfig;
