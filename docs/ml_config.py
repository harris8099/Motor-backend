"""
Advanced ML Prediction System Configuration

This file contains configuration options for the ML prediction system.
You can customize which models are used and how Gemini AI behaves.

Add these to your .env file to override defaults:
"""

# Prediction System Mode
# Options: 'basic' (rule-based), 'ml' (basic ML), 'advanced' (NASA models + advanced ML)
PREDICTION_MODE = 'advanced'

# Gemini AI Configuration
# Options: 'disabled' (no Gemini), 'commentary' (Gemini comments on ML results), 'prediction' (Gemini makes predictions)
GEMINI_MODE = 'commentary'

# NASA Bearing Model
# Enable/disable NASA bearing failure prediction model
NASA_BEARING_MODEL = True

# Advanced Anomaly Detection
# Enable multiple anomaly detection algorithms (Isolation Forest + One-Class SVM)
ADVANCED_ANOMALY_DETECTION = True

# Random Forest Stall Prediction
# Use Random Forest for stall risk prediction instead of basic rules
RANDOM_FOREST_STALL = True

# Remaining Useful Life (RUL) Prediction
# Enable RUL prediction using multiple health indicators
RUL_PREDICTION = True

# Advanced Efficiency Analysis
# Use exponential smoothing and change point detection for efficiency analysis
ADVANCED_EFFICIENCY = True

# Model Configuration
DEFAULT_CONTAMINATION_RATE = 0.1  # For Isolation Forest
BEARING_HEALTH_THRESHOLD = 0.7    # NASA bearing health threshold
RUL_CONFIDENCE_THRESHOLD = 0.6    # Minimum confidence for RUL predictions

# Data Requirements
MIN_HISTORICAL_DATA_POINTS = 10   # Minimum data points for ML models
OPTIMAL_HISTORICAL_DATA_POINTS = 50  # Optimal data points for best performance
MAX_HISTORICAL_DATA_POINTS = 300   # Maximum data points to process

# Prediction Thresholds
ANOMALY_ENSEMBLE_THRESHOLD = 2    # Minimum votes for anomaly detection
OVERHEATING_CONFIDENCE_THRESHOLD = 0.3  # Minimum confidence for overheating prediction
STALL_RISK_PROBABILITY_THRESHOLD = 0.3  # Minimum probability for stall risk
EFFICIENCY_DEGRADATION_THRESHOLD = 0.1  # Minimum degradation rate

# Feature Engineering
TIME_SERIES_FUTURE_STEPS = 72      # Steps to predict ahead (6 hours at 5-min intervals)
EFFICIENCY_SMOOTHING_ALPHA = 0.3   # Alpha for exponential smoothing
CHANGE_POINT_WINDOW_SIZE = 10      # Window size for change point detection

# Health Indicators for RUL
TEMP_STRESS_THRESHOLD = 70         # Temperature stress threshold (°C)
VIBRATION_STRESS_THRESHOLD = 5     # Vibration stress threshold
CURRENT_STRESS_THRESHOLD = 12      # Current stress threshold (A)

# NASA Bearing Model Parameters
NASA_RMS_NORMALIZATION_FACTOR = 20.0
NASA_CREST_FACTOR_BASE = 3.0
NASA_CREST_FACTOR_RANGE = 5.0
NASA_KURTOSIS_BASE = 3.0
NASA_KURTOSIS_RANGE = 10.0
NASA_FREQUENCY_NORMALIZATION = 100.0

# Output Configuration
INCLUDE_MODEL_DETAILS = True        # Include detailed model information in output
INCLUDE_FEATURE_IMPORTANCE = True   # Include feature importance for applicable models
INCLUDE_CONFIDENCE_INTERVALS = True # Include confidence intervals for predictions

# Performance Optimization
ENABLE_PARALLEL_PROCESSING = True   # Enable parallel processing for multiple models
CACHE_MODELS = True                  # Cache trained models for reuse
MODEL_UPDATE_FREQUENCY = 100         # Update models every N predictions

print("🔧 Advanced ML Configuration Loaded")
print(f"   Prediction Mode: {PREDICTION_MODE}")
print(f"   Gemini Mode: {GEMINI_MODE}")
print(f"   NASA Bearing Model: {NASA_BEARING_MODEL}")
print(f"   Advanced Anomaly Detection: {ADVANCED_ANOMALY_DETECTION}")
print(f"   RUL Prediction: {RUL_PREDICTION}")
