import subprocess
import time
import sys

def main():
    print("🚀 Starting NEXUS High-Availability ERP & Watchdog System...")
    
    # 1. Start Secondary ERP
    erp_process = subprocess.Popen([sys.executable, "server.py"])
    print("-> Secondary ERP running on http://localhost:8001")
    
    time.sleep(2)
    
    # 2. Start Primary Watchdog
    watchdog_process = subprocess.Popen([sys.executable, "primary_server.py"])
    print("-> Primary Watchdog running on http://localhost:8000")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down all servers...")
        erp_process.terminate()
        watchdog_process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()