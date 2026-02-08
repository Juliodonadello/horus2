# Edge collector (HTTP) - simula sensores y envía lecturas vía HTTP al backend
import time, os, requests, json, logging, sys
from sensors.voltage_sensor import VoltageSensor
from sensors.current_sensor import CurrentSensor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8000/ingest')
INTERVAL = int(os.environ.get('INTERVAL', '5'))
MAX_RETRIES = 3
RETRY_DELAY = 2

def main():
    logger.info('Edge collector starting...')
    logger.info('Backend URL: %s', BACKEND_URL)
    logger.info('Send interval: %d seconds', INTERVAL)
    
    v = VoltageSensor()
    c = CurrentSensor()
    
    retry_count = 0
    
    while True:
        try:
            data = {
                'site_id': os.environ.get('SITE_ID', 'site_001'),
                'timestamp': int(time.time()),
                'readings': [v.read(), c.read()]
            }
            
            resp = requests.post(BACKEND_URL, json=data, timeout=5)
            
            if resp.status_code == 200:
                logger.info('Successfully sent %d readings', len(data['readings']))
                retry_count = 0  # Reset retry count on success
            else:
                logger.warning('Backend returned status %d: %s', resp.status_code, resp.text)
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
