import requests
from bs4 import BeautifulSoup
import pandas as pd
import json

url = "https://caniwin.com/texasholdem/preflop/heads-up.php"
page = requests.get(url)

soup = BeautifulSoup(page.text, 'lxml')
soup

ev_table = soup.find('table', {'class':'pocketTable'})

headers = ['Rank', 'Name', 'EV', 'Win %', 'Tie %','Occur %', 'Cumulative %']

mydata = pd.DataFrame(columns = headers)

for j in ev_table.find_all('tr')[1:]:
    row_data = j.find_all('td')
    row = [i.text for i in row_data]
    length = len(mydata)
    mydata.loc[length] = row

result_dict = {}

for n in range(169):
    result_dict[mydata['Name'][n]] = float(mydata['Win %'][n])/100

with open('preflop_ev.json', 'w') as convert_file:
    convert_file.write(json.dumps(result_dict))











