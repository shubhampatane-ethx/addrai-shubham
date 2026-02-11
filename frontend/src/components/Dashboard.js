import React, { useState, useEffect } from 'react';
import {
  Container, Paper, Button, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, LinearProgress, Chip, Box, Typography, Grid, Card,
  CardContent, FormControl, InputLabel, Select, MenuItem, IconButton,
  TextField, Dialog, DialogTitle, DialogContent, DialogActions, Checkbox,
  Toolbar
} from '@mui/material';
import {
  CloudUpload, Refresh, Visibility, GetApp, CheckCircle, Error as ErrorIcon,
  Warning, Edit, Save, Cancel, Description, Assessment, TrendingUp, Speed,
  VerifiedUser, DataUsage, Delete, DeleteOutline, PlayArrow
} from '@mui/icons-material';
import axios from 'axios';
import ResultsDialog from './ResultsDialog';


const formatETA = (seconds) => {
  if (!seconds || seconds <= 0) return "—";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.ceil(seconds / 60)} min`;
  return `${(seconds / 3600).toFixed(1)} hr`;
};



const Dashboard = () => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedValidator, setSelectedValidator] = useState('openstreetmap');
  const [resultsDialogOpen, setResultsDialogOpen] = useState(false);
  const [openaiPrompt, setOpenaiPrompt] = useState('');
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [editingJob, setEditingJob] = useState(null);
  const [editedName, setEditedName] = useState('');
  const [editedTags, setEditedTags] = useState('');
  
  // NEW: Checkbox selection state
  const [selectedJobs, setSelectedJobs] = useState([]);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  
  // Dynamic validators
  const [validators, setValidators] = useState([]);
  
  // Overall metrics
  const [metrics, setMetrics] = useState({
    totalJobs: 0,
    totalRecords: 0,
    completedJobs: 0,
    validationRate: 0,
    highConfidence: 0,
    averageProgress: 0
  });

  useEffect(() => {
    fetchJobs();
    fetchValidators();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchJobs = async () => {
    try {
      const response = await axios.get('/api/v1/jobs');
      const jobsList = response.data.jobs || [];
      setJobs(jobsList);
      calculateMetrics(jobsList);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching jobs:', error);
      setLoading(false);
    }
  };

  const calculateMetrics = (jobsList) => {
    const totalJobs = jobsList.length;
    const completedJobs = jobsList.filter(j => j.status === 'COMPLETED').length;
    const totalRecords = jobsList.reduce((sum, j) => sum + (j.total_records || 0), 0);
    const processedRecords = jobsList.reduce((sum, j) => sum + (j.processed_records || 0), 0);
    const highConfidence = jobsList.reduce((sum, j) => sum + (j.high_confidence || 0), 0);
    const validationRate = totalRecords > 0 ? ((processedRecords / totalRecords) * 100).toFixed(1) : 0;
    const averageProgress = totalJobs > 0 
      ? (jobsList.reduce((sum, j) => sum + (j.progress_percentage || 0), 0) / totalJobs).toFixed(1)
      : 0;

    setMetrics({
      totalJobs,
      totalRecords,
      completedJobs,
      validationRate: parseFloat(validationRate),
      highConfidence,
      averageProgress: parseFloat(averageProgress)
    });
  };

  const fetchValidators = async () => {
    try {
      const response = await axios.get('/api/v1/validators/active');
      const validatorList = response.data.validators || [];
      
      const mappedValidators = validatorList.map(v => ({
        ...v,
        mappedValue: v.value === 'osm_nominatim' ? 'openstreetmap' : v.value
      }));
      
      setValidators(mappedValidators);
      
      if (mappedValidators.length > 0) {
        setSelectedValidator(mappedValidators[0].mappedValue);
      }
    } catch (error) {
      console.error('Error fetching validators:', error);
      setValidators([
        {
          value: 'osm_nominatim',
          label: 'OpenStreetMap',
          cost_per_1000: 0,
          mappedValue: 'openstreetmap'
        },
        {
          value: 'openai',
          label: 'OpenAI (Prompted)',
          cost_per_1000: 0,
          mappedValue: 'openai'
        }
      ]);

      setSelectedValidator('openstreetmap');

    }
  };

  const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  setUploading(true);
  const formData = new FormData();
  formData.append('file', file);

  try {
    await axios.post('/api/v1/jobs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    fetchJobs();
  } catch (error) {
    console.error('Upload error:', error);
    alert('Upload failed: ' + (error.response?.data?.detail || error.message));
  } finally {
    setUploading(false);
    event.target.value = '';
  }
};


  const handleValidate = async (jobId) => {
    try {
      const validatorToSend =
        validators.find(v => v.mappedValue === selectedValidator)?.mappedValue
        || selectedValidator;

      await axios.post(`/api/v1/jobs/${jobId}/validate`, {
        validator_type: validatorToSend,
        prompt: validatorToSend === 'openai' ? openaiPrompt : ''
      });

      fetchJobs();
    } catch (error) {
      console.error('Validation error:', error);
      alert('Validation failed: ' + (error.response?.data?.detail || error.message));
    }
  };


  const handleViewResults = (jobId, jobName) => {
    setSelectedJobId(jobId);
    setResultsDialogOpen(true);
  };

  const handleExport = async (jobId) => {
    try {
      const response = await axios.get(`/api/v1/jobs/${jobId}/export?format=3stage`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `validation_results_${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export error:', error);
      alert('Export failed');
    }
  };

  const startEditJob = (job) => {
    setEditingJob(job.job_id);
    setEditedName(job.job_name);
    setEditedTags(job.client_name || '');
  };

  const saveEditJob = async (jobId) => {
    try {
      await axios.patch(`/api/v1/jobs/${jobId}`, {
        job_name: editedName,
        client_name: editedTags
      });
      setEditingJob(null);
      fetchJobs();
    } catch (error) {
      console.error('Update error:', error);
      alert('Update failed');
    }
  };

  const cancelEditJob = () => {
    setEditingJob(null);
    setEditedName('');
    setEditedTags('');
  };

  // NEW: Checkbox handlers
  const handleSelectAll = (event) => {
    if (event.target.checked) {
      setSelectedJobs(jobs.map(job => job.job_id));
    } else {
      setSelectedJobs([]);
    }
  };

  const handleSelectJob = (jobId) => {
    setSelectedJobs(prev => {
      if (prev.includes(jobId)) {
        return prev.filter(id => id !== jobId);
      } else {
        return [...prev, jobId];
      }
    });
  };

  // NEW: Delete handlers
  const handleDeleteClick = () => {
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    setDeleting(true);
    try {
      // Delete all selected jobs
      await Promise.all(
        selectedJobs.map(jobId => 
          axios.delete(`/api/v1/jobs/${jobId}`)
        )
      );
      
      // Clear selection
      setSelectedJobs([]);
      setDeleteConfirmOpen(false);
      
      // Refresh jobs list
      fetchJobs();
    } catch (error) {
      console.error('Delete error:', error);
      alert('Delete failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmOpen(false);
  };

  const getStatusChip = (status) => {
    const statusConfig = {
      'COMPLETED': { color: 'success', icon: <CheckCircle sx={{ fontSize: 16 }} /> },
      'PROCESSING': { color: 'info', icon: <Assessment sx={{ fontSize: 16 }} /> },
      'FAILED': { color: 'error', icon: <ErrorIcon sx={{ fontSize: 16 }} /> },
      'UPLOADED': { color: 'default', icon: <CloudUpload sx={{ fontSize: 16 }} /> },
      'QUEUED': { color: 'warning', icon: <Warning sx={{ fontSize: 16 }} /> }
    };

    const config = statusConfig[status] || { color: 'default', icon: null };
    
    return (
      <Chip
        icon={config.icon}
        label={status}
        color={config.color}
        size="small"
        sx={{ fontWeight: 600, minWidth: 100 }}
      />
    );
  };

  const isAllSelected = jobs.length > 0 && selectedJobs.length === jobs.length;
  const isSomeSelected = selectedJobs.length > 0 && selectedJobs.length < jobs.length;

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Dashboard
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Upload, validate, and export entity addresses
        </Typography>
      </Box>

      {/* Metrics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={2} sx={{ borderRadius: 2 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <DataUsage sx={{ color: '#3b82f6', mr: 1 }} />
                <Typography variant="body2" color="textSecondary">
                  Total Jobs
                </Typography>
              </Box>
              <Typography variant="h3" sx={{ fontWeight: 700, color: '#3b82f6' }}>
                {metrics.totalJobs}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                {metrics.completedJobs} completed
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={2} sx={{ borderRadius: 2 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Assessment sx={{ color: '#10b981', mr: 1 }} />
                <Typography variant="body2" color="textSecondary">
                  Total Records
                </Typography>
              </Box>
              <Typography variant="h3" sx={{ fontWeight: 700, color: '#10b981' }}>
                {metrics.totalRecords}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                {metrics.validationRate}% validated
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={2} sx={{ borderRadius: 2 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <VerifiedUser sx={{ color: '#f59e0b', mr: 1 }} />
                <Typography variant="body2" color="textSecondary">
                  High Confidence
                </Typography>
              </Box>
              <Typography variant="h3" sx={{ fontWeight: 700, color: '#f59e0b' }}>
                {metrics.highConfidence}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                quality validated
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card elevation={2} sx={{ borderRadius: 2 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Speed sx={{ color: '#ef4444', mr: 1 }} />
                <Typography variant="body2" color="textSecondary">
                  Avg Progress
                </Typography>
              </Box>
              <Typography variant="h3" sx={{ fontWeight: 700, color: '#ef4444' }}>
                {metrics.averageProgress}%
              </Typography>
              <Typography variant="caption" color="textSecondary">
                across all jobs
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Compact Actions Row */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Button
                variant="contained"
                component="label"
                disabled={uploading}
                sx={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  minWidth: 150
                }}
                startIcon={<CloudUpload />}
              >
                {uploading ? 'Uploading...' : 'Upload File'}
                <input
                  type="file"
                  hidden
                  accept=".xlsx,.xls,.csv"
                  onChange={handleFileUpload}
                />
              </Button>
              <Typography variant="body2" color="textSecondary">
                Excel or CSV files with entity addresses
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 2 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Validation Engine</InputLabel>
              <Select
                value={selectedValidator}
                label="Validation Engine"
                onChange={(e) => setSelectedValidator(e.target.value)}
              >
                {validators.map((validator) => (
                  <MenuItem key={validator.value} value={validator.mappedValue}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                      <Typography variant="body2">{validator.label}</Typography>
                      {validator.cost_per_1000 > 0 && (
                        <Typography variant="caption" color="textSecondary">
                          ${validator.cost_per_1000}/1K
                        </Typography>
                      )}
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Paper>
        </Grid>
      </Grid>

      {/* Jobs Table */}
      <Paper elevation={3} sx={{ borderRadius: 2 }}>
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Validation Jobs
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              {selectedJobs.length > 0 && (
                <Button
                  variant="contained"
                  color="error"
                  size="small"
                  startIcon={<Delete />}
                  onClick={handleDeleteClick}
                  sx={{ mr: 1 }}
                >
                  Delete ({selectedJobs.length})
                </Button>
              )}
              <IconButton onClick={fetchJobs} color="primary" size="small">
                <Refresh />
              </IconButton>
            </Box>
          </Box>
        </Box>

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow sx={{ bgcolor: 'grey.50' }}>
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={isSomeSelected}
                    checked={isAllSelected}
                    onChange={handleSelectAll}
                  />
                </TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Job Name</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Tags</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Records</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Progress</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Quality</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600 }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobs.map((job) => (
                <TableRow
                  key={job.job_id}
                  sx={{
                    '&:hover': { bgcolor: 'grey.50' },
                    transition: 'background-color 0.2s',
                    bgcolor: selectedJobs.includes(job.job_id) ? 'action.selected' : 'transparent'
                  }}
                >
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selectedJobs.includes(job.job_id)}
                      onChange={() => handleSelectJob(job.job_id)}
                    />
                  </TableCell>
                  
                  <TableCell>
                    {editingJob === job.job_id ? (
                      <TextField
                        size="small"
                        value={editedName}
                        onChange={(e) => setEditedName(e.target.value)}
                        fullWidth
                      />
                    ) : (
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Description fontSize="small" sx={{ mr: 1, color: 'grey.500' }} />
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {job.job_name}
                        </Typography>
                        {editingJob !== job.job_id && (
                          <IconButton
                            size="small"
                            onClick={() => startEditJob(job)}
                            sx={{ ml: 1 }}
                          >
                            <Edit fontSize="small" />
                          </IconButton>
                        )}
                      </Box>
                    )}
                  </TableCell>

                  <TableCell>
                    {editingJob === job.job_id ? (
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <TextField
                          size="small"
                          value={editedTags}
                          onChange={(e) => setEditedTags(e.target.value)}
                          placeholder="Tags..."
                        />
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => saveEditJob(job.job_id)}
                        >
                          <Save fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={cancelEditJob}
                        >
                          <Cancel fontSize="small" />
                        </IconButton>
                      </Box>
                    ) : (
                      job.client_name || '-'
                    )}
                  </TableCell>

                  <TableCell>
                    {getStatusChip(job.status)}
                  </TableCell>

                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {job.processed_records || 0} / {job.total_records || 0}
                    </Typography>
                  </TableCell>

                  <TableCell sx={{ minWidth: 170 }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={job.progress_percentage || 0}
                          sx={{ flex: 1, height: 8, borderRadius: 4 }}
                        />
                        <Typography variant="caption" sx={{ minWidth: 40 }}>
                          {Math.round(job.progress_percentage || 0)}%
                        </Typography>
                      </Box>

                      {job.status === 'PROCESSING' && (
                        <Typography
                          variant="caption"
                          sx={{ color: 'text.secondary', fontSize: '0.7rem' }}
                        >
                          {job.estimated_time_seconds
                            ? `ETA: ${formatETA(job.estimated_time_seconds)}`
                            : 'Calculating ETA...'}
                        </Typography>
                      )}

                    </Box>
                  </TableCell>


                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      {job.high_confidence > 0 && (
                        <Chip
                          label={`H:${job.high_confidence}`}
                          size="small"
                          sx={{ bgcolor: '#10b981', color: 'white', fontWeight: 600 }}
                        />
                      )}
                      {job.medium_confidence > 0 && (
                        <Chip
                          label={`M:${job.medium_confidence}`}
                          size="small"
                          sx={{ bgcolor: '#f59e0b', color: 'white', fontWeight: 600 }}
                        />
                      )}
                    </Box>
                  </TableCell>

                  <TableCell align="right">
                    <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                      
                      {/* VALIDATE BUTTON - Shows for UPLOADED or FAILED jobs */}
                      {(job.status === 'UPLOADED' || job.status === 'FAILED') && (
                        <IconButton
                          size="small"
                          onClick={() => handleValidate(job.job_id)}
                          title="Start Validation"
                          sx={{
                            bgcolor: 'success.main',
                            color: 'white',
                            '&:hover': { bgcolor: 'success.dark' }
                          }}
                        >
                          <PlayArrow fontSize="small" />
                        </IconButton>
                      )}
                      
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => handleViewResults(job.job_id, job.job_name)}
                        title="View Results"
                      >
                        <Visibility fontSize="small" />
                      </IconButton>
                      
                      {job.status === 'COMPLETED' && (
                        <IconButton
                          size="small"
                          color="success"
                          onClick={() => handleExport(job.job_id)}
                          title="Export"
                        >
                          <GetApp fontSize="small" />
                        </IconButton>
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Results Dialog */}
      <ResultsDialog
        open={resultsDialogOpen}
        onClose={() => setResultsDialogOpen(false)}
        jobId={selectedJobId}
        jobName={jobs.find(j => j.job_id === selectedJobId)?.job_name}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmOpen}
        onClose={handleDeleteCancel}
      >
        <DialogTitle>
          Confirm Delete
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete {selectedJobs.length} job{selectedJobs.length > 1 ? 's' : ''}?
          </Typography>
          <Typography variant="body2" color="error" sx={{ mt: 2 }}>
            This will permanently delete all job data including statistics and cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel} disabled={deleting}>
            Cancel
          </Button>
          <Button 
            onClick={handleDeleteConfirm} 
            color="error" 
            variant="contained"
            disabled={deleting}
            startIcon={deleting ? null : <Delete />}
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Dashboard;