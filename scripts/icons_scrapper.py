from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import requests
import pandas as pd
from datetime import datetime
import json



url = 'https://www.tradingview.com/markets/stocks-egypt/market-movers-all-stocks/'

snitch = webdriver.Chrome()
snitch.get(url)

# Close popup if it exists
try:
    close_btn = WebDriverWait(snitch, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH,'/html/body/div[7]/div[2]/div[2]/div/div/div/div[2]')
        )
    )
    close_btn.click()
    print("Popup closed.")
except:
    print("Popup not found OR already closed.")

time.sleep(2)

# Click "Load more" button
while True:
    try:
        # Wait for the "Load more" button to appear
        load_more = WebDriverWait(snitch, 5).until(
            EC.element_to_be_clickable(
                (By.XPATH, '/html/body/div[2]/main/div/div[2]/div/div[4]/div/div[3]/button')
            )
        )
        load_more.click()
        print("Load more clicked. Waiting for new rows...")
        time.sleep(2)  # wait for new rows to load

    except:
        # No more buttons found → exit loop
        print("No more 'Load more' button found. All rows loaded.")
        break

icon_table = {}

# Locate all table rows
rows = snitch.find_elements(By.XPATH, "//table/tbody/tr")
print("Rows found:", len(rows))

for row in rows:
    cells = row.find_elements(By.TAG_NAME, "td")
    if not cells:
        continue

    # Extract symbol text
    symbol = cells[0].text.strip().replace("\n"," ")

    # Extract icon (inside <img>)
    try:
        img = cells[0].find_element(By.TAG_NAME, "img")
        icon_url = img.get_attribute("src")
    except:
        icon_url = None

    icon_table[symbol] = icon_url

snitch.quit()

# Convert to DataFrame
df_icons = pd.DataFrame(list(icon_table.items()), columns=["Symbol", "IconURL"])
print(df_icons)
df_icons.to_csv('icons.csv', index=False)