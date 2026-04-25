import requests
import json

def test_api():
    API_URL = 'http://localhost:8000'
    API_KEY = 'your-secret-key-same-as-esp32'
    headers = {'x-api-key': API_KEY, 'Content-Type': 'application/json'}

    try:
        # Test devices endpoint
        print('Testing devices endpoint...')
        devices_resp = requests.get(f'{API_URL}/devices', headers=headers)
        if devices_resp.status_code == 200:
            devices = devices_resp.json()
            print(f'✓ Found {len(devices)} devices')
            for device in devices[:3]:
                print(f'  - {device["id"]}: {device["name"]}')
        else:
            print(f'✗ Devices endpoint failed: {devices_resp.status_code}')
            return
        
        # Test predictions endpoint for first device
        if devices and len(devices) > 0:
            device_id = devices[0]['id']
            print(f'\nTesting predictions endpoint for {device_id}...')
            pred_resp = requests.get(f'{API_URL}/predictions/{device_id}?limit=5', headers=headers)
            if pred_resp.status_code == 200:
                predictions = pred_resp.json()
                print(f'✓ Found {len(predictions.get("data", []))} predictions')
                for pred in predictions.get('data', [])[:3]:
                    print(f'  - {pred["prediction_type"]}: {pred["confidence"]:.2f} ({pred["severity"]})')
            else:
                print(f'✗ Predictions endpoint failed: {pred_resp.status_code}')
        
        # Test sensor data endpoint
        if devices and len(devices) > 0:
            device_id = devices[0]['id']
            print(f'\nTesting sensor data endpoint for {device_id}...')
            data_resp = requests.get(f'{API_URL}/data/{device_id}?limit=5', headers=headers)
            if data_resp.status_code == 200:
                data = data_resp.json()
                print(f'✓ Found {len(data.get("data", []))} sensor readings')
                if data.get('data'):
                    latest = data['data'][0]
                    print(f'  - Latest: RPM={latest.get("rpm")}, Temp={latest.get("temp1")}°C, Power={latest.get("power")}kW')
            else:
                print(f'✗ Data endpoint failed: {data_resp.status_code}')
        
        print('\n🌐 API endpoints are working! Check the frontend at http://localhost:5173')
        print('📱 Navigate to a device page to see ML predictions in action!')
        
    except requests.exceptions.ConnectionError:
        print('✗ Backend server is not running.')
        print('Start it with: python -m uvicorn app.main:app --reload')
    except Exception as e:
        print(f'✗ Error testing API: {e}')

if __name__ == "__main__":
    test_api()
