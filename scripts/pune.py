from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
from bs4 import BeautifulSoup as bs
from location import get_location_info, get_contact_info
import os, sys, django, re, time
from pathlib import Path
from selenium.webdriver.chrome.options import Options

bedav_dir = str(Path(os.getcwd()).parent) + '/api'
sys.path.append(bedav_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from hospitals.models import Hospital, Equipment

def get_pune_data(driver):
  def get_nap(string):
    """Get name, address phone"""

    split_string = string.split("Address:")
    name = split_string[0].strip()

    split_string = split_string[1].split("Number:")
    address = split_string[0].strip()

    split_string = split_string[1].split("Last Updated Date:")
    phone = split_string[0].strip()

    if '/' in phone:
      phone = phone.split('/')[0].strip()
    elif ',' in phone:
      phone = phone.split(',')[0].strip()

    return (name, address, phone)

  data = pd.DataFrame(columns=["name", "category", "gen_total",  "oxy_total", "ICU_total", "vent_total", "gen_occupied", "oxy_occupied", "ICU_occupied", "vent_occupied", "address", "phone"])

  while True:
    page_source = driver.page_source
    source = bs(page_source, 'html.parser')


    table = source.find('table', {"id": "tablegrid"})
    table = table.find("tbody")
    rows = table.find_all("tr")

    for row in rows:
      columns = row.find_all("td") 
      columns = [column.text.strip() for column in columns]
      name, address, phone = get_nap(columns[4])
      gen_total = int(columns[9]) + int(columns[11])

      if 'No Data Available' in phone or phone in ('', '0', 'NA'):
        phone = 'NA'

      if 'No Data Available' in address or len(address) <= 22:
        address = "NA"

      print(name, address, phone)

      phone = re.sub(r'[ ]+', ' ', phone)
      phone = phone.split(" ")[0]

      hospital = {
        "name": name,
        "category": columns[3],
        "address": address,
        "phone": phone,
        "gen_total": gen_total,
        "gen_occupied": gen_total - (int(columns[10]) + int(columns[12])),
        "oxy_total": int(columns[11]),
        "oxy_occupied": int(columns[11]) - int(columns[12]),
        "ICU_total": int(columns[13]),
        "ICU_occupied": int(columns[13]) - int(columns[14]),
        "vent_total": int(columns[15]),
        "vent_occupied": int(columns[15]) - int(columns[16])
      }

      data = data.append(hospital, ignore_index=True)

    try:
      next_button = driver.find_element_by_class_name('pagelink')
      next_button = next_button.find_elements_by_tag_name("a")[-1]

      print(next_button.text)
      if next_button.text.strip().lower() == "last":
        break

      next_button.click()
    except NoSuchElementException:
      break

  data[["gen_total", "oxy_total", "ICU_total", "vent_total", "gen_occupied", "oxy_occupied", "ICU_occupied", "vent_occupied"]] = data[["gen_total", "oxy_total", "ICU_total", "vent_total", "gen_occupied", "oxy_occupied", "ICU_occupied", "vent_occupied"]].applymap(lambda value: re.sub(',', '', str(value))).apply(pd.to_numeric, errors="coerce")
  data["address"] = data.address.str.replace(r' +', ' ', regex=True)
  data['name'] = data.name.str.replace(r' +', ' ', regex=True)

  return data

def add_pune_hospitals(data, locality_id):
  for index, item in data[['name', 'category', 'phone', 'address']].iterrows():
    print(index)
    hospital = item.to_dict()

    def hospital_exists(name):
      obj = Hospital.objects.filter(name=name, locality_id=locality_id).first()

      if obj is None:
        return False

      return True

    if hospital_exists(hospital["name"]):
      continue

    args = {
      "name": hospital["name"],
      "city": "Pune",
      "state": "Maharashtra",
      "address": None if hospital["address"] == "NA" else hospital["address"]
    }

    location_info = get_location_info(**args)
    hospital = { **hospital, **location_info}

    contact_info = get_contact_info(hospital["place_id"]) if 'place_id' in hospital.keys() else {}
    hospital = {**hospital, **contact_info}

    if item.loc["phone"] != "NA":
      hospital["phone"] = item.loc["phone"]

    hospital["district"] = "Pune"
    hospital["locality_id"] = locality_id

    obj = Hospital(**hospital)
    obj.save()

def upadate_pune_data(data, locality_id):
  current_time = time.time()
  for index, item in data.iterrows():
    equipment = []

    item = item.to_dict()

    name = item["name"]
    hospital = Hospital.objects.filter(name=name, locality_id=locality_id).first()
    print(name, hospital)

    available = {
      "gen": item['gen_total'] - item['gen_occupied'],
      "ICU": item['ICU_total'] - item['ICU_occupied'],
      "vent": item['vent_total'] - item['vent_occupied'],
      "oxy": item['oxy_total'] - item['oxy_occupied']
    }

    for category, value in available.items():
      equipment.append({
        "available": value,
        "category": category,
        "total": item[category + "_total"],
        "time": current_time,
        "branch": hospital
      })

    for x in equipment:
      obj = Equipment(**x)
      obj.save()

def get_all():
  options = Options()
  options.headless = True
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  driver = webdriver.Chrome(options=options)
  driver.get("https://www.divcommpunecovid.com/ccsbeddashboard/hsr")
  ids = {
    1: 2,
    2: 6,
    3: 5,
    4: 4,
    5: 3,
  }

  for i in range(1,6):
    input_value = f'phc_center_{i}'
    driver.execute_script(f'document.getElementById("phc_center_1").value = "{input_value}"')
    btn = driver.find_element_by_id("employee_0")
    btn.click()
    time.sleep(2)
    data = get_pune_data(driver)
    print(data)
    add_pune_hospitals(data, ids[i])
    upadate_pune_data(data, ids[i])

get_all()
