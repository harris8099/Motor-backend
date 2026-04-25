import asyncio
import json
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.schemas import SensorPayload
import google.generativeai as genai
from app.database import settings

class EnhancedPredictionService:
    def __init__(self):
        # Initialize Gemini AI if API key is available
        self.gemini_enabled = hasattr(settings, 'gemini_api_key') and settings.gemini_api_key
        if self.gemini_enabled:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-pro')
    
    async def run_enhanced_predictions(self, payload: SensorPayload, db: AsyncSession) -> List[dict]:
        """Run enhanced predictions with historical analysis and AI insights"""
        results = []
        device_id = payload.deviceId
        
        # Get historical data for trend analysis
        historical_data = await self._get_historical_data(db, device_id)
        
        # 1. Enhanced overheating prediction with trend analysis
        overheating_pred = await self._predict_overheating(payload, historical_data)
        if overheating_pred:
            results.append(overheating_pred)
        
        # 2. Advanced stall risk with power analysis
        stall_pred = await self._predict_stall_risk(payload, historical_data)
        if stall_pred:
            results.append(stall_pred)
        
        # 3. Bearing wear with vibration trends
        bearing_pred = await self._predict_bearing_wear(payload, historical_data)
        if bearing_pred:
            results.append(bearing_pred)
        
        # 4. Power efficiency analysis
        efficiency_pred = await self._predict_efficiency_anomaly(payload, historical_data)
        if efficiency_pred:
            results.append(efficiency_pred)
        
        # 5. Maintenance with usage patterns
        maintenance_pred = await self._predict_maintenance_need(payload, historical_data)
        if maintenance_pred:
            results.append(maintenance_pred)
        
        # 6. Gemini AI comprehensive analysis
        if self.gemini_enabled and len(historical_data) >= 10:
            ai_insight = await self._get_gemini_analysis(payload, historical_data, results)
            if ai_insight:
                results.append(ai_insight)
        
        return results
    
    async def _get_historical_data(self, db: AsyncSession, device_id: str, hours: int = 24) -> List[Dict]:
        """Get historical sensor data for trend analysis"""
        result = await db.execute(text("""
            SELECT power, current, voltage, rpm, temp1, temp2, accel_x, accel_y, accel_z, 
                   motor_running, ts, energy
            FROM sensor_readings 
            WHERE device_id = :device_id AND ts >= NOW() - INTERVAL '1 hours'
            ORDER BY ts DESC
            LIMIT 100
        """), {"device_id": device_id})
        
        return [dict(row) for row in result.mappings()]
    
    async def _predict_overheating(self, payload: SensorPayload, historical_data: List[Dict]) -> Optional[dict]:
        """Enhanced overheating prediction with trend analysis"""
        avg_temp = (payload.temperature.t1 + payload.temperature.t2) / 2
        
        # Current threshold check
        if avg_temp > payload.protection.maxTempC:
            confidence = min((avg_temp - payload.protection.maxTempC) / 30, 1.0)
            severity = "high" if avg_temp > (payload.protection.maxTempC + 10) else "medium"
            
            # Analyze temperature trend
            if len(historical_data) >= 5:
                recent_temps = [(d['temp1'] + d['temp2']) / 2 for d in historical_data[:5] if d['temp1'] and d['temp2']]
                if len(recent_temps) >= 3:
                    temp_trend = statistics.linear_regression(range(len(recent_temps)), recent_temps).slope
                    confidence = min(confidence + abs(temp_trend) * 0.1, 1.0)
            
            return {
                "type": "overheating",
                "confidence": confidence,
                "severity": severity,
                "details": {
                    "avg_temp": avg_temp,
                    "max_temp": payload.protection.maxTempC,
                    "trend": "increasing" if temp_trend > 0.1 else "stable"
                }
            }
        
        return None
    
    async def _predict_stall_risk(self, payload: SensorPayload, historical_data: List[Dict]) -> Optional[dict]:
        """Advanced stall risk prediction with power analysis"""
        current = payload.power.current
        rpm = payload.motor.rpm
        power = payload.power.power
        
        # Enhanced stall conditions
        stall_conditions = [
            current > payload.protection.stallCurrentA and rpm < payload.protection.minRpm,
            power > 0 and rpm < 100,  # Power but no rotation
            current > payload.protection.stallCurrentA * 0.8 and rpm < payload.protection.minRpm * 0.5
        ]
        
        if any(stall_conditions):
            confidence = 0.75
            if current > payload.protection.stallCurrentA * 1.2:
                confidence = 0.9
            
            # Analyze current trend
            if len(historical_data) >= 5:
                recent_currents = [d['current'] for d in historical_data[:5] if d['current']]
                if len(recent_currents) >= 3:
                    current_trend = statistics.linear_regression(range(len(recent_currents)), recent_currents).slope
                    if current_trend > 0.5:
                        confidence = min(confidence + 0.15, 1.0)
            
            return {
                "type": "stall_risk",
                "confidence": confidence,
                "severity": "high",
                "details": {
                    "current": current,
                    "rpm": rpm,
                    "power": power,
                    "stall_current": payload.protection.stallCurrentA,
                    "min_rpm": payload.protection.minRpm
                }
            }
        
        return None
    
    async def _predict_bearing_wear(self, payload: SensorPayload, historical_data: List[Dict]) -> Optional[dict]:
        """Bearing wear prediction with vibration trend analysis"""
        magnitude = (payload.vibration.x**2 + payload.vibration.y**2 + payload.vibration.z**2) ** 0.5
        
        # Vibration anomaly detection
        if len(historical_data) >= 10:
            historical_magnitudes = []
            for d in historical_data:
                if d['accel_x'] and d['accel_y'] and d['accel_z']:
                    mag = (d['accel_x']**2 + d['accel_y']**2 + d['accel_z']**2) ** 0.5
                    historical_magnitudes.append(mag)
            
            if len(historical_magnitudes) >= 5:
                avg_historical = statistics.mean(historical_magnitudes)
                std_historical = statistics.stdev(historical_magnitudes) if len(historical_magnitudes) > 1 else 0
                
                # Statistical anomaly detection
                z_score = (magnitude - avg_historical) / std_historical if std_historical > 0 else 0
                
                if magnitude > 2.5 or z_score > 2:
                    confidence = min((magnitude - 2.5) / 2.0, 1.0)
                    if z_score > 2:
                        confidence = min(confidence + 0.2, 1.0)
                    
                    # Analyze vibration trend
                    recent_mags = historical_magnitudes[:5]
                    if len(recent_mags) >= 3:
                        vibration_trend = statistics.linear_regression(range(len(recent_mags)), recent_mags).slope
                        if vibration_trend > 0.1:
                            confidence = min(confidence + 0.15, 1.0)
                    
                    return {
                        "type": "bearing_fault",
                        "confidence": confidence,
                        "severity": "medium" if confidence < 0.8 else "high",
                        "details": {
                            "vibration_magnitude": magnitude,
                            "historical_avg": avg_historical,
                            "z_score": z_score,
                            "trend": "increasing" if vibration_trend > 0.1 else "stable"
                        }
                    }
        
        elif magnitude > 2.5:  # Fallback to simple threshold
            return {
                "type": "bearing_fault",
                "confidence": min((magnitude - 2.5) / 2.0, 1.0),
                "severity": "medium",
                "details": {"vibration_magnitude": magnitude}
            }
        
        return None
    
    async def _predict_efficiency_anomaly(self, payload: SensorPayload, historical_data: List[Dict]) -> Optional[dict]:
        """Power efficiency anomaly prediction"""
        current = payload.power.current
        voltage = payload.power.voltage
        power = payload.power.power
        rpm = payload.motor.rpm
        
        if power > 0 and rpm > 0:
            # Calculate power efficiency (simplified)
            efficiency = (rpm * 0.001) / power if power > 0 else 0  # Simplified efficiency metric
            
            if len(historical_data) >= 10:
                historical_efficiency = []
                for d in historical_data:
                    if d['power'] and d['rpm'] and d['power'] > 0 and d['rpm'] > 0:
                        eff = (d['rpm'] * 0.001) / d['power']
                        historical_efficiency.append(eff)
                
                if len(historical_efficiency) >= 5:
                    avg_efficiency = statistics.mean(historical_efficiency)
                    
                    # Detect efficiency drop
                    if efficiency < avg_efficiency * 0.8:  # 20% drop
                        confidence = 1 - (efficiency / avg_efficiency)
                        return {
                            "type": "efficiency_drop",
                            "confidence": confidence,
                            "severity": "medium" if confidence < 0.7 else "high",
                            "details": {
                                "current_efficiency": efficiency,
                                "historical_avg": avg_efficiency,
                                "efficiency_loss": (avg_efficiency - efficiency) / avg_efficiency * 100,
                                "power": power,
                                "rpm": rpm
                            }
                        }
        
        return None
    
    async def _predict_maintenance_need(self, payload: SensorPayload, historical_data: List[Dict]) -> Optional[dict]:
        """Enhanced maintenance prediction with usage patterns"""
        total_hours = payload.maintenance.totalLifeCycleHours
        hours_limit = payload.maintenance.maintenanceHoursLimit
        
        # Time-based maintenance
        if total_hours > hours_limit:
            return {
                "type": "maintenance_due",
                "confidence": 1.0,
                "severity": "high",
                "details": {
                    "total_hours": total_hours,
                    "limit": hours_limit,
                    "overdue_by": total_hours - hours_limit
                }
            }
        
        # Predictive maintenance based on stress factors
        elif len(historical_data) >= 20:
            # Calculate stress factors
            high_temp_events = sum(1 for d in historical_data[:20] 
                                 if d['temp1'] and d['temp1'] > payload.protection.maxTempC * 0.9)
            high_current_events = sum(1 for d in historical_data[:20] 
                                    if d['current'] and d['current'] > payload.protection.stallCurrentA * 0.8)
            high_vibration_events = sum(1 for d in historical_data[:20] 
                                      if d['accel_x'] and d['accel_y'] and d['accel_z'])
            
            stress_score = (high_temp_events + high_current_events + high_vibration_events) / 60
            
            if stress_score > 0.3:  # High stress usage
                remaining_hours = hours_limit - total_hours
                predicted_maintenance_hours = remaining_hours * (1 - stress_score * 0.5)
                
                if predicted_maintenance_hours < 100:  # Less than 100 hours predicted
                    return {
                        "type": "maintenance_due",
                        "confidence": 0.8,
                        "severity": "medium",
                        "details": {
                            "total_hours": total_hours,
                            "limit": hours_limit,
                            "predicted_maintenance_hours": predicted_maintenance_hours,
                            "stress_score": stress_score,
                            "recommendation": "Schedule maintenance soon due to high-stress operation"
                        }
                    }
        
        return None
    
    async def _get_gemini_analysis(self, payload: SensorPayload, historical_data: List[Dict], predictions: List[dict]) -> Optional[dict]:
        """Get comprehensive AI analysis from Gemini"""
        try:
            # Prepare data summary for Gemini
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
                "predictions": predictions,
                "historical_summary": {
                    "data_points": len(historical_data),
                    "avg_rpm": statistics.mean([d['rpm'] for d in historical_data if d['rpm']]) if historical_data else 0,
                    "avg_power": statistics.mean([d['power'] for d in historical_data if d['power']]) if historical_data else 0,
                    "avg_temp": statistics.mean([(d['temp1'] + d['temp2']) / 2 for d in historical_data if d['temp1'] and d['temp2']]) if historical_data else 0
                }
            }
            
            prompt = f"""
            As an expert motor maintenance engineer, analyze this motor data and provide comprehensive insights:
            
            Current Readings: {json.dumps(data_summary['current_readings'], indent=2)}
            Active Predictions: {json.dumps(predictions, indent=2)}
            Historical Summary: {json.dumps(data_summary['historical_summary'], indent=2)}
            
            Provide:
            1. Overall motor health assessment (Excellent/Good/Fair/Poor/Critical)
            2. Key concerns and risks
            3. Recommended actions
            4. Priority level (Low/Medium/High/Critical)
            5. Estimated time until maintenance is needed
            
            Respond in JSON format with these exact keys: health_assessment, key_concerns, recommended_actions, priority, maintenance_timeline
            """
            
            response = self.model.generate_content(prompt)
            ai_analysis = json.loads(response.text)
            
            return {
                "type": "ai_analysis",
                "confidence": 0.9,
                "severity": ai_analysis.get('priority', 'medium').lower(),
                "details": ai_analysis
            }
            
        except Exception as e:
            print(f"Gemini AI analysis failed: {e}")
            return None

# Global service instance
enhanced_prediction_service = EnhancedPredictionService()

async def run_enhanced_predictions(payload: SensorPayload, db: AsyncSession) -> List[dict]:
    """Main function to run enhanced predictions"""
    return await enhanced_prediction_service.run_enhanced_predictions(payload, db)
