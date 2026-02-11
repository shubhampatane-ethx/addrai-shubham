import React, { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Chip, Box, Typography, CircularProgress, TextField,
  InputAdornment, IconButton, Tabs, Tab, Badge, TablePagination,
  Tooltip
} from '@mui/material';
import {
  Search, Close, CheckCircle, Warning, Error as ErrorIcon,
  Download, HourglassEmpty
} from '@mui/icons-material';
import axios from 'axios';

const ResultsDialog = ({ open, onClose, jobId, jobName }) => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('all');
  
  // Pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  
  // Stats
  const [stats, setStats] = useState({
    total: 0,
    high: 0,
    medium: 0,
    low: 0,
    none: 0
  });

  useEffect(() => {
    if (open && jobId) {
      fetchResults();
    }
  }, [open, jobId]);

  const fetchResults = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`/api/v1/jobs/${jobId}/results`);
      const data = response.data.results || [];
      setResults(data);
      
      // Calculate stats - handle NONE as separate category
      const newStats = {
        total: data.length,
        high: data.filter(r => r.confidence_level?.toUpperCase() === 'HIGH').length,
        medium: data.filter(r => r.confidence_level?.toUpperCase() === 'MEDIUM').length,
        low: data.filter(r => r.confidence_level?.toUpperCase() === 'LOW').length,
        none: data.filter(r => !r.confidence_level || r.confidence_level?.toUpperCase() === 'NONE').length
      };
      setStats(newStats);
    } catch (err) {
      console.error('Error fetching results:', err);
      setError('Failed to load results: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleExportTab = async () => {
    try {
      let exportUrl = `/api/v1/jobs/${jobId}/export?format=3stage`;
      
      // Add confidence filter
      if (activeTab !== 'all' && activeTab !== 'none') {
        exportUrl += `&confidence=${activeTab}`;
      }
      
      const response = await axios.get(exportUrl, {
        responseType: 'blob'
      });
      
      // Download file
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const tabSuffix = activeTab !== 'all' ? `_${activeTab}` : '';
      link.setAttribute('download', `validation_results${tabSuffix}_${Date.now()}.csv`);
      
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export error:', err);
      setError('Failed to export: ' + (err.response?.data?.detail || err.message));
    }
  };

  const getConfidenceStyle = (level) => {
    const levelUpper = level?.toUpperCase();
    switch (levelUpper) {
      case 'HIGH':
        return {
          color: '#2e7d32',
          bgcolor: '#e8f5e9',
          icon: <CheckCircle sx={{ fontSize: 16, color: '#2e7d32' }} />
        };
      case 'MEDIUM':
        return {
          color: '#f57c00',
          bgcolor: '#fff3e0',
          icon: <Warning sx={{ fontSize: 16, color: '#f57c00' }} />
        };
      case 'LOW':
        return {
          color: '#d32f2f',
          bgcolor: '#ffebee',
          icon: <ErrorIcon sx={{ fontSize: 16, color: '#d32f2f' }} />
        };
      default:
        return {
          color: '#757575',
          bgcolor: '#f5f5f5',
          icon: <HourglassEmpty sx={{ fontSize: 16, color: '#757575' }} />
        };
    }
  };

  // Safe value formatter - handles null, undefined, NaN
  const safeValue = (value, defaultValue = '-') => {
    if (value === null || value === undefined || value === '' || value === 'NaN' || (typeof value === 'number' && isNaN(value))) {
      return defaultValue;
    }
    return value;
  };

  // Filter by search and tab
  const filteredResults = results.filter(result => {
    // Tab filter
    if (activeTab !== 'all') {
      const resultConfidence = (result.confidence_level || 'NONE').toUpperCase();
      const tabConfidence = activeTab.toUpperCase();
      
      if (resultConfidence !== tabConfidence) {
        return false;
      }
    }
    
    // Search filter
    if (searchTerm.trim() !== '') {
      const search = searchTerm.toLowerCase();
      return (
        safeValue(result.entity_name, '').toLowerCase().includes(search) ||
        safeValue(result.original_address, '').toLowerCase().includes(search) ||
        safeValue(result.oracle_address, '').toLowerCase().includes(search) ||
        safeValue(result.validated_address, '').toLowerCase().includes(search) ||
        safeValue(result.city, '').toLowerCase().includes(search)
      );
    }
    
    return true;
  });

  // Pagination
  const paginatedResults = filteredResults.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
    setPage(0);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xl"
      fullWidth
      PaperProps={{
        sx: { height: '90vh', maxHeight: '90vh' }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h6">Validation Results - Oracle Transformed</Typography>
            {jobName && (
              <Typography variant="body2" color="textSecondary" sx={{ mt: 0.5 }}>
                {jobName}
              </Typography>
            )}
          </Box>
          <IconButton onClick={onClose} size="small">
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography color="error">{error}</Typography>
            <Button onClick={fetchResults} sx={{ mt: 2 }}>
              Retry
            </Button>
          </Box>
        ) : (
          <>
            {/* Tabs */}
            <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
              <Tabs value={activeTab} onChange={handleTabChange}>
                <Tab
                  label={`ALL (${stats.total})`}
                  value="all"
                />
                <Tab
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <CheckCircle sx={{ fontSize: 18, color: '#2e7d32' }} />
                      HIGH ({stats.high})
                    </Box>
                  }
                  value="high"
                  sx={{
                    bgcolor: stats.high > 0 && activeTab === 'high' ? '#e8f5e9' : 'transparent',
                  }}
                />
                <Tab
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Warning sx={{ fontSize: 18, color: '#f57c00' }} />
                      MEDIUM ({stats.medium})
                    </Box>
                  }
                  value="medium"
                  sx={{
                    bgcolor: stats.medium > 0 && activeTab === 'medium' ? '#fff3e0' : 'transparent',
                  }}
                />
                <Tab
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <ErrorIcon sx={{ fontSize: 18, color: '#d32f2f' }} />
                      LOW ({stats.low})
                    </Box>
                  }
                  value="low"
                  sx={{
                    bgcolor: stats.low > 0 && activeTab === 'low' ? '#ffebee' : 'transparent',
                  }}
                />
                {stats.none > 0 && (
                  <Tab
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <HourglassEmpty sx={{ fontSize: 18, color: '#757575' }} />
                        PROCESSING ({stats.none})
                      </Box>
                    }
                    value="none"
                    sx={{
                      bgcolor: activeTab === 'none' ? '#f5f5f5' : 'transparent',
                    }}
                  />
                )}
              </Tabs>
            </Box>

            {/* Search and Export */}
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <TextField
                placeholder="Search by address or entity name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                size="small"
                sx={{ width: 400 }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
              />

              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <Typography variant="body2" color="textSecondary">
                  Showing: <strong>{filteredResults.length}</strong> records
                </Typography>

                <Tooltip title={`Export ${activeTab === 'all' ? 'all' : activeTab.toUpperCase() + ' confidence'} records`}>
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={<Download />}
                    onClick={handleExportTab}
                    disabled={filteredResults.length === 0}
                    sx={{
                      bgcolor: activeTab === 'high' ? '#2e7d32' : 
                               activeTab === 'medium' ? '#f57c00' : 
                               activeTab === 'low' ? '#d32f2f' : 
                               'primary.main',
                      '&:hover': {
                        bgcolor: activeTab === 'high' ? '#1b5e20' : 
                                 activeTab === 'medium' ? '#e65100' : 
                                 activeTab === 'low' ? '#c62828' : 
                                 'primary.dark'
                      }
                    }}
                  >
                    Export {activeTab !== 'all' ? activeTab.toUpperCase() : 'ALL'}
                  </Button>
                </Tooltip>
              </Box>
            </Box>

            {/* Table */}
            <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 'calc(90vh - 350px)' }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, bgcolor: '#f5f5f5' }}>Entity Name</TableCell>
                    <TableCell sx={{ fontWeight: 600, bgcolor: '#f5f5f5' }}>Original Address</TableCell>
                    <TableCell sx={{ fontWeight: 600, bgcolor: '#f5f5f5', color: '#2e7d32' }}>
                      Oracle Address (ALL CAPS)
                    </TableCell>
                    <TableCell sx={{ fontWeight: 600, bgcolor: '#f5f5f5' }}>Oracle City/State/ZIP</TableCell>
                    <TableCell sx={{ fontWeight: 600, bgcolor: '#f5f5f5' }}>Confidence</TableCell>
                    <TableCell sx={{ fontWeight: 600, bgcolor: '#f5f5f5' }}>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {paginatedResults.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                        <Typography color="textSecondary">
                          {searchTerm
                            ? 'No results match your search'
                            : `No ${activeTab !== 'all' ? activeTab + ' confidence' : ''} records found`}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    paginatedResults.map((result, index) => {
                      const confidenceStyle = getConfidenceStyle(result.confidence_level);
                      const confidenceLevel = (result.confidence_level || 'NONE').toUpperCase();
                      
                      // Oracle address - prefer oracle_address, fallback to validated_address
                      const oracleAddress = safeValue(result.oracle_address) !== '-' 
                        ? result.oracle_address 
                        : safeValue(result.validated_address, 'Processing...');

                      // Oracle city/state/zip
                      const oracleCityStateZip = [
                        safeValue(result.city),
                        safeValue(result.state),
                        safeValue(result.postal_code)
                      ].filter(v => v !== '-').join(', ') || '-';

                      return (
                        <TableRow
                          key={index}
                          hover
                          sx={{ 
                            '&:hover': { bgcolor: 'grey.50' },
                            bgcolor: confidenceLevel === 'HIGH' ? '#f1f8f4' :
                                     confidenceLevel === 'MEDIUM' ? '#fff8f0' :
                                     confidenceLevel === 'LOW' ? '#fef0f0' :
                                     'transparent'
                          }}
                        >
                          <TableCell>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {safeValue(result.entity_name_ora || result.entity_name, 'Unknown')}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="textSecondary" sx={{ fontSize: '0.875rem' }}>
                              {safeValue(result.original_address, 'No address')}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ 
                              fontWeight: 500, 
                              color: confidenceLevel === 'NONE' ? '#757575' : '#1976d2',
                              fontFamily: 'monospace'
                            }}>
                              {oracleAddress}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                              {oracleCityStateZip}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              icon={confidenceStyle.icon}
                              label={confidenceLevel}
                              size="small"
                              sx={{
                                bgcolor: confidenceStyle.bgcolor,
                                color: confidenceStyle.color,
                                fontWeight: 600,
                                minWidth: 90,
                                '& .MuiChip-icon': {
                                  marginLeft: '4px'
                                }
                              }}
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ 
                              color: safeValue(result.record_status) === 'READY' ? '#2e7d32' : '#757575'
                            }}>
                              {safeValue(result.record_status, 'Processing')}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </TableContainer>

            {/* Pagination */}
            <TablePagination
              rowsPerPageOptions={[25, 50, 100, 250]}
              component="div"
              count={filteredResults.length}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
              sx={{
                borderTop: '1px solid #e0e0e0',
                mt: 1
              }}
            />
          </>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Typography variant="caption" color="textSecondary" sx={{ mr: 'auto' }}>
          {paginatedResults.length > 0 && (
            <>
              Showing {page * rowsPerPage + 1}-{Math.min((page + 1) * rowsPerPage, filteredResults.length)} of {filteredResults.length}
              {activeTab !== 'all' && ` (${activeTab.toUpperCase()} confidence)`}
            </>
          )}
        </Typography>
        <Button onClick={onClose} variant="outlined">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ResultsDialog;