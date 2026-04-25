# Project Structure

This document outlines the organized structure of the AI Motor Prediction System.

## 📁 Directory Structure

```
AI ml for smart motor/
├── app/                    # Main application code
│   ├── database.py        # Database configuration and connection
│   ├── main.py            # FastAPI application entry point
│   ├── routers/           # API route handlers
│   │   ├── data.py        # Sensor data ingestion endpoint
│   │   ├── predictions.py # Prediction retrieval endpoint
│   │   ├── devices.py     # Device management endpoints
│   │   ├── faults.py      # Fault event endpoints
│   │   └── forecast.py    # Power forecasting endpoint
│   ├── schemas/           # Pydantic data models
│   │   └── schemas.py     # Data validation schemas
│   └── services/          # Business logic and ML models
│       ├── prediction.py              # Basic rule-based predictions
│       ├── ml_prediction.py           # ML-based predictions
│       ├── advanced_ml_prediction.py  # Advanced ML with NASA models
│       └── prebuilt_models.py         # Prebuilt sklearn models
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   └── api.js         # API client configuration
│   └── public/            # Static assets
├── tests/                 # Test files and testing utilities
│   ├── test_api.py                    # API endpoint tests
│   ├── test_db.py                     # Database connection tests
│   ├── test_ml_predictions.py         # ML prediction tests
│   ├── test_advanced_ml.py            # Advanced ML tests
│   ├── test_prebuilt_models.py        # Prebuilt model tests
│   └── ...                           # Other test files
├── scripts/               # Utility and maintenance scripts
│   ├── check_data.py      # Data verification utilities
│   ├── verify_data.py     # Data validation scripts
│   └── create_dummy_data.py # Test data generation
├── docs/                  # Documentation and configuration
│   ├── ml_config.py       # ML model configuration
│   ├── prebuilt_models_guide.py # Guide to available ML models
│   ├── prediction.py      # Legacy prediction documentation
│   └── PROJECT_STRUCTURE.md # This file
├── .env                   # Environment variables (private)
├── .gitignore            # Git ignore rules
├── requirements.txt      # Python dependencies
├── sql_setup.sql         # Database schema
├── Procfile              # Heroku deployment configuration
└── README.md             # Project overview
```

## 🧪 Testing

Run tests from the project root:

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python tests/test_ml_predictions.py

# Run API tests
python tests/test_api.py
```

## 📜 Scripts

Utility scripts in the `scripts/` directory:

- `check_data.py` - Verify data integrity
- `verify_data.py` - Validate sensor readings
- `create_dummy_data.py` - Generate test data

## 📚 Documentation

- `ml_config.py` - ML model configuration options
- `prebuilt_models_guide.py` - Available prebuilt ML models
- `prediction.py` - Legacy prediction system documentation

## 🔧 Configuration

### Environment Variables (.env)
- `DATABASE_URL` - PostgreSQL connection string
- `API_KEY` - API authentication key
- `GEMINI_API_KEY` - Google Gemini AI API key

### ML Configuration
Edit `docs/ml_config.py` to configure:
- Prediction modes (basic/ml/advanced)
- Gemini AI modes (disabled/commentary/prediction)
- NASA bearing model settings
- Model thresholds and parameters

## 🚀 Deployment

- **Backend**: FastAPI on port 8000
- **Frontend**: React on port 5174
- **Database**: PostgreSQL
- **Deployment**: Heroku (Procfile configured)

## 📊 ML Models Available

### Basic Models
- Rule-based predictions
- Threshold monitoring

### ML Models
- Isolation Forest anomaly detection
- Linear regression time series
- Random Forest classification

### Advanced Models
- NASA bearing failure prediction
- Ensemble anomaly detection
- RUL (Remaining Useful Life) prediction
- Advanced time series analysis

### Prebuilt Models
- Local Outlier Factor
- Elliptic Envelope
- Ridge/Lasso regression
- Gradient Boosting
- Support Vector Regression

## 🔄 Development Workflow

1. Make changes to `app/` directory
2. Run tests in `tests/` directory
3. Update documentation in `docs/` if needed
4. Use scripts in `scripts/` for data management

## 📝 Notes

- All test files moved to `tests/` for organization
- Documentation and configuration moved to `docs/`
- Utility scripts moved to `scripts/`
- Root directory now contains only essential files
