# Edge collector (HTTP) - simula 4 instancias de sensores y envía lecturas vía HTTP al backend
import time, os, requests, json, logging, sys
from sensors.voltage_sensor import VoltageSensor
from sensors.current_sensor import CurrentSensor
from sensors.temperature_sensor import TemperatureSensor
from sensors.irradiance_sensor import IrradianceSensor
from sensors.soc_sensor import SOCSensor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8000/ingest')
INTERVAL = int(os.environ.get('INTERVAL', '2'))
MAX_RETRIES = 3
RETRY_DELAY = 2

# Configuración de 4 instancias de sensores con características diferentes
SENSOR_INSTANCES = [
    {
        'site_id': 'site_001',
        'voltage': {'min_v': 46.0, 'max_v': 52.0, 'noise': 0.12},
        'current': {'min_a': 0.5, 'max_a': 5.0, 'noise': 0.1}
    },
    {
        'site_id': 'site_002',
        'voltage': {'min_v': 46.5, 'max_v': 51.5, 'noise': 0.1},
        'current': {'min_a': 0.3, 'max_a': 4.5, 'noise': 0.08}
    },
    {
        'site_id': 'site_003',
        'voltage': {'min_v': 47.0, 'max_v': 53.0, 'noise': 0.12},
        'current': {'min_a': 0.8, 'max_a': 5.5, 'noise': 0.12}
    },
    {
        'site_id': 'site_004',
        'voltage': {'min_v': 45.5, 'max_v': 51.0, 'noise': 0.09},
        'current': {'min_a': 0.2, 'max_a': 4.0, 'noise': 0.07}
    },
    {
        'site_id': 'site_005',
        'voltage': {'min_v': 46.2, 'max_v': 52.2, 'noise': 0.11},
        'current': {'min_a': 0.4, 'max_a': 4.8, 'noise': 0.09}
    },
    {
        'site_id': 'site_006',
        'voltage': {'min_v': 46.8, 'max_v': 52.6, 'noise': 0.11},
        'current': {'min_a': 0.6, 'max_a': 5.2, 'noise': 0.1}
    },
    {
        'site_id': 'site_007',
        'voltage': {'min_v': 45.8, 'max_v': 51.3, 'noise': 0.1},
        'current': {'min_a': 0.3, 'max_a': 4.2, 'noise': 0.08}
    },
    {
        'site_id': 'site_008',
        'voltage': {'min_v': 47.2, 'max_v': 53.2, 'noise': 0.12},
        'current': {'min_a': 0.7, 'max_a': 5.7, 'noise': 0.12}
    }
]

def init_sensors():
    """Initialize 8 sensor instances with different characteristics."""
    sensors = []
    for config in SENSOR_INSTANCES:
        v_config = config['voltage']
        c_config = config['current']
        v_sensor = VoltageSensor(
            name=f"voltage_{config['site_id']}",
            min_v=v_config['min_v'],
            max_v=v_config['max_v'],
            noise=v_config['noise']
        )
        c_sensor = CurrentSensor(
            name=f"current_{config['site_id']}",
            min_a=c_config['min_a'],
            max_a=c_config['max_a'],
            noise=c_config['noise']
        )

        # extra sensors for richer telemetry
        t_sensor = TemperatureSensor(name=f"temp_{config['site_id']}")
        irr_sensor = IrradianceSensor(name=f"irr_{config['site_id']}")
        soc_sensor = SOCSensor(name=f"soc_{config['site_id']}")

        sensors.append({
            'site_id': config['site_id'],
            'voltage': v_sensor,
            'current': c_sensor,
            'temperature': t_sensor,
            'irradiance': irr_sensor,
            'soc': soc_sensor
        })
        
        logger.info('Initialized sensor instance for %s', config['site_id'])
    
    return sensors

def main():
    logger.info('Edge collector starting...')
    logger.info('Backend URL: %s', BACKEND_URL)
    logger.info('Send interval: %d seconds', INTERVAL)
    logger.info('Initializing 8 sensor instances...')
    
    sensors = init_sensors()
    
    retry_count = 0
    
    while True:
        try:
            # Send readings for all 8 sensor instances
            for sensor_set in sensors:
                # Read voltage and current first so we can calculate power locally
                v = sensor_set['voltage'].read()
                c = sensor_set['current'].read()

                # compute instantaneous power (W)
                try:
                    power_val = round(float(v['value']) * float(c['value']), 3)
                except Exception:
                    power_val = 0.0

                readings = [
                    v,
                    c,
                    {
                        'sensor': f"power_{sensor_set['site_id']}",
                        'type': 'power',
                        'value': power_val
                    },
                    sensor_set['temperature'].read(),
                    sensor_set['irradiance'].read(),
                    sensor_set['soc'].read()
                ]

                data = {
                    'site_id': sensor_set['site_id'],
                    'timestamp': int(time.time()),
                    'readings': readings
                }
                
                resp = requests.post(BACKEND_URL, json=data, timeout=5)
                
                if resp.status_code == 200:
                    logger.debug('Successfully sent readings from %s', sensor_set['site_id'])
                    retry_count = 0
                else:
                    logger.warning('Backend returned status %d for %s: %s', 
                                 resp.status_code, sensor_set['site_id'], resp.text)
                    retry_count += 1
                    
        except requests.exceptions.Timeout:
            logger.error('Request timeout after 5 seconds')
            retry_count += 1
        except requests.exceptions.ConnectionError as e:
            logger.error('Connection error: %s', e)
            retry_count += 1
        except Exception as e:
            logger.error('Unexpected error: %s', e)
            retry_count += 1
        
        # Check if we've exceeded max retries
        if retry_count >= MAX_RETRIES:
            logger.error('Max retries exceeded, waiting longer before next attempt')
            time.sleep(RETRY_DELAY * 2)
            retry_count = 0
        else:
            time.sleep(INTERVAL)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Edge collector stopped by user')
        sys.exit(0)
    except Exception as e:
        logger.critical('Fatal error: %s', e)
        sys.exit(1)
