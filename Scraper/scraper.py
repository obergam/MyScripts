import requests
from bs4 import BeautifulSoup

URL = 'https://www.bedbathandbeyond.com/store/product/breville-reg-the-barista-express-trade-espresso-machine/3244573?opbthead=true&ta=typeahead&keyword=breville-espresso'

headers = {"User-Agent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'}

page = requests.get(URL, headers=headers)

soup1 = BeautifulSoup(page.content, "html.parser")

soup2 = BeautifulSoup(soup1.prettify(), "html.parser")

title = soup2.find(id= "productTitle")

converted_price = [0:5]
print(title.strip())

