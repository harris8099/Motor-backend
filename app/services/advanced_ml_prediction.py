import asyncio
import json
import statistics
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.schemas import SensorPayload
import google.generativeai as genai
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
        # Gemini AI Configuration
        self.gemini_enabled = hasattr(settings, 'gemini_api_key') and settings.gemini_api_key
        self.gemini_mode = getattr(settings, 'gemini_mode', 'commentary')  # 'commentary', 'prediction', 'disabled'
        if self.gemini_enabled and self.gemini_mode != 'disabled':
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        
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
        
        # 7. Gemini AI (Configurable Mode)
        if self.gemini_enabled and self.gemini_mode != 'disabled':
            if self.gemini_mode == 'prediction':
                # Gemini makes predictions
                gemini_pred = await self._get_gemini_predictions(payload, historical_data, results)
            else:
                # Gemini provides commentary (default)
                gemini_pred = await self._get_gemini_commentary(payload, historical_data, results)
            
            if gemini_pred:
                results.append(gemini_pred)
        
        return results
    
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
            dominant_freq_idx = np.argmax(fft_magnitudes[1:len(fft_magnitudes)//2]) + 1
            
            # 5. NASA Bearing Health Index (BHI)
            # Based on NASA's research on bearing fault detection
            health_indicators = {
                'rms_level': rms_total,
                'crest_factor': np.mean([crest_factor_x, crest_factor_y, crest_factor_z]),
                'kurtosis': np.mean([kurtosis_x, kurtosis_y, kurtosis_z]),
                'frequency_content': np.mean(fft_magnitudes),
                'dominant_frequency': dominant_freq_idx
            }
            
            # Normalize health indicators (0-1 scale, higher is worse)
            normalized_indicators = {}
            normalized_indicators['rms_norm'] = min(rms_total / 20.0, 1.0)  # Normalize against 20 units
            normalized_indicators['crest_norm'] = min((np.mean([crest_factor_x, crest_factor_y, crest_factor_z]) - 3.0) / 5.0, 1.0)
            normalized_indicators['kurtosis_norm'] = min(max((np.mean([kurtosis_x, kurtosis_y, kurtosis_z]) - 3.0) / 10.0, 0), 1.0)
            normalized_indicators['freq_norm'] = min(np.mean(fft_magnitudes) / 100.0, 1.0)
            
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
    
    async def _get_gemini_predictions(self, payload: SensorPayload, historical_data: List[Dict], ml_predictions: List[dict]) -> Optional[dict]:
        """Gemini AI makes predictions (not just commentary)"""
        try:
            # Prepare comprehensive data for Gemini
            data_summary = {
                "current_readings": {
                    "rpm": payload.motor.rpm,
                    "current": payload.power.current,
                    "voltage": payload.power.voltage,
                    "power": payload.power.power,
                    "temp1": payload.temperature.t1,
                    "temp2": payload.temperature.t2,
                    "vibration": {
                        "x": payload.vibration.x,
                        "y": payload.vibration.y,
                        "z": payload.vibration.z
                    }
                },
                "operational_context": {
                    "uptime": payload.uptime,
                    "motor_running": payload.motor.running,
                    "maintenance_hours": payload.maintenance.totalLifeCycleHours,
                    "maintenance_limit": payload.maintenance.maintenanceHoursLimit
                },
                "protection_limits": {
                    "max_current": payload.protection.maxCurrentA,
                    "max_temp": payload.protection.maxTempC,
                    "min_rpm": payload.protection.minRpm
                }
            }
            
            prompt = f"""
            As an expert motor reliability engineer, analyze this motor data and make specific predictions about future failures and maintenance needs.
            
            Current Motor Data: {json.dumps(data_summary, indent=2)}
            ML Model Predictions: {json.dumps(ml_predictions, indent=2)}
            
            Provide predictions for:
            1. Likelihood of failure in next 24 hours (percentage)
            2. Most likely failure mode (bearing, overheating, stall, electrical)
            3. Recommended maintenance actions
            4. Critical parameters to monitor
            5. Expected remaining useful life in days
            
            Be specific and actionable. This is for industrial motor maintenance planning.
            
            Respond in JSON format with these exact keys: failure_probability_24h, likely_failure_mode, maintenance_actions, critical_parameters, estimated_rul_days
            """
            
            response = self.model.generate_content(prompt)
            ai_predictions = json.loads(response.text)
            
            return {
                "type": "gemini_ai_predictions",
                "confidence": 0.85,
                "severity": ai_predictions.get('failure_probability_24h', 0) > 0.5 and "high" or "medium",
                "details": {
                    **ai_predictions,
                    "prediction_mode": "gemini_ai",
                    "based_on_ml_analysis": True,
                    "recommendation_priority": "high" if ai_predictions.get('failure_probability_24h', 0) > 0.7 else "medium"
                }
            }
            
        except Exception as e:
            print(f"Gemini AI prediction failed: {e}")
            return None
    
    async def _get_gemini_commentary(self, payload: SensorPayload, historical_data: List[Dict], ml_predictions: List[dict]) -> Optional[dict]:
        """Gemini AI provides commentary on ML predictions"""
        try:
            ml_summary = {
                "device_id": payload.deviceId,
                "current_status": {
                    "rpm": payload.motor.rpm,
                    "power": payload.power.power,
                    "temperature": (payload.temperature.t1 + payload.temperature.t2) / 2,
                    "current": payload.power.current
                },
                "ml_predictions": [
                    {
                        "type": pred["type"],
                        "confidence": pred["confidence"],
                        "severity": pred["severity"]
                    } for pred in ml_predictions
                ],
                "data_quality": {
                    "historical_data_points": len(historical_data),
                    "analysis_period": "72 hours"
                }
            }
            
            prompt = f"""
            You are an expert industrial engineer commenting on advanced ML-based motor analysis. The ML models have generated these predictions:
            
            Device Status: {json.dumps(ml_summary['current_status'], indent=2)}
            ML Predictions: {json.dumps(ml_summary['ml_predictions'], indent=2)}
            Data Quality: {json.dumps(ml_summary['data_quality'], indent=2)}
            
            Provide a brief expert comment (2-3 sentences) on the ML analysis results. Focus on:
            1. Overall assessment of the ML predictions
            2. Key concerns or insights
            3. Recommended priority level
            
            Keep it concise and professional. Do not make new predictions - only comment on the ML results.
            """
            
            response = self.model.generate_content(prompt)
            
            return {
                "type": "gemini_ai_commentary",
                "confidence": 0.95,
                "severity": "low",
                "details": {
                    "comment": response.text.strip(),
                    "ml_predictions_count": len(ml_predictions),
                    "analysis_type": "ML expert commentary",
                    "gemini_mode": "commentary"
                }
            }
            
        except Exception as e:
            print(f"Gemini commentary failed: {e}")
            return None
    
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
