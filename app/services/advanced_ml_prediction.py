import asyncio
import json
import re
import statistics
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.schemas import SensorPayload
from google import genai
from mistralai.client import Mistral
from groq import Groq
from app.database import settings
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import mean_absolute_error
from sklearn.svm import OneClassSVM
import scipy.signal as signal
import scipy.stats as stats

class AdvancedMLPredictionService:
    def __init__(self):
        # AI Configuration
        self.gemini_mode = getattr(settings, 'gemini_mode', 'commentary')
        
        # Properly check for non-empty API keys
        gemini_key = getattr(settings, 'gemini_api_key', None)
        mistral_key = getattr(settings, 'mistral_api_key', None)
        groq_key = getattr(settings, 'groq_api_key', None)
        
        self.gemini_enabled = bool(gemini_key and str(gemini_key).strip())
        self.mistral_enabled = bool(mistral_key and str(mistral_key).strip())
        self.groq_enabled = bool(groq_key and str(groq_key).strip())
        
        # Only create clients if API keys are valid
        try:
            self.gemini_client = genai.Client(api_key=gemini_key) if self.gemini_enabled else None
        except Exception as e:
            print(f"Failed to initialize Gemini client: {e}")
            self.gemini_client = None
            self.gemini_enabled = False
            
        try:
            if self.mistral_enabled:
                self.mistral_client = Mistral(api_key=mistral_key)
                print(f"Mistral AI initialized successfully")
            else:
                self.mistral_client = None
        except Exception as e:
            print(f"Failed to initialize Mistral client: {e}")
            self.mistral_client = None
            self.mistral_enabled = False
            
        try:
            if self.groq_enabled:
                # Use AsyncGroq for async support per https://console.groq.com/docs/overview
                from groq import AsyncGroq
                self.groq_client = AsyncGroq(api_key=groq_key)
            else:
                self.groq_client = None
        except Exception as e:
            print(f"Failed to initialize Groq client: {e}")
            self.groq_client = None
            self.groq_enabled = False
        
        self.last_ai_error: Optional[str] = None
        
        # Initialize ML Models
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.one_class_svm = OneClassSVM(kernel='rbf', nu=0.1)
        self.scaler = StandardScaler()
        
        # NASA Bearing Model Configuration
        self.nasa_bearing_enabled = getattr(settings, 'nasa_bearing_model', True)
        self.bearing_health_threshold = 0.7  # NASA recommended threshold
        
    async def run_advanced_ml_predictions(self, payload: SensorPayload, db: AsyncSession) -> List[dict]:
        """Run advanced ML predictions with configurable Gemini and NASA models"""
        results = []
        device_id = payload.deviceId
        
        # Get historical data for ML training
        historical_data = await self._get_historical_data(db, device_id, hours=72)
        
        if len(historical_data) < 10:
            return await self._fallback_predictions(payload, historical_data)
        
        # Prepare ML features
        features = self._prepare_features(historical_data)
        current_features = self._extract_current_features(payload)
        
        # 1. Advanced Anomaly Detection (Multiple Models)
        anomaly_pred = await self._detect_anomalies_advanced(features, current_features, historical_data)
        if anomaly_pred:
            results.append(anomaly_pred)
        
        # 2. NASA Bearing Failure Prediction
        if self.nasa_bearing_enabled:
            bearing_pred = await self._predict_bearing_failure_nasa(features, current_features, historical_data)
            if bearing_pred:
                results.append(bearing_pred)
        
        # 3. Advanced Overheating Prediction
        overheating_pred = await self._predict_overheating_advanced(features, current_features, payload, historical_data)
        if overheating_pred:
            results.append(overheating_pred)
        
        # 4. Stall Risk Prediction (Random Forest)
        stall_pred = await self._predict_stall_risk_rf(features, current_features, payload, historical_data)
        if stall_pred:
            results.append(stall_pred)
        
        # 5. Efficiency Degradation (Advanced Time Series)
        efficiency_pred = await self._predict_efficiency_degradation_advanced(features, current_features, historical_data)
        if efficiency_pred:
            results.append(efficiency_pred)
        
        # 6. Remaining Useful Life (RUL) Prediction
        rul_pred = await self._predict_remaining_useful_life(features, current_features, historical_data)
        if rul_pred:
            results.append(rul_pred)
        
        # Note: Gemini AI is now available on-demand via /ai/analyze endpoint
        # This allows ML models to run fast at intervals while AI analysis is optional
        return results
    
    async def get_ai_analysis(self, payload: SensorPayload, db: AsyncSession) -> Optional[dict]:
        """Get on-demand AI analysis using Mistral -> Gemini -> Groq fallback loop"""
        self.last_ai_error = None
        if not any([self.mistral_enabled, self.gemini_enabled, self.groq_enabled]):
            self.last_ai_error = "No AI providers configured. Set MISTRAL_API_KEY, GEMINI_API_KEY, or GROQ_API_KEY."
            return None
        
        try:
            # Use already-stored recent predictions — no need to re-run ML models
            result = await db.execute(text("""
                SELECT prediction_type, confidence, severity, details
                FROM predictions
                WHERE device_id = :device_id
                ORDER BY ts DESC LIMIT 10
            """), {"device_id": payload.deviceId})
            recent_predictions = [
                {"type": row["prediction_type"], "confidence": row["confidence"], "severity": row["severity"]}
                for row in result.mappings()
            ]

            # Call AI based on mode
            if self.gemini_mode == 'prediction':
                return await self._get_ai_predictions(payload, recent_predictions)
            else:
                return await self._get_ai_commentary(payload, recent_predictions)
                
        except Exception as e:
            self.last_ai_error = str(e)
            print(f"On-demand AI analysis failed: {e}")
            return None
    
    async def _predict_bearing_failure_nasa(self, features: np.ndarray, current_features: np.ndarray, historical_data: List[Dict]) -> Optional[dict]:
        """NASA Bearing Failure Prediction Model"""
        if len(features) < 30:
            return None
        
        try:
            # Extract vibration data for NASA model
            vibration_x = features[:, 6]  # accel_x squared
            vibration_y = features[:, 7]  # accel_y squared  
            vibration_z = features[:, 8]  # accel_z squared
            
            # NASA Bearing Health Indicators
            # 1. RMS (Root Mean Square) - Overall vibration level
            rms_x = np.sqrt(np.mean(vibration_x))
            rms_y = np.sqrt(np.mean(vibration_y))
            rms_z = np.sqrt(np.mean(vibration_z))
            rms_total = np.sqrt(rms_x**2 + rms_y**2 + rms_z**2)
            
            # 2. Crest Factor - Peak to RMS ratio
            crest_factor_x = np.max(np.sqrt(vibration_x)) / rms_x if rms_x > 0 else 0
            crest_factor_y = np.max(np.sqrt(vibration_y)) / rms_y if rms_y > 0 else 0
            crest_factor_z = np.max(np.sqrt(vibration_z)) / rms_z if rms_z > 0 else 0
            
            # 3. Kurtosis - Peakiness of distribution
            kurtosis_x = stats.kurtosis(np.sqrt(vibration_x))
            kurtosis_y = stats.kurtosis(np.sqrt(vibration_y))
            kurtosis_z = stats.kurtosis(np.sqrt(vibration_z))
            
            # 4. Frequency Domain Analysis (FFT)
            current_vibration = current_features[0, 6:9]
            fft_magnitudes = np.abs(np.fft.fft(current_vibration))
            fft_window = fft_magnitudes[1:len(fft_magnitudes)//2]
            dominant_freq_idx = int(np.argmax(fft_window) + 1) if len(fft_window) > 0 else 0
            
            # 5. NASA Bearing Health Index (BHI)
            # Based on NASA's research on bearing fault detection
            health_indicators = {
                'rms_level': rms_total,
                'crest_factor': np.mean([crest_factor_x, crest_factor_y, crest_factor_z]),
                'kurtosis': np.mean([kurtosis_x, kurtosis_y, kurtosis_z]),
                'frequency_content': float(np.mean(fft_magnitudes)) if len(fft_magnitudes) > 0 else 0.0,
                'dominant_frequency': dominant_freq_idx
            }
            
            # Normalize health indicators (0-1 scale, higher is worse)
            normalized_indicators = {}
            normalized_indicators['rms_norm'] = min(rms_total / 20.0, 1.0)  # Normalize against 20 units
            normalized_indicators['crest_norm'] = min((np.mean([crest_factor_x, crest_factor_y, crest_factor_z]) - 3.0) / 5.0, 1.0)
            normalized_indicators['kurtosis_norm'] = min(max((np.mean([kurtosis_x, kurtosis_y, kurtosis_z]) - 3.0) / 10.0, 0), 1.0)
            normalized_indicators['freq_norm'] = min((float(np.mean(fft_magnitudes)) if len(fft_magnitudes) > 0 else 0.0) / 100.0, 1.0)
            
            # Calculate NASA Bearing Health Index
            bhi = np.mean(list(normalized_indicators.values()))
            
            # Trend analysis
            if len(vibration_x) >= 20:
                recent_rms = np.sqrt(vibration_x[-20:])
                rms_trend = np.polyfit(range(len(recent_rms)), recent_rms, 1)[0]
            else:
                rms_trend = 0
            
            # Fault detection based on NASA thresholds
            fault_detected = False
            fault_type = None
            confidence = 0.0
            
            if bhi > 0.8:
                fault_detected = True
                fault_type = "severe_damage"
                confidence = 0.9
            elif bhi > 0.6:
                fault_detected = True
                fault_type = "developing_fault"
                confidence = 0.7
            elif rms_trend > 0.5:
                fault_detected = True
                fault_type = "degradation_trend"
                confidence = 0.6
            elif normalized_indicators['kurtosis_norm'] > 0.7:
                fault_detected = True
                fault_type = "impulsive_fault"
                confidence = 0.65
            
            if fault_detected:
                return {
                    "type": "nasa_bearing_analysis",
                    "confidence": confidence,
                    "severity": "high" if bhi > 0.7 else "medium",
                    "details": {
                        "bearing_health_index": float(bhi),
                        "health_status": "critical" if bhi > 0.8 else "warning" if bhi > 0.6 else "monitor",
                        "fault_type": fault_type,
                        "rms_level": float(rms_total),
                        "crest_factor": float(np.mean([crest_factor_x, crest_factor_y, crest_factor_z])),
                        "kurtosis": float(np.mean([kurtosis_x, kurtosis_y, kurtosis_z])),
                        "rms_trend": float(rms_trend),
                        "dominant_frequency": int(dominant_freq_idx),
                        "nasa_indicators": {
                            "rms_normalized": float(normalized_indicators['rms_norm']),
                            "crest_normalized": float(normalized_indicators['crest_norm']),
                            "kurtosis_normalized": float(normalized_indicators['kurtosis_norm'])
                        },
                        "recommendation": self._get_bearing_recommendation(bhi, fault_type)
                    }
                }
            
        except Exception as e:
            print(f"NASA bearing prediction failed: {e}")
        
        return None
    
    def _get_bearing_recommendation(self, bhi: float, fault_type: str) -> str:
        """NASA-based bearing maintenance recommendations"""
        if bhi > 0.8:
            return "IMMEDIATE ACTION REQUIRED: Bearing failure imminent. Schedule replacement within 24 hours."
        elif bhi > 0.6:
            return "Plan bearing replacement within 1 week. Monitor vibration levels closely."
        elif fault_type == "degradation_trend":
            return "Schedule bearing inspection within 1 month. Trend indicates progressive wear."
        elif fault_type == "impulsive_fault":
            return "Investigate for bearing contamination or lubrication issues."
        else:
            return "Continue monitoring. No immediate action required."
    
    async def _detect_anomalies_advanced(self, features: np.ndarray, current_features: np.ndarray, historical_data: List[Dict]) -> Optional[dict]:
        """Advanced anomaly detection using multiple models"""
        if len(features) < 20:
            return None
        
        try:
            # Multiple anomaly detection models
            anomaly_scores = {}
            
            # Isolation Forest
            self.isolation_forest.fit(features)
            iso_score = self.isolation_forest.decision_function(current_features)[0]
            iso_anomaly = self.isolation_forest.predict(current_features)[0] == -1
            anomaly_scores['isolation_forest'] = iso_score
            
            # One-Class SVM
            self.one_class_svm.fit(features)
            svm_score = self.one_class_svm.decision_function(current_features)[0]
            svm_anomaly = self.one_class_svm.predict(current_features)[0] == -1
            anomaly_scores['one_class_svm'] = svm_score
            
            # Statistical Z-score method
            z_scores = np.abs((current_features[0] - np.mean(features, axis=0)) / np.std(features, axis=0))
            max_z_score = np.max(z_scores)
            anomaly_scores['z_score'] = -max_z_score  # Negative for consistency
            
            # Ensemble decision
            anomaly_votes = sum(1 for score in anomaly_scores.values() if score < -0.1)
            avg_score = np.mean(list(anomaly_scores.values()))
            
            if anomaly_votes >= 2 or avg_score < -0.2:
                # Find most anomalous features
                feature_importance = np.abs(current_features[0] - np.mean(features, axis=0))
                most_anomalous_idx = np.argmax(feature_importance)
                feature_names = ['power', 'current', 'voltage', 'rpm', 'temp1', 'temp2', 'vibration', 'energy', 'uptime', 'motor_status']
                
                confidence = min(abs(avg_score) + 0.3, 1.0)
                
                return {
                    "type": "advanced_anomaly_detection",
                    "confidence": confidence,
                    "severity": "high" if avg_score < -0.3 else "medium",
                    "details": {
                        "ensemble_score": float(avg_score),
                        "anomaly_votes": anomaly_votes,
                        "model_scores": {k: float(v) for k, v in anomaly_scores.items()},
                        "anomalous_feature": feature_names[most_anomalous_idx],
                        "feature_deviation": float(feature_importance[most_anomalous_idx]),
                        "detection_methods": list(anomaly_scores.keys())
                    }
                }
        except Exception as e:
            print(f"Advanced anomaly detection failed: {e}")
        
        return None
    
    async def _predict_overheating_advanced(self, features: np.ndarray, current_features: np.ndarray, payload: SensorPayload, historical_data: List[Dict]) -> Optional[dict]:
        """Advanced overheating prediction with multiple models"""
        if len(features) < 30:
            return None
        
        try:
            # Temperature series
            temp_series = features[:, 4]  # temp1
            current_temp = current_features[0, 4]
            
            # Multiple prediction models
            predictions = {}
            
            # Linear Regression
            X = np.arange(len(temp_series)).reshape(-1, 1)
            lr_model = LinearRegression()
            lr_model.fit(X, temp_series)
            future_steps = 72  # 6 hours ahead
            future_X = np.arange(len(temp_series), len(temp_series) + future_steps).reshape(-1, 1)
            lr_predictions = lr_model.predict(future_X)
            predictions['linear_regression'] = np.max(lr_predictions)
            
            # Polynomial Regression (degree 2)
            poly_coeffs = np.polyfit(X.flatten(), temp_series, 2)
            poly_model = np.poly1d(poly_coeffs)
            poly_predictions = poly_model(future_X.flatten())
            predictions['polynomial'] = np.max(poly_predictions)
            
            # Moving Average trend
            window_size = min(10, len(temp_series) // 3)
            moving_avg = np.convolve(temp_series, np.ones(window_size)/window_size, mode='valid')
            ma_trend = np.polyfit(range(len(moving_avg)), moving_avg, 1)[0]
            ma_prediction = current_temp + ma_trend * future_steps
            predictions['moving_average'] = ma_prediction
            
            # Ensemble prediction
            max_predicted_temp = np.mean(list(predictions.values()))
            temp_threshold = payload.protection.maxTempC
            
            if max_predicted_temp > temp_threshold:
                # Time to threshold calculation
                time_to_threshold = None
                for model_name, pred_temp in predictions.items():
                    if pred_temp > temp_threshold:
                        steps_to_threshold = np.argmax(lr_predictions > temp_threshold) if model_name == 'linear_regression' else future_steps
                        time_to_threshold = steps_to_threshold * 5  # 5 minutes per step
                        break
                
                confidence = min((max_predicted_temp - temp_threshold) / 20, 1.0)
                
                return {
                    "type": "advanced_overheating_prediction",
                    "confidence": confidence,
                    "severity": "high" if max_predicted_temp > temp_threshold + 10 else "medium",
                    "details": {
                        "current_temp": float(current_temp),
                        "max_predicted_temp": float(max_predicted_temp),
                        "temp_threshold": temp_threshold,
                        "time_to_threshold_minutes": int(time_to_threshold) if time_to_threshold else None,
                        "model_predictions": {k: float(v) for k, v in predictions.items()},
                        "trend_analysis": {
                            "linear_trend": float(lr_model.coef_[0]),
                            "polynomial_curvature": float(poly_coeffs[0]),
                            "moving_avg_trend": float(ma_trend)
                        }
                    }
                }
        except Exception as e:
            print(f"Advanced overheating prediction failed: {e}")
        
        return None
    
    async def _predict_stall_risk_rf(self, features: np.ndarray, current_features: np.ndarray, payload: SensorPayload, historical_data: List[Dict]) -> Optional[dict]:
        """Stall risk prediction using Random Forest"""
        if len(features) < 30:
            return None
        
        try:
            # Prepare training data for Random Forest
            X = features[:, [0, 1, 3, 4, 6]]  # power, current, rpm, temp, vibration
            
            # Create labels based on stall conditions
            y = []
            for i in range(len(features)):
                power, current, rpm, temp, vibration = X[i]
                # Simulate stall conditions
                stall_score = 0
                if current > payload.protection.stallCurrentA * 0.8:
                    stall_score += 0.3
                if rpm < payload.protection.minRpm * 1.2:
                    stall_score += 0.4
                if power > 0 and rpm < 100:
                    stall_score += 0.3
                y.append(1 if stall_score > 0.5 else 0)
            
            # Train Random Forest
            rf_model = RandomForestClassifier(n_estimators=50, random_state=42)
            rf_model.fit(X, y)
            
            # Predict current state
            current_X = current_features[0, [0, 1, 3, 4, 6]].reshape(1, -1)
            stall_probability = rf_model.predict_proba(current_X)[0, 1]
            
            # Feature importance
            feature_names = ['power', 'current', 'rpm', 'temperature', 'vibration']
            feature_importance = dict(zip(feature_names, rf_model.feature_importances_))
            
            if stall_probability > 0.3:
                current_power = current_features[0, 0]
                current_current = current_features[0, 1]
                current_rpm = current_features[0, 3]
                
                # Calculate efficiency
                efficiency = current_rpm / current_power if current_power > 0 else 0
                
                return {
                    "type": "stall_risk_random_forest",
                    "confidence": stall_probability,
                    "severity": "high" if stall_probability > 0.7 else "medium",
                    "details": {
                        "stall_probability": float(stall_probability),
                        "current_efficiency": float(efficiency),
                        "feature_importance": {k: float(v) for k, v in feature_importance.items()},
                        "risk_factors": {
                            "high_current": current_current > payload.protection.stallCurrentA * 0.8,
                            "low_rpm": current_rpm < payload.protection.minRpm * 1.2,
                            "power_without_rotation": current_power > 0 and current_rpm < 100
                        },
                        "model_type": "Random Forest Classifier"
                    }
                }
        except Exception as e:
            print(f"Random Forest stall prediction failed: {e}")
        
        return None
    
    async def _predict_efficiency_degradation_advanced(self, features: np.ndarray, current_features: np.ndarray, historical_data: List[Dict]) -> Optional[dict]:
        """Advanced efficiency degradation prediction"""
        if len(features) < 50:
            return None
        
        try:
            # Calculate efficiency over time
            efficiency_series = []
            for i in range(len(features)):
                power = features[i, 0]
                rpm = features[i, 3]
                if power > 0 and rpm > 0:
                    efficiency_series.append(rpm / power)
            
            if len(efficiency_series) < 30:
                return None
            
            # Current efficiency
            current_power = current_features[0, 0]
            current_rpm = current_features[0, 3]
            current_efficiency = current_rpm / current_power if current_power > 0 else 0
            
            # Advanced time series analysis
            # 1. Exponential smoothing
            alpha = 0.3
            smoothed_efficiency = [efficiency_series[0]]
            for i in range(1, len(efficiency_series)):
                smoothed_efficiency.append(alpha * efficiency_series[i] + (1 - alpha) * smoothed_efficiency[-1])
            
            # 2. Trend detection with multiple models
            X = np.arange(len(efficiency_series)).reshape(-1, 1)
            
            # Linear trend
            linear_model = LinearRegression()
            linear_model.fit(X, efficiency_series)
            linear_trend = linear_model.coef_[0]
            
            # Exponential trend
            log_efficiency = np.log(np.array(efficiency_series) + 1e-6)
            exp_model = LinearRegression()
            exp_model.fit(X, log_efficiency)
            exp_trend = exp_model.coef_[0]
            
            # 3. Change point detection
            # Simple change point detection using rolling statistics
            window_size = 10
            rolling_mean = np.convolve(efficiency_series, np.ones(window_size)/window_size, mode='valid')
            rolling_std = np.convolve(efficiency_series, np.ones(window_size)/window_size, mode='valid')
            
            # Detect significant changes
            changes = []
            for i in range(1, len(rolling_mean)):
                if abs(rolling_mean[i] - rolling_mean[i-1]) > 2 * rolling_std[i-1]:
                    changes.append(i)
            
            # 4. Future prediction
            future_steps = 48  # 4 hours ahead
            future_X = np.arange(len(efficiency_series), len(efficiency_series) + future_steps).reshape(-1, 1)
            
            # Ensemble prediction
            linear_future = linear_model.predict(future_X)
            exp_future = np.exp(exp_model.predict(future_X)) - 1e-6
            ensemble_future = 0.6 * linear_future + 0.4 * exp_future
            
            # Calculate degradation metrics
            baseline_efficiency = np.mean(efficiency_series[:10])
            current_efficiency_norm = current_efficiency / baseline_efficiency
            min_predicted_efficiency = np.min(ensemble_future)
            future_degradation = (baseline_efficiency - min_predicted_efficiency) / baseline_efficiency
            
            # Determine if degradation is significant
            degradation_rate = (baseline_efficiency - np.mean(efficiency_series[-10:])) / baseline_efficiency
            trend_consensus = (linear_trend < 0) + (exp_trend < 0)  # Count negative trends
            
            if degradation_rate > 0.1 or future_degradation > 0.15 or trend_consensus >= 2:
                confidence = min(degradation_rate * 2 + future_degradation, 1.0)
                
                return {
                    "type": "advanced_efficiency_degradation",
                    "confidence": confidence,
                    "severity": "high" if future_degradation > 0.25 else "medium",
                    "details": {
                        "current_efficiency": float(current_efficiency),
                        "baseline_efficiency": float(baseline_efficiency),
                        "degradation_rate": float(degradation_rate),
                        "future_degradation": float(future_degradation),
                        "min_predicted_efficiency": float(min_predicted_efficiency),
                        "trend_analysis": {
                            "linear_trend": float(linear_trend),
                            "exponential_trend": float(exp_trend),
                            "trend_consensus": trend_consensus
                        },
                        "change_points": {
                            "detected_changes": len(changes),
                            "recent_change": len(changes) > 0 and changes[-1] > len(efficiency_series) - 20
                        },
                        "prediction_horizon": "4 hours",
                        "model_ensemble": "Linear + Exponential"
                    }
                }
        except Exception as e:
            print(f"Advanced efficiency degradation prediction failed: {e}")
        
        return None
    
    async def _predict_remaining_useful_life(self, features: np.ndarray, current_features: np.ndarray, historical_data: List[Dict]) -> Optional[dict]:
        """Remaining Useful Life (RUL) Prediction"""
        if len(features) < 50:
            return None
        
        try:
            # Multiple health indicators for RUL
            health_indicators = {}
            
            # 1. Temperature stress indicator
            temp_series = features[:, 4]
            temp_stress = np.sum(np.maximum(temp_series - 70, 0)) / len(temp_series)  # Stress above 70°C
            health_indicators['temp_stress'] = temp_stress
            
            # 2. Vibration stress indicator
            vibration_series = features[:, 6]
            vibration_stress = np.sum(np.maximum(vibration_series - 5, 0)) / len(vibration_series)
            health_indicators['vibration_stress'] = vibration_stress
            
            # 3. Current stress indicator
            current_series = features[:, 1]
            current_stress = np.sum(np.maximum(current_series - 12, 0)) / len(current_series)
            health_indicators['current_stress'] = current_stress
            
            # 4. Efficiency degradation indicator
            efficiency_series = []
            for i in range(len(features)):
                power, rpm = features[i, 0], features[i, 3]
                if power > 0 and rpm > 0:
                    efficiency_series.append(rpm / power)
            
            if len(efficiency_series) > 20:
                efficiency_degradation = (efficiency_series[0] - efficiency_series[-1]) / efficiency_series[0]
                health_indicators['efficiency_degradation'] = efficiency_degradation
            
            # Normalize health indicators (0-1, higher is worse)
            normalized_indicators = {}
            normalized_indicators['temp_stress_norm'] = min(temp_stress / 20, 1.0)
            normalized_indicators['vibration_stress_norm'] = min(vibration_stress / 10, 1.0)
            normalized_indicators['current_stress_norm'] = min(current_stress / 5, 1.0)
            if 'efficiency_degradation' in health_indicators:
                normalized_indicators['efficiency_degradation_norm'] = min(max(health_indicators['efficiency_degradation'], 0), 1.0)
            
            # Calculate overall health index
            overall_health = 1 - np.mean(list(normalized_indicators.values()))
            
            # RUL estimation based on health degradation trend
            if len(efficiency_series) > 30:
                # Calculate degradation rate
                recent_efficiency = efficiency_series[-20:]
                degradation_rate = (recent_efficiency[0] - recent_efficiency[-1]) / len(recent_efficiency)
                
                if degradation_rate > 0:
                    # Estimate RUL in hours
                    remaining_efficiency = overall_health
                    rul_hours = remaining_efficiency / degradation_rate if degradation_rate > 0 else 9999
                else:
                    rul_hours = 9999  # No degradation detected
            else:
                rul_hours = 9999
            
            # Convert to days
            rul_days = rul_hours / 24
            
            if overall_health < 0.8 or rul_days < 30:
                confidence = 0.8 if overall_health < 0.6 else 0.6
                
                return {
                    "type": "remaining_useful_life",
                    "confidence": confidence,
                    "severity": "high" if rul_days < 7 else "medium" if rul_days < 30 else "low",
                    "details": {
                        "health_index": float(overall_health),
                        "health_status": "critical" if overall_health < 0.5 else "poor" if overall_health < 0.7 else "fair" if overall_health < 0.9 else "good",
                        "rul_days": int(min(rul_days, 999)),
                        "rul_hours": int(min(rul_hours, 9999)),
                        "health_indicators": {k: float(v) for k, v in health_indicators.items()},
                        "normalized_indicators": {k: float(v) for k, v in normalized_indicators.items()},
                        "degradation_rate": float(degradation_rate) if 'degradation_rate' in locals() else 0.0,
                        "maintenance_priority": "immediate" if rul_days < 7 else "schedule" if rul_days < 30 else "monitor"
                    }
                }
        except Exception as e:
            print(f"RUL prediction failed: {e}")
        
        return None
    
    async def _get_ai_predictions(self, payload: SensorPayload, ml_predictions: list) -> Optional[dict]:
        """AI makes predictions based on ML alerts"""
        avg_temp = round((payload.temperature.t1 + payload.temperature.t2) / 2, 1)
        alerts = ", ".join(f"{p['type']}(conf={round(p['confidence'],2)},{p['severity']})" for p in ml_predictions[:5]) or "none"
        
        prompt = (
            f"Motor: rpm={payload.motor.rpm} power={payload.power.power}W "
            f"temp={avg_temp}C current={payload.power.current}A uptime={payload.uptime}h running={payload.motor.running}\n"
            f"Limits: maxCurrent={payload.protection.maxCurrentA}A maxTemp={payload.protection.maxTempC}C minRpm={payload.protection.minRpm}\n"
            f"ML alerts: {alerts}\n"
            f"As a motor reliability engineer, predict: failure probability in 24h (%), "
            f"most likely failure mode, top 2 maintenance actions, estimated RUL in days.\n"
            f"Reply strictly in JSON format: {{\"failure_probability_24h\": 0.0, \"likely_failure_mode\": \"\", \"maintenance_actions\": [], \"estimated_rul_days\": 0}}"
        )

        providers = [
            (self._call_mistral, "mistral-small"),
            (self._call_gemini, "gemini-2.0-flash"),
            (self._call_groq, "llama-3.3-70b-versatile")
        ]

        for call_func, model_name in providers:
            try:
                response_text = await call_func(prompt, model_name, is_json=True)
                if response_text:
                    try:
                        ai_predictions = json.loads(response_text)
                        failure_prob = ai_predictions.get('failure_probability_24h', 0)
                        return {
                            "type": "ai_analysis",
                            "confidence": 0.85,
                            "severity": "high" if failure_prob > 0.5 else "medium",
                            "details": {
                                **ai_predictions,
                                "prediction_mode": "cloud_ai",
                                "based_on_ml_analysis": True,
                            }
                        }
                    except json.JSONDecodeError as je:
                        print(f"JSON parse error from {model_name}: {je}")
                        # Try to extract JSON from markdown code blocks
                        json_match = re.search(r'```(?:json)?\s*(\{[^}]+\})\s*```', response_text, re.DOTALL)
                        if json_match:
                            try:
                                ai_predictions = json.loads(json_match.group(1))
                                failure_prob = ai_predictions.get('failure_probability_24h', 0)
                                return {
                                    "type": "ai_analysis",
                                    "confidence": 0.85,
                                    "severity": "high" if failure_prob > 0.5 else "medium",
                                    "details": {
                                        **ai_predictions,
                                        "prediction_mode": "cloud_ai",
                                        "based_on_ml_analysis": True,
                                    }
                                }
                            except:
                                pass
                        continue
            except Exception as e:
                print(f"Prediction failed with {model_name}: {e}")
                if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                    continue
                # Continue to next provider on any error
                continue
                
        self.last_ai_error = "All AI providers failed or exhausted quota."
        return None

    async def _get_ai_commentary(self, payload: SensorPayload, ml_predictions: list) -> Optional[dict]:
        """AI provides commentary on ML predictions"""
        avg_temp = round((payload.temperature.t1 + payload.temperature.t2) / 2, 1)
        alerts = ", ".join(f"{p['type']}(conf={round(p['confidence'],2)},{p['severity']})" for p in ml_predictions[:5]) or "none"

        prompt = (
            f"Motor: rpm={payload.motor.rpm} power={payload.power.power}W "
            f"temp={avg_temp}C current={payload.power.current}A uptime={payload.uptime}h\n"
            f"ML alerts: {alerts}\n"
            f"In 2-3 sentences, give an expert maintenance engineer comment on these ML alerts. "
            f"Focus on key concern and recommended priority. Be concise."
        )

        providers = [
            (self._call_mistral, "mistral-small"),
            (self._call_gemini, "gemini-2.0-flash"),
            (self._call_groq, "llama-3.3-70b-versatile")
        ]

        for call_func, model_name in providers:
            try:
                response_text = await call_func(prompt, model_name, is_json=False)
                if response_text:
                    return {
                        "type": "ai_comment",
                        "confidence": 0.95,
                        "severity": "low",
                        "details": {
                            "comment": response_text.strip(),
                            "ml_predictions_count": len(ml_predictions),
                            "analysis_type": "ML expert commentary",
                            "gemini_mode": "commentary"
                        }
                    }
            except Exception as e:
                print(f"Commentary failed with {model_name}: {e}")
                if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                    continue
                    
        self.last_ai_error = "All AI providers failed or exhausted quota."
        return None

    async def _call_mistral(self, prompt: str, model: str, is_json: bool) -> Optional[str]:
        if not self.mistral_client:
            raise Exception("Mistral not configured")
        # Use native async method per https://docs.mistral.ai/
        messages = [{"role": "user", "content": prompt}]
        
        response = await self.mistral_client.chat.complete_async(model=model, messages=messages)
        
        if not response:
            raise Exception("Empty response from Mistral")
        
        # Debug: log response structure
        print(f"Mistral response type: {type(response)}, has choices: {hasattr(response, 'choices')}")
        
        if not hasattr(response, 'choices') or not response.choices:
            raise Exception(f"Empty choices from Mistral. Response: {response}")
        
        if len(response.choices) == 0:
            raise Exception("Empty choices list from Mistral")
        
        choice = response.choices[0]
        if not hasattr(choice, 'message'):
            raise Exception("No message in Mistral response choice")
        
        content = choice.message.content
        if not content or not content.strip():
            raise Exception("Empty content from Mistral")
        
        return content.strip()

    async def _call_gemini(self, prompt: str, model: str, is_json: bool) -> Optional[str]:
        if not self.gemini_client: raise Exception("Gemini not configured")
        # Use native async method per https://ai.google.dev/gemini-api/docs
        response = await self.gemini_client.aio.models.generate_content(model=model, contents=prompt)
        if not response or not response.text:
            raise Exception("Empty response from Gemini")
        text = response.text.strip()
        if is_json:
            text = text.removeprefix('```json').removeprefix('```').removesuffix('```').strip()
        return text

    async def _call_groq(self, prompt: str, model: str, is_json: bool) -> Optional[str]:
        if not self.groq_client: raise Exception("Groq not configured")
        # Use native async client per https://console.groq.com/docs/overview
        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if is_json:
            kwargs["response_format"] = {"type": "json_object"}
            
        response = await self.groq_client.chat.completions.create(**kwargs)
        if not response or not response.choices:
            raise Exception("Empty response from Groq")
        content = response.choices[0].message.content
        if not content:
            raise Exception("Empty content from Groq")
        return content
    
    # Helper methods (same as before)
    async def _get_historical_data(self, db: AsyncSession, device_id: str, hours: int = 72) -> List[Dict]:
        result = await db.execute(text("""
            SELECT power, current, voltage, rpm, temp1, temp2, accel_x, accel_y, accel_z, 
                   motor_running, ts, energy, uptime_seconds
            FROM sensor_readings 
            WHERE device_id = :device_id AND ts >= NOW() - INTERVAL '72 hours'
            ORDER BY ts ASC
            LIMIT 300
        """), {"device_id": device_id})
        
        return [dict(row) for row in result.mappings()]
    
    def _prepare_features(self, historical_data: List[Dict]) -> np.ndarray:
        features = []
        for data in historical_data:
            if all(key in data and data[key] is not None for key in ['power', 'current', 'voltage', 'rpm', 'temp1', 'temp2']):
                feature_vector = [
                    data['power'] or 0,
                    data['current'] or 0,
                    data['voltage'] or 0,
                    data['rpm'] or 0,
                    data['temp1'] or 0,
                    data['temp2'] or 0,
                    (data['accel_x'] or 0) ** 2 + (data['accel_y'] or 0) ** 2 + (data['accel_z'] or 0) ** 2,
                    data['energy'] or 0,
                    data['uptime_seconds'] or 0,
                    1 if data['motor_running'] else 0
                ]
                features.append(feature_vector)
        
        return np.array(features) if features else np.array([])
    
    def _extract_current_features(self, payload: SensorPayload) -> np.ndarray:
        vibration_mag = payload.vibration.x**2 + payload.vibration.y**2 + payload.vibration.z**2
        return np.array([[
            payload.power.power,
            payload.power.current,
            payload.power.voltage,
            payload.motor.rpm,
            payload.temperature.t1,
            payload.temperature.t2,
            vibration_mag,
            payload.power.energy,
            payload.uptime,
            1 if payload.motor.running else 0
        ]])
    
    async def _fallback_predictions(self, payload: SensorPayload, historical_data: List[Dict]) -> List[dict]:
        """Fallback predictions when insufficient data for ML"""
        results = []
        
        # Basic threshold-based predictions
        avg_temp = (payload.temperature.t1 + payload.temperature.t2) / 2
        if avg_temp > payload.protection.maxTempC:
            results.append({
                "type": "overheating_basic",
                "confidence": 0.7,
                "severity": "medium",
                "details": {"avg_temp": avg_temp, "threshold": payload.protection.maxTempC}
            })
        
        if payload.power.current > payload.protection.stallCurrentA and payload.motor.rpm < payload.protection.minRpm:
            results.append({
                "type": "stall_risk_basic",
                "confidence": 0.8,
                "severity": "high",
                "details": {"current": payload.power.current, "rpm": payload.motor.rpm}
            })
        
        return results

# Global service instance
advanced_ml_prediction_service = AdvancedMLPredictionService()

async def run_advanced_ml_predictions(payload: SensorPayload, db: AsyncSession) -> List[dict]:
    """Main function to run advanced ML predictions"""
    return await advanced_ml_prediction_service.run_advanced_ml_predictions(payload, db)
