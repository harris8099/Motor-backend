"""
Prebuilt ML Models Implementation
Easy-to-implement models that provide immediate value
"""

import asyncio
import json
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.schemas import SensorPayload
from sklearn.neighbors import LocalOutlierFactor
from sklearn.covariance import EllipticEnvelope
from sklearn.linear_model import Ridge, Lasso
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler

class PrebuiltModelsService:
    def __init__(self):
        # Initialize prebuilt models
        self.lof = LocalOutlierFactor(n_neighbors=20, contamination=0.1, novelty=True)
        self.elliptic = EllipticEnvelope(contamination=0.1, random_state=42)
        self.ridge = Ridge(alpha=1.0, random_state=42)
        self.lasso = Lasso(alpha=0.1, random_state=42)
        self.gbr_regressor = GradientBoostingRegressor(n_estimators=50, random_state=42)
        self.gbr_classifier = GradientBoostingClassifier(n_estimators=50, random_state=42)
        self.svr = SVR(kernel='rbf', C=1.0, gamma='scale')
        self.scaler = StandardScaler()
        
    async def run_prebuilt_predictions(self, payload: SensorPayload, db: AsyncSession) -> List[dict]:
        """Run predictions using prebuilt models"""
        results = []
        device_id = payload.deviceId
        
        # Get historical data
        historical_data = await self._get_historical_data(db, device_id, hours=24)
        
        if len(historical_data) < 10:
            return []
        
        # Prepare features
        features = self._prepare_features(historical_data)
        current_features = self._extract_current_features(payload)
        
        # 1. Local Outlier Factor - Anomaly Detection
        lof_pred = await self._predict_lof_anomaly(features, current_features, historical_data)
        if lof_pred:
            results.append(lof_pred)
        
        # 2. Elliptic Envelope - Anomaly Detection
        elliptic_pred = await self._predict_elliptic_anomaly(features, current_features, historical_data)
        if elliptic_pred:
            results.append(elliptic_pred)
        
        # 3. Ridge Regression - Temperature Prediction
        ridge_pred = await self._predict_temperature_ridge(features, current_features, payload)
        if ridge_pred:
            results.append(ridge_pred)
        
        # 4. Lasso Regression - Power Prediction
        lasso_pred = await self._predict_power_lasso(features, current_features, payload)
        if lasso_pred:
            results.append(lasso_pred)
        
        # 5. Gradient Boosting - Vibration Prediction
        gbr_pred = await self._predict_vibration_gbr(features, current_features, historical_data)
        if gbr_pred:
            results.append(gbr_pred)
        
        # 6. SVR - Efficiency Prediction
        svr_pred = await self._predict_efficiency_svr(features, current_features, historical_data)
        if svr_pred:
            results.append(svr_pred)
        
        return results
    
    async def _predict_lof_anomaly(self, features: np.ndarray, current_features: np.ndarray, historical_data: List[Dict]) -> Optional[dict]:
        """Local Outlier Factor for anomaly detection"""
        if len(features) < 15:
            return None
        
        try:
            # Fit LOF on historical data
            self.lof.fit(features)
            
            # Predict anomaly score for current data
            anomaly_score = self.lof.decision_function(current_features)[0]
            is_anomaly = self.lof.predict(current_features)[0] == -1
            
            if is_anomaly or anomaly_score < -0.5:
                confidence = min(abs(anomaly_score) + 0.3, 1.0)
                
                # Find most anomalous features
                feature_importance = np.abs(current_features[0] - np.mean(features, axis=0))
                most_anomalous_idx = np.argmax(feature_importance)
                feature_names = ['power', 'current', 'voltage', 'rpm', 'temp1', 'temp2', 'vibration', 'energy', 'uptime', 'motor_status']
                
                return {
                    "type": "lof_anomaly_detection",
                    "confidence": confidence,
                    "severity": "high" if anomaly_score < -1.0 else "medium",
                    "details": {
                        "lof_score": float(anomaly_score),
                        "anomalous_feature": feature_names[most_anomalous_idx],
                        "feature_deviation": float(feature_importance[most_anomalous_idx]),
                        "model_type": "Local Outlier Factor",
                        "neighbors_used": 20
                    }
                }
        except Exception as e:
            print(f"LOF prediction failed: {e}")
        
        return None
    
    async def _predict_elliptic_anomaly(self, features: np.ndarray, current_features: np.ndarray, historical_data: List[Dict]) -> Optional[dict]:
        """Elliptic Envelope for anomaly detection"""
        if len(features) < 15:
            return None
        
        try:
            # Fit Elliptic Envelope on historical data
            self.elliptic.fit(features)
            
            # Predict anomaly score for current data
            anomaly_score = self.elliptic.decision_function(current_features)[0]
            is_anomaly = self.elliptic.predict(current_features)[0] == -1
            
            if is_anomaly or anomaly_score < 0:
                confidence = min(abs(anomaly_score) + 0.4, 1.0)
                
                # Mahalanobis distance for additional insight
                mahalanobis_dist = self.elliptic.mahalanobis(current_features)[0]
                
                return {
                    "type": "elliptic_anomaly_detection",
                    "confidence": confidence,
                    "severity": "high" if anomaly_score < -2.0 else "medium",
                    "details": {
                        "elliptic_score": float(anomaly_score),
                        "mahalanobis_distance": float(mahalanobis_dist),
                        "model_type": "Elliptic Envelope",
                        "statistical_method": "Gaussian-based"
                    }
                }
        except Exception as e:
            print(f"Elliptic prediction failed: {e}")
        
        return None
    
    async def _predict_temperature_ridge(self, features: np.ndarray, current_features: np.ndarray, payload: SensorPayload) -> Optional[dict]:
        """Ridge Regression for temperature prediction"""
        if len(features) < 20:
            return None
        
        try:
            # Prepare temperature prediction data
            X = features[:, [0, 1, 3, 6]]  # power, current, rpm, vibration
            y_temp1 = features[:, 4]  # temp1
            y_temp2 = features[:, 5]  # temp2
            
            # Train Ridge models
            self.ridge.fit(X, y_temp1)
            future_temp1 = self.ridge.predict(current_features[0, [0, 1, 3, 6]].reshape(1, -1))[0]
            
            self.ridge.fit(X, y_temp2)
            future_temp2 = self.ridge.predict(current_features[0, [0, 1, 3, 6]].reshape(1, -1))[0]
            
            avg_predicted_temp = (future_temp1 + future_temp2) / 2
            current_avg_temp = (payload.temperature.t1 + payload.temperature.t2) / 2
            
            if avg_predicted_temp > payload.protection.maxTempC:
                confidence = min((avg_predicted_temp - payload.protection.maxTempC) / 30, 1.0)
                
                return {
                    "type": "ridge_temperature_prediction",
                    "confidence": confidence,
                    "severity": "high" if avg_predicted_temp > payload.protection.maxTempC + 10 else "medium",
                    "details": {
                        "predicted_temp1": float(future_temp1),
                        "predicted_temp2": float(future_temp2),
                        "avg_predicted_temp": float(avg_predicted_temp),
                        "current_avg_temp": float(current_avg_temp),
                        "temp_threshold": payload.protection.maxTempC,
                        "model_type": "Ridge Regression",
                        "regularization_alpha": 1.0
                    }
                }
        except Exception as e:
            print(f"Ridge temperature prediction failed: {e}")
        
        return None
    
    async def _predict_power_lasso(self, features: np.ndarray, current_features: np.ndarray, payload: SensorPayload) -> Optional[dict]:
        """Lasso Regression for power prediction"""
        if len(features) < 20:
            return None
        
        try:
            # Prepare power prediction data
            X = features[:, [1, 3, 4, 5, 6]]  # current, rpm, temp1, temp2, vibration
            y_power = features[:, 0]  # power
            
            # Train Lasso model
            self.lasso.fit(X, y_power)
            predicted_power = self.lasso.predict(current_features[0, [1, 3, 4, 5, 6]].reshape(1, -1))[0]
            
            current_power = payload.power.power
            power_deviation = abs(predicted_power - current_power) / current_power if current_power > 0 else 0
            
            if power_deviation > 0.2:  # 20% deviation
                confidence = min(power_deviation, 1.0)
                
                # Get feature coefficients for insight
                feature_names = ['current', 'rpm', 'temp1', 'temp2', 'vibration']
                coefficients = dict(zip(feature_names, self.lasso.coef_))
                
                return {
                    "type": "lasso_power_prediction",
                    "confidence": confidence,
                    "severity": "high" if power_deviation > 0.4 else "medium",
                    "details": {
                        "predicted_power": float(predicted_power),
                        "actual_power": float(current_power),
                        "power_deviation_percent": float(power_deviation * 100),
                        "model_type": "Lasso Regression",
                        "feature_coefficients": {k: float(v) for k, v in coefficients.items()},
                        "regularization_alpha": 0.1
                    }
                }
        except Exception as e:
            print(f"Lasso power prediction failed: {e}")
        
        return None
    
    async def _predict_vibration_gbr(self, features: np.ndarray, current_features: np.ndarray, historical_data: List[Dict]) -> Optional[dict]:
        """Gradient Boosting for vibration prediction"""
        if len(features) < 25:
            return None
        
        try:
            # Prepare vibration prediction data
            X = features[:, [0, 1, 3, 4, 5]]  # power, current, rpm, temp1, temp2
            y_vibration = features[:, 6]  # vibration (squared magnitude)
            
            # Train Gradient Boosting model
            self.gbr_regressor.fit(X, y_vibration)
            predicted_vibration = self.gbr_regressor.predict(current_features[0, [0, 1, 3, 4, 5]].reshape(1, -1))[0]
            
            current_vibration = current_features[0, 6]
            vibration_increase = (predicted_vibration - current_vibration) / current_vibration if current_vibration > 0 else 0
            
            if vibration_increase > 0.3:  # 30% increase predicted
                confidence = min(vibration_increase, 1.0)
                
                # Feature importance
                feature_names = ['power', 'current', 'rpm', 'temp1', 'temp2']
                importance = dict(zip(feature_names, self.gbr_regressor.feature_importances_))
                
                return {
                    "type": "gbr_vibration_prediction",
                    "confidence": confidence,
                    "severity": "high" if vibration_increase > 0.6 else "medium",
                    "details": {
                        "predicted_vibration": float(predicted_vibration),
                        "current_vibration": float(current_vibration),
                        "vibration_increase_percent": float(vibration_increase * 100),
                        "model_type": "Gradient Boosting Regressor",
                        "feature_importance": {k: float(v) for k, v in importance.items()},
                        "n_estimators": 50
                    }
                }
        except Exception as e:
            print(f"GBR vibration prediction failed: {e}")
        
        return None
    
    async def _predict_efficiency_svr(self, features: np.ndarray, current_features: np.ndarray, historical_data: List[Dict]) -> Optional[dict]:
        """SVR for efficiency prediction"""
        if len(features) < 30:
            return None
        
        try:
            # Calculate efficiency for historical data
            efficiency_data = []
            X_data = []
            
            for i in range(len(features)):
                power, rpm = features[i, 0], features[i, 3]
                if power > 0 and rpm > 0:
                    efficiency = rpm / power
                    efficiency_data.append(efficiency)
                    X_data.append(features[i, [0, 1, 3, 4, 5]])  # power, current, rpm, temp1, temp2
            
            if len(efficiency_data) < 20:
                return None
            
            X_data = np.array(X_data)
            efficiency_data = np.array(efficiency_data)
            
            # Scale features for SVR
            X_scaled = self.scaler.fit_transform(X_data)
            
            # Train SVR model
            self.svr.fit(X_scaled, efficiency_data)
            
            # Predict current efficiency
            current_X = current_features[0, [0, 1, 3, 4, 5]].reshape(1, -1)
            current_X_scaled = self.scaler.transform(current_X)
            predicted_efficiency = self.svr.predict(current_X_scaled)[0]
            
            # Calculate actual efficiency
            current_power, current_rpm = current_features[0, 0], current_features[0, 3]
            actual_efficiency = current_rpm / current_power if current_power > 0 else 0
            
            efficiency_drop = (actual_efficiency - predicted_efficiency) / actual_efficiency if actual_efficiency > 0 else 0
            
            if efficiency_drop > 0.15:  # 15% efficiency drop
                confidence = min(efficiency_drop * 2, 1.0)
                
                return {
                    "type": "svr_efficiency_prediction",
                    "confidence": confidence,
                    "severity": "high" if efficiency_drop > 0.3 else "medium",
                    "details": {
                        "predicted_efficiency": float(predicted_efficiency),
                        "actual_efficiency": float(actual_efficiency),
                        "efficiency_drop_percent": float(efficiency_drop * 100),
                        "model_type": "Support Vector Regression",
                        "kernel": "rbf",
                        "support_vectors": len(self.svr.support_vectors_)
                    }
                }
        except Exception as e:
            print(f"SVR efficiency prediction failed: {e}")
        
        return None
    
    # Helper methods
    async def _get_historical_data(self, db: AsyncSession, device_id: str, hours: int = 24) -> List[Dict]:
        result = await db.execute(text("""
            SELECT power, current, voltage, rpm, temp1, temp2, accel_x, accel_y, accel_z, 
                   motor_running, ts, energy, uptime_seconds
            FROM sensor_readings 
            WHERE device_id = :device_id AND ts >= NOW() - INTERVAL '24 hours'
            ORDER BY ts ASC
            LIMIT 200
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

# Global service instance
prebuilt_models_service = PrebuiltModelsService()

async def run_prebuilt_predictions(payload: SensorPayload, db: AsyncSession) -> List[dict]:
    """Main function to run prebuilt model predictions"""
    return await prebuilt_models_service.run_prebuilt_predictions(payload, db)
