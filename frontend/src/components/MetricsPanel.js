import React, { useState, useEffect } from 'react';
import {
  Box, Card, CardContent, Typography, Grid, Paper, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow,
  CircularProgress, Chip, Alert
} from '@mui/material';
import {
  TrendingUp, Assessment, Transform, CheckCircle
} from '@mui/icons-material';
import { Pie, Bar, Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import axios from 'axios';

// Register Chart.js components
ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend
);

const MetricsPanel = ({ jobId }) => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchMetrics();
  }, [jobId]);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/v1/metrics/job/${jobId}/metrics`);
      setMetrics(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching metrics:', err);
      setError('Failed to load metrics. Please try again.');
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading metrics...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!metrics) {
    return (
      <Box p={3}>
        <Alert severity="info">No metrics available for this job.</Alert>
      </Box>
    );
  }

  const { summary_cards, pie_chart, bar_chart, line_chart, field_breakdown, aggregate_stats } = metrics;

  // Summary Card Component
  const SummaryCard = ({ data, icon: Icon, color }) => (
    <Card sx={{ height: '100%', borderTop: `4px solid ${color}` }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography variant="h6" color="textSecondary" gutterBottom>
              {data.title}
            </Typography>
            <Typography variant="h3" component="div" sx={{ color, fontWeight: 'bold', my: 1 }}>
              {data.completeness}%
            </Typography>
            <Typography variant="body2" color="textSecondary">
              {data.subtitle}
            </Typography>
            <Typography variant="caption" color="textSecondary" display="block" sx={{ mt: 1 }}>
              {data.description}
            </Typography>
          </Box>
          <Icon sx={{ fontSize: 48, color, opacity: 0.3 }} />
        </Box>
      </CardContent>
    </Card>
  );

  // Pie Chart Configuration
  const pieChartConfig = {
    labels: pie_chart.labels,
    datasets: [{
      data: pie_chart.data,
      backgroundColor: pie_chart.colors,
      borderWidth: 2,
      borderColor: '#fff'
    }]
  };

  const pieChartOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          padding: 15,
          font: { size: 12 }
        }
      },
      title: {
        display: true,
        text: pie_chart.title,
        font: { size: 16, weight: 'bold' },
        padding: { bottom: 20 }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.label || '';
            const value = context.parsed || 0;
            const percentage = ((value / pie_chart.total) * 100).toFixed(1);
            return `${label}: ${value} (${percentage}%)`;
          }
        }
      }
    }
  };

  // Bar Chart Configuration
  const barChartConfig = {
    labels: bar_chart.labels,
    datasets: bar_chart.datasets.map(ds => ({
      label: ds.label,
      data: ds.data,
      backgroundColor: ds.color,
      borderColor: ds.color,
      borderWidth: 1
    }))
  };

  const barChartOptions = {
    responsive: true,
    maintainAspectRatio: true,
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: function(value) {
            return value + '%';
          }
        }
      }
    },
    plugins: {
      legend: {
        position: 'bottom',
        labels: { padding: 15 }
      },
      title: {
        display: true,
        text: bar_chart.title,
        font: { size: 16, weight: 'bold' },
        padding: { bottom: 20 }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return `${context.dataset.label}: ${context.parsed.y}%`;
          }
        }
      }
    }
  };

  // Line Chart Configuration
  const lineChartConfig = {
    labels: line_chart.labels,
    datasets: [{
      label: 'Data Completeness',
      data: line_chart.data,
      borderColor: line_chart.color,
      backgroundColor: line_chart.color + '20',
      borderWidth: 3,
      fill: true,
      tension: 0.4,
      pointRadius: 6,
      pointHoverRadius: 8
    }]
  };

  const lineChartOptions = {
    responsive: true,
    maintainAspectRatio: true,
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: function(value) {
            return value + '%';
          }
        }
      }
    },
    plugins: {
      legend: {
        display: false
      },
      title: {
        display: true,
        text: line_chart.title,
        font: { size: 16, weight: 'bold' },
        padding: { bottom: 20 }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return `Completeness: ${context.parsed.y}%`;
          }
        }
      }
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* ROW 1: SUMMARY CARDS */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <SummaryCard 
            data={summary_cards.original} 
            icon={Assessment}
            color="#2196f3"
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <SummaryCard 
            data={summary_cards.osm} 
            icon={TrendingUp}
            color="#4caf50"
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <SummaryCard 
            data={summary_cards.oracle} 
            icon={CheckCircle}
            color="#9c27b0"
          />
        </Grid>
      </Grid>

      {/* ROW 2: CHARTS */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Pie data={pieChartConfig} options={pieChartOptions} />
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Bar data={barChartConfig} options={barChartOptions} />
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Line data={lineChartConfig} options={lineChartOptions} />
          </Paper>
        </Grid>
      </Grid>

      {/* AGGREGATE STATS BANNER */}
      <Paper sx={{ p: 2, mb: 3, bgcolor: '#f5f5f5' }}>
        <Grid container spacing={2}>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="textSecondary">Total Records</Typography>
            <Typography variant="h6">{aggregate_stats.total_records}</Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="textSecondary">Fields Filled by OSM</Typography>
            <Typography variant="h6" color="success.main">+{aggregate_stats.osm_fields_filled}</Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="textSecondary">Total Transformations</Typography>
            <Typography variant="h6" color="secondary.main">{aggregate_stats.oracle_total_transformations}</Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="textSecondary">Quality Improvement</Typography>
            <Typography variant="h6" color="primary.main">+{aggregate_stats.quality_improvement}%</Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* ROW 3: DETAILED BREAKDOWN TABLE */}
      <Typography variant="h6" gutterBottom sx={{ mt: 4, mb: 2 }}>
        Field-by-Field Breakdown
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ bgcolor: '#f5f5f5' }}>
              <TableCell><strong>Field</strong></TableCell>
              <TableCell align="right"><strong>Original</strong></TableCell>
              <TableCell align="right"><strong>OSM Validated</strong></TableCell>
              <TableCell align="right"><strong>Oracle Ready</strong></TableCell>
              <TableCell align="center"><strong>OSM Filled</strong></TableCell>
              <TableCell><strong>Transformations Applied</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {field_breakdown.map((field, index) => (
              <TableRow key={index} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight="medium">
                    {field.field}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Chip 
                    label={`${field.original}%`}
                    size="small"
                    color={field.original >= 90 ? 'success' : field.original >= 70 ? 'warning' : 'error'}
                    variant="outlined"
                  />
                </TableCell>
                <TableCell align="right">
                  <Chip 
                    label={`${field.osm}%`}
                    size="small"
                    color={field.osm >= 90 ? 'success' : field.osm >= 70 ? 'warning' : 'default'}
                  />
                </TableCell>
                <TableCell align="right">
                  <Chip 
                    label="100%"
                    size="small"
                    color="success"
                    icon={<CheckCircle />}
                  />
                </TableCell>
                <TableCell align="center">
                  {field.osm_filled > 0 ? (
                    <Chip 
                      label={`+${field.osm_filled}`}
                      size="small"
                      color="success"
                      variant="filled"
                    />
                  ) : (
                    <Typography variant="caption" color="textSecondary">-</Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {field.transformations.map((trans, i) => (
                      <Chip 
                        key={i}
                        label={trans}
                        size="small"
                        variant="outlined"
                        color="secondary"
                      />
                    ))}
                    {field.transformations.length === 0 && (
                      <Typography variant="caption" color="textSecondary">None</Typography>
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* FOOTER INFO */}
      <Box sx={{ mt: 3, p: 2, bgcolor: '#e3f2fd', borderRadius: 1 }}>
        <Typography variant="caption" color="textSecondary">
          <strong>Metrics Breakdown:</strong> Original completeness shows data quality from your uploaded file. 
          OSM Validation shows improvements after OpenStreetMap validation (missing fields filled, geocoding added). 
          Oracle Ready shows final data quality after Oracle Fusion transformations (ALL CAPS, state codes, standardized abbreviations).
        </Typography>
      </Box>
    </Box>
  );
};

export default MetricsPanel;
