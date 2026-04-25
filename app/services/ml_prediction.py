import asyncio
import json
import statistics
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.schemas import SensorPayload
from google import genai
from app.database import settings
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

class MLPredictionService:
    def __init__(self):
        # Initialize Gemini AI for commenting only
        self.gemini_enabled = hasattr(settings, 'gemini_api_key') and settings.gemini_api_key
        if self.gemini_enabled:
            self.client = genai.Client(api_key=settings.gemini_api_key)
        
        # Initialize ML models
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        
    async def run_ml_predictions(self, payload: SensorPayload, db: AsyncSession) -> List[dict]:
        """Run ML-based predictions with Gemini commenting"""
        results = []
        device_id = payload.deviceId
        
        # Get historical data for ML training
        historical_data = await self._get_historical_data(db, device_id, hours=48)
        
        if len(historical_data) < 10:
            # Fallback to basic predictions if insufficient data
            return await self._fallback_predictions(payload, historical_data)
        
        # Prepare ML features
        features = self._prepare_features(historical_data)
        current_features = self._extract_current_features(payload)
        
        # 1. Anomaly Detection using Isolation Forest
        anomaly_pred = await self._detect_anomalies(features, current_features, historical_data)
        if anomaly_pred:
            results.append(anomaly_pred)
        
        # 2. Time Series Prediction for Overheating
        overheating_pred = await self._predict_overheating_ml(features, current_features, payload)
        if overheating_pred:
            results.append(overheating_pred)
        
        # 3. Bearing Failure Prediction using Vibration Analysis
        bearing_pred = await self._predict_bearing_failure_ml(features, current_features, historical_data)
        if bearing_pred:
            results.append(bearing_pred)
        
        # 4. Stall Risk Prediction using Power Analysis
        stall_pred = await self._predict_stall_risk_ml(features, current_features, payload)
        if stall_pred:
            results.append(stall_pred)
        
        # 5. Efficiency Degradation Prediction
        efficiency_pred = await self._predict_efficiency_degradation_ml(features, current_features, historical_data)
        if efficiency_pred:
            results.append(efficiency_pred)
        
        # 6. Maintenance Prediction using Usage Patterns
        maintenance_pred = await self._predict_maintenance_ml(features, current_features, payload, historical_data)
        if maintenance_pred:
            results.append(maintenance_pred)
        
        # Note: Gemini AI commentary is now available on-demand via separate endpoint
        # This keeps ML predictions fast while allowing optional AI analysis
        return results
    
    async def get_gemini_commentary(self, payload: SensorPayload, db: AsyncSession) -> Optional[dict]:
        """Get on-demand Gemini AI commentary (called separately from automatic predictions)"""
        if not self.gemini_enabled:
            return None
        
        try:
            # Get recent predictions for context
            result = await db.execute(text("""
                SELECT prediction_type, confidence, severity, details
                FROM predictions
                WHERE device_id = :device_id
                ORDER BY ts DESC LIMIT 10
            """), {"device_id": payload.deviceId})
            recent_predictions = [dict(row) for row in result.mappings()]
            
            # Get historical data
            historical_data = await self._get_historical_data(db, payload.deviceId, hours=48)
            
            return await self._get_gemini_comment(payload, historical_data, recent_predictions)
        except Exception as e:
            print(f"On-demand Gemini commentary failed: {e}")
            return None
    
    async def _get_historical_data(self, db: AsyncSession, device_id: str, hours: int = 48) -> List[Dict]:
        """Get historical sensor data for ML training"""
        result = await db.execute(text("""
            SELECT power, current, voltage, rpm, temp1, temp2, accel_x, accel_y, accel_z, 
                   motor_running, ts, energy, uptime_seconds
            FROM sensor_readings 
            WHERE device_id = :device_id AND ts >= NOW() - INTERVAL '48 hours'
            ORDER BY ts ASC
            LIMIT 200
        """), {"device_id": device_id})
        
        return [dict(row) for row in result.mappings()]
    
    def _prepare_features(self, historical_data: List[Dict]) -> np.ndarray:
        """Prepare features for ML models"""
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
                    (data['accel_x'] or 0) ** 2 + (data['accel_y'] or 0) ** 2 + (data['accel_z'] or 0) ** 2,  # Vibration magnitude squared
                    data['energy'] or 0,
                    data['uptime_seconds'] or 0,
                    1 if data['motor_running'] else 0
                ]
                features.append(feature_vector)
        
        return np.array(features) if features else np.array([])
    
    def _extract_current_features(self, payload: SensorPayload) -> np.ndarray:
        """Extract features from current sensor payload"""
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
    
    async def _detect_anomalies(self, features: np.ndarray, current_features: np.ndarray, historical_data: List[Dict]) -> Optional[dict]:
        """Detect anomalies using Isolation Forest"""
        if len(features) < 10:
            return None
        
        try:
            # Fit Isolation Forest on historical data
            self.isolation_forest.fit(features)
            
            # Predict anomaly score for current data
            anomaly_score = self.isolation_forest.decision_function(current_features)[0]
            is_anomaly = self.isolation_forest.predict(current_features)[0] == -1
            
            if is_anomaly or anomaly_score < -0.1:
                confidence = min(abs(anomaly_score) + 0.5, 1.0)
                
                # Find which features are most anomalous
                feature_importance = np.abs(current_features[0] - np.mean(features, axis=0))
                most_anomalous_feature_idx = np.argmax(feature_importance)
                feature_names = ['power', 'current', 'voltage', 'rpm', 'temp1', 'temp2', 'vibration', 'energy', 'uptime', 'motor_status']
                
                return {
                    "type": "anomaly_detection",
                    "confidence": confidence,
                    "severity": "high" if anomaly_score < -0.2 else "medium",
                    "details": {
                        "anomaly_score": float(anomaly_score),
                        "anomalous_feature": feature_names[most_anomalous_feature_idx],
                        "feature_deviation": float(feature_importance[most_anomalous_feature_idx]),
                        "current_value": float(current_features[0][most_anomalous_feature_idx]),
                        "historical_mean": float(np.mean(features, axis=0)[most_anomalous_feature_idx])
                    }
                }
        except Exception as e:
            print(f"Anomaly detection failed: {e}")
        
        return None
    
    async def _predict_overheating_ml(self, features: np.ndarray, current_features: np.ndarray, payload: SensorPayload) -> Optional[dict]:
        """Predict overheating using time series analysis"""
        if len(features) < 20:
            return None
        
        try:
            # Extract temperature series
            temp_series = features[:, 4]  # temp1 column
            current_temp = current_features[0, 4]
            
            # Linear regression for trend prediction
            X = np.arange(len(temp_series)).reshape(-1, 1)
            y = temp_series
            
            model = LinearRegression()
            model.fit(X, y)
            
            # Predict next 6 hours (assuming 5-minute intervals)
            future_steps = 72  # 6 hours * 12 steps per hour
            future_X = np.arange(len(temp_series), len(temp_series) + future_steps).reshape(-1, 1)
            future_temps = model.predict(future_X)
            
            # Check if temperature will exceed threshold
            max_temp_threshold = payload.protection.maxTempC
            max_predicted_temp = np.max(future_temps)
            
            if max_predicted_temp > max_temp_threshold:
                time_to_threshold = np.argmax(future_temps > max_temp_threshold) * 5  # minutes
                confidence = min((max_predicted_temp - max_temp_threshold) / 20, 1.0)
                
                return {
                    "type": "overheating_prediction",
                    "confidence": confidence,
                    "severity": "high" if time_to_threshold < 60 else "medium",
                    "details": {
                        "current_temp": float(current_temp),
                        "max_predicted_temp": float(max_predicted_temp),
                        "temp_threshold": max_temp_threshold,
                        "time_to_threshold_minutes": int(time_to_threshold),
                        "trend_slope": float(model.coef_[0]),
                        "current_r2": float(model.score(X, y))
                    }
                }
        except Exception as e:
            print(f"Overheating prediction failed: {e}")
        
        return None
    
    async def _predict_bearing_failure_ml(self, features: np.ndarray, current_features: np.ndarray, historical_data: List[Dict]) -> Optional[dict]:
        """Predict bearing failure using vibration analysis"""
        if len(features) < 30:
            return None
        
        try:
            # Extract vibration magnitude series
            vibration_series = features[:, 6]  # vibration magnitude squared
            current_vibration = current_features[0, 6]
            
            # Calculate statistical features
            vibration_mean = np.mean(vibration_series)
            vibration_std = np.std(vibration_series)
            
            # Z-score for current vibration
            z_score = (current_vibration - vibration_mean) / vibration_std if vibration_std > 0 else 0
            
            # Trend analysis
            X = np.arange(len(vibration_series)).reshape(-1, 1)
            model = LinearRegression()
            model.fit(X, vibration_series)
            trend_slope = model.coef_[0]
            
            # Predict future vibration levels
            future_steps = 48  # 4 hours ahead
            future_X = np.arange(len(vibration_series), len(vibration_series) + future_steps).reshape(-1, 1)
            future_vibration = model.predict(future_X)
            
            # Risk assessment
            risk_factors = []
            if abs(z_score) > 2:
                risk_factors.append(f"High Z-score: {z_score:.2f}")
            if trend_slope > 0.1:
                risk_factors.append(f"Increasing trend: {trend_slope:.4f}")
            if np.max(future_vibration) > vibration_mean + 2 * vibration_std:
                risk_factors.append("Predicted anomaly in future")
            
            if len(risk_factors) > 0:
                confidence = min(len(risk_factors) * 0.3 + abs(z_score) * 0.1, 1.0)
                
                return {
                    "type": "bearing_failure_prediction",
                    "confidence": confidence,
                    "severity": "high" if confidence > 0.7 else "medium",
                    "details": {
                        "current_vibration": float(current_vibration),
                        "vibration_mean": float(vibration_mean),
                        "vibration_std": float(vibration_std),
                        "z_score": float(z_score),
                        "trend_slope": float(trend_slope),
                        "risk_factors": risk_factors,
                        "predicted_max_vibration": float(np.max(future_vibration))
                    }
                }
        except Exception as e:
            print(f"Bearing failure prediction failed: {e}")
        
        return None
    
    async def _predict_stall_risk_ml(self, features: np.ndarray, current_features: np.ndarray, payload: SensorPayload) -> Optional[dict]:
        """Predict stall risk using power and current analysis"""
        if len(features) < 20:
            return None
        
        try:
            current_power = current_features[0, 0]
            current_current = current_features[0, 1]
            current_rpm = current_features[0, 3]
            
            # Historical patterns
            power_series = features[:, 0]
            current_series = features[:, 1]
            rpm_series = features[:, 3]
            
            # Calculate efficiency trends
            efficiency_series = []
            for i in range(len(features)):
                if power_series[i] > 0 and rpm_series[i] > 0:
                    efficiency_series.append(rpm_series[i] / power_series[i])
            
            if len(efficiency_series) < 10:
                return None
            
            # Current efficiency
            current_efficiency = current_rpm / current_power if current_power > 0 else 0
            
            # Efficiency trend
            X = np.arange(len(efficiency_series)).reshape(-1, 1)
            model = LinearRegression()
            model.fit(X, efficiency_series)
            efficiency_trend = model.coef_[0]
            
            # Risk factors
            risk_factors = []
            risk_score = 0
            
            if current_current > payload.protection.stallCurrentA * 0.8:
                risk_factors.append(f"High current: {current_current:.2f}A")
                risk_score += 0.3
            
            if current_rpm < payload.protection.minRpm * 1.2:
                risk_factors.append(f"Low RPM: {current_rpm:.0f}")
                risk_score += 0.3
            
            if current_efficiency < np.mean(efficiency_series) * 0.8:
                risk_factors.append(f"Low efficiency: {current_efficiency:.4f}")
                risk_score += 0.2
            
            if efficiency_trend < -0.001:
                risk_factors.append(f"Decreasing efficiency trend: {efficiency_trend:.6f}")
                risk_score += 0.2
            
            if risk_score > 0.4:
                confidence = min(risk_score + 0.2, 1.0)
                
                return {
                    "type": "stall_risk_prediction",
                    "confidence": confidence,
                    "severity": "high" if risk_score > 0.7 else "medium",
                    "details": {
                        "current_power": float(current_power),
                        "current_current": float(current_current),
                        "current_rpm": float(current_rpm),
                        "current_efficiency": float(current_efficiency),
                        "efficiency_trend": float(efficiency_trend),
                        "risk_score": float(risk_score),
                        "risk_factors": risk_factors,
                        "stall_current_threshold": payload.protection.stallCurrentA
                    }
                }
        except Exception as e:
            print(f"Stall risk prediction failed: {e}")
        
        return None
    
    async def _predict_efficiency_degradation_ml(self, features: np.ndarray, current_features: np.ndarray, historical_data: List[Dict]) -> Optional[dict]:
        """Predict efficiency degradation using time series analysis"""
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
            
            # Polynomial regression for efficiency trend
            X = np.arange(len(efficiency_series)).reshape(-1, 1)
            y = np.array(efficiency_series)
            
            # Fit polynomial (degree 2 for curvature)
            coeffs = np.polyfit(X.flatten(), y, 2)
            poly_model = np.poly1d(coeffs)
            
            # Predict future efficiency
            future_steps = 48  # 4 hours ahead
            future_X = np.arange(len(efficiency_series), len(efficiency_series) + future_steps)
            future_efficiency = poly_model(future_X)
            
            # Calculate degradation rate
            recent_efficiency = np.mean(efficiency_series[-10:])
            baseline_efficiency = np.mean(efficiency_series[:10])
            degradation_rate = (baseline_efficiency - recent_efficiency) / baseline_efficiency
            
            # Predict future degradation
            min_predicted_efficiency = np.min(future_efficiency)
            future_degradation = (baseline_efficiency - min_predicted_efficiency) / baseline_efficiency
            
            if degradation_rate > 0.1 or future_degradation > 0.2:
                confidence = min(degradation_rate * 2 + future_degradation, 1.0)
                
                return {
                    "type": "efficiency_degradation_prediction",
                    "confidence": confidence,
                    "severity": "high" if future_degradation > 0.3 else "medium",
                    "details": {
                        "current_efficiency": float(current_efficiency),
                        "baseline_efficiency": float(baseline_efficiency),
                        "degradation_rate": float(degradation_rate),
                        "future_degradation": float(future_degradation),
                        "min_predicted_efficiency": float(min_predicted_efficiency),
                        "efficiency_trend": "decreasing" if coeffs[1] < 0 else "stable"
                    }
                }
        except Exception as e:
            print(f"Efficiency degradation prediction failed: {e}")
        
        return None
    
    async def _predict_maintenance_ml(self, features: np.ndarray, current_features: np.ndarray, payload: SensorPayload, historical_data: List[Dict]) -> Optional[dict]:
        """Predict maintenance needs using usage pattern analysis"""
        try:
            # Usage patterns analysis
            total_hours = payload.maintenance.totalLifeCycleHours
            hours_limit = payload.maintenance.maintenanceHoursLimit
            
            # Stress factor calculation
            stress_events = 0
            total_data_points = len(features)
            
            for i in range(len(features)):
                temp_stress = 1 if features[i, 4] > payload.protection.maxTempC * 0.9 else 0
                current_stress = 1 if features[i, 1] > payload.protection.stallCurrentA * 0.8 else 0
                vibration_stress = 1 if features[i, 6] > np.mean(features[:, 6]) + 2 * np.std(features[:, 6]) else 0
                
                stress_events += temp_stress + current_stress + vibration_stress
            
            stress_ratio = stress_events / (total_data_points * 3) if total_data_points > 0 else 0
            
            # Time-based prediction
            time_remaining = hours_limit - total_hours
            base_prediction = total_hours > hours_limit
            
            # Adjust prediction based on stress
            if stress_ratio > 0.3:
                # High stress usage - reduce remaining time
                adjusted_time_remaining = time_remaining * (1 - stress_ratio * 0.5)
                maintenance_needed = adjusted_time_remaining < 100  # Less than 100 hours
            else:
                adjusted_time_remaining = time_remaining
                maintenance_needed = base_prediction
            
            if maintenance_needed or adjusted_time_remaining < 200:
                confidence = 0.8 if stress_ratio > 0.3 else 0.6
                if base_prediction:
                    confidence = 1.0
                
                return {
                    "type": "maintenance_prediction_ml",
                    "confidence": confidence,
                    "severity": "high" if adjusted_time_remaining < 50 else "medium",
                    "details": {
                        "total_hours": total_hours,
                        "hours_limit": hours_limit,
                        "time_remaining": float(adjusted_time_remaining),
                        "stress_ratio": float(stress_ratio),
                        "stress_events": stress_events,
                        "usage_pattern": "high_stress" if stress_ratio > 0.3 else "normal",
                        "recommended_action": "Schedule maintenance soon" if adjusted_time_remaining < 100 else "Plan maintenance within next month"
                    }
                }
        except Exception as e:
            print(f"Maintenance prediction failed: {e}")
        
        return None
    
    async def _get_gemini_comment(self, payload: SensorPayload, historical_data: List[Dict], ml_predictions: List[dict]) -> Optional[dict]:
        """Get Gemini AI comments on ML predictions (not for making predictions)"""
        try:
            # Prepare ML prediction summary for Gemini
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
                    "analysis_period": "48 hours"
                }
            }
            
            prompt = f"""
            You are an expert industrial engineer commenting on ML-based motor analysis. The ML models have generated these predictions:
            
            Device Status: {json.dumps(ml_summary['current_status'], indent=2)}
            ML Predictions: {json.dumps(ml_summary['ml_predictions'], indent=2)}
            Data Quality: {json.dumps(ml_summary['data_quality'], indent=2)}
            
            Provide a brief expert comment (2-3 sentences) on the ML analysis results. Focus on:
            1. Overall assessment of the ML predictions
            2. Key concerns or insights
            3. Recommended priority level
            
            Keep it concise and professional. Do not make new predictions - only comment on the ML results.
            """
            
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            
            return {
                "type": "ai_comment",
                "confidence": 0.95,
                "severity": "low",  # Comments are informational
                "details": {
                    "comment": response.text.strip(),
                    "ml_predictions_count": len(ml_predictions),
                    "analysis_type": "ML-based expert commentary"
                }
            }
            
        except Exception as e:
            print(f"Gemini commenting failed: {e}")
            return None
    
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
ml_prediction_service = MLPredictionService()

async def run_ml_predictions(payload: SensorPayload, db: AsyncSession) -> List[dict]:
    """Main function to run ML-based predictions"""
    return await ml_prediction_service.run_ml_predictions(payload, db)
