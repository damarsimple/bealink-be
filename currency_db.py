import json
import requests
from bs4 import BeautifulSoup
import threading
import time
from langchain.tools import tool

URL = "https://fiskal.kemenkeu.go.id/informasi-publik/kurs-pajak"

currencyDB = {}
currencyBasedOn = ""
currencyEffectiveDate = ""

def load_currency_data():
    global currencyDB, currencyBasedOn, currencyEffectiveDate
    # Make the GET request
    response = requests.get(URL)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        em = soup.find("p", attrs={'class': 'text-muted'})
        effective_date = em.text.replace("Tanggal Berlaku: ", "").strip()
        strong = soup.find("strong")
        rule = strong.text.strip()
        
        # Find the table
        table = soup.find('table')
        # Create a list to store the exchange rates
        exchange_rates = []
        
        # Check if the table is found
        if table:
            # Find all rows in the table body
            rows = table.find('tbody').find_all('tr')
            for row in rows:
                # Find all the columns in the row
                cols = row.find_all('td')
                if len(cols) != 4:
                    continue # Skip rows that do not have exactly 4 columns.
                
                # Extract data and store it in a dictionary
                exchange_rate = {
                    "No": cols[0].text.strip(),
                    "Mata Uang": cols[1].text.strip(),
                    "Nilai": cols[2].text.strip(),
                    "Perubahan": cols[3].text.strip()
                }
                # Add the dictionary to the list
                exchange_rates.append(exchange_rate)

            # Update global variables
            currencyBasedOn = rule
            currencyEffectiveDate = effective_date
            currencyDB.clear()
            for rate in exchange_rates:
                splt = str(rate["Mata Uang"]).splitlines()[1]
                currencyDB[splt] = {
                    **rate,
                    "currencyRuleBasedOn": currencyBasedOn,
                    "currencyEffectiveDate": currencyEffectiveDate
                }
            print("Currency data updated successfully.")
        else:
            print("Table not found in the HTML content")
    else:
        print(f"Failed to retrieve the web page. Status code: {response.status_code}")

@tool
def get_currency_detail(currency_code: str) -> dict:
    """Get the currency from IDR to other currency"""
    return currencyDB.get(currency_code, {})

def periodic_task(interval, func, *args):
    """Run func() every interval seconds."""
    while True:
        func(*args)
        time.sleep(interval)

# Initialize currency data on import
load_currency_data()

# Start periodic task to refresh currency data every hour (3600 seconds)
threading.Thread(target=periodic_task, args=(3600, load_currency_data), daemon=True).start()