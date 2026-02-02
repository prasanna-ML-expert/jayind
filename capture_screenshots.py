import os
import time
from playwright.sync_api import sync_playwright

URL_MAP = {
    "quantum": "https://www.tradingview.com/chart/Ls0KjlAU/",
    "power_management_chips": "https://www.tradingview.com/chart/iHFjEihw/",
    "uas_defense_robotics": "https://www.tradingview.com/chart/bc9LVHG4/",
    "lidar_sensing": "https://www.tradingview.com/chart/y66m0tBS/",
    "service_robotics": "https://www.tradingview.com/chart/yXkclwxW/",
    "autonomous_driving": "https://www.tradingview.com/chart/gNgM9ZRC/",
    "space_launch_systems": "https://www.tradingview.com/chart/n7Ak2qQF/",
    "earth_observation": "https://www.tradingview.com/chart/ee3TjuCV/",
    "ev_charging_infrastructure": "https://www.tradingview.com/chart/L8RehbH2/",
    "evtol_air_mobility": "https://www.tradingview.com/chart/P1TUSyPv/",
    "hydrogen_fuel_cells": "https://www.tradingview.com/chart/LPs0FIja/",
    "new_nuclear_energy": "https://www.tradingview.com/chart/6RnjuCRf/",
    "batteries_storage_tech": "https://www.tradingview.com/chart/bmnG95Wd/",
    "batteries_storage_sw": "https://www.tradingview.com/chart/ThpDElE5/",
    "battery_materials_mining": "https://www.tradingview.com/chart/kAOiJNLK/",
    "Hyperscalers": "https://www.tradingview.com/chart/XFDtWdGp/",
    "Mining": "https://www.tradingview.com/chart/rPD36MDH/",
    "Mag7" : "https://www.tradingview.com/chart/S2Cbsl8n/"
}

def run():
    with sync_playwright() as p:
        # Using Firefox as requested
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        for name, url in URL_MAP.items():
            try:
                print(f"Opening {name}...")
                page.goto(url, wait_until="load")
                
                # Wait for the chart canvas to actually appear in the DOM
                page.wait_for_selector("canvas.chart-gui-wrapper", timeout=30000)
                
                # The 60-second delay you requested for data to populate
                print(f"Waiting 60s for {name} data...")
                time.sleep(60) 
                
                filename = f"screenshots/{name}.png"
                page.screenshot(path=filename)
                print(f"Successfully saved {filename}")
                
            except Exception as e:
                print(f"Failed to capture {name}: {e}")

        browser.close()

if __name__ == "__main__":
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")
    run()
