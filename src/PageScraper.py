#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fileencoding=utf-8

import time
import os
import os.path
import sqlite3
import sys
import io

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

import pickle
import bs4 as bs
import re
import json

urlDict = {
	'login':'https://badoo.com/signin/',
	'encounters': 'https://badoo.com/encounters/',
	'search': 'https://badoo.com/search/',
	'signup': 'https://badoo.com/signin/',
	'not_found': 'https://badoo.com/not_found'
}

class PageScraper:
    
    class REASON:
		OK = 0
		PAGE_DOESNT_EXIST = 1
		CAPCHA = 2

	def SignIn(driver):
		driver.get(urlDict['login'])
			print('Current page: {-2}'.format(driver.current_url))

cookiesFile = 'cookies.pkl'
if(os.path.exists(cookiesFile)):
cookies = pickle.load(open(cookiesFile, "rb"))
	print('Loading cookies: {0}', len(cookies))
	for cookie in cookies:
		driver.add_cookie(cookie)
	print('Signing in')
	driver.get('https://badoo.com/encounters/')
else:
# Uncomment this part of code if you want auto sign in with no cookies.
# 	user = ''
# 	password = ''
# 	while('encounters' not in driver.current_url):
# 		InputElement(driver, 'email', user)
# 		InputElement(driver, 'password', password)
# 		xpath = '/html/body/div[2]/div[1]/div[2]/div/div[2]/div[1]/form/div[5]/div/button'
# 		ClickElement(driver, xpath)
	print('You should sign in - selenium have no cookies')
	while('encounters' not in driver.current_url):
		try:
			wait = WebDriverWait(driver, 10)
			wait.until(EC.url_contains('encounters'))
			break
		except:
			return False

cookies = driver.get_cookies()
print('Dumping cookies: {0}', len(cookies))
pickle.dump(cookies, open(cookiesFile,"wb"))

def ParseProfileAttribute(soup, profile, dictionaryName, tagName, className):
elem = soup.find(tagName, class_=className)
profile[dictionaryName] = ''
if(elem is None):
	return
profile[dictionaryName] = elem.text.strip(' ')

def ParseProfileRangeAttribute(soup, profile, dictionaryName, tagName, className):
elements = soup.find_all(tagName, class_=className)
profile[dictionaryName] = []
for elem in elements:
	profile[dictionaryName] += [elem.text]

def ParseProfile(driver, profile):
profileUrl = profile['link']
driver.get(profileUrl)
if(driver.current_url == urlDict['signup']):
	print("Something went wrong cookie not applied.")
	return False

while(True):
	try:
		xpath = '/html/body/div[2]/div[2]/main/div[1]/div/div[1]/header'
		elem = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
		break
	except:
		if(driver.current_url == urlDict['not_found']):
			return REASON.PAGE_DOESNT_EXIST
		else:
			return REASON.CAPCHA

soup = bs.BeautifulSoup(driver.page_source, 'html.parser')
if(soup.find('div', class_='promo') is not None):
	print('Invalid link %s, removing' % profileUrl)

ParseProfileAttribute(soup, profile, 'name', 'span', 'profile-header__name')
ParseProfileAttribute(soup, profile, 'age', 'span', 'profile-header__age')
if('age' in profile):
	profile['age'] = re.sub(r'\D', '', profile['age'])
ParseProfileRangeAttribute(soup, profile, 'interests', 'span', 'pill__text')
ParseProfileAttribute(soup, profile, 'about', 'span', 'profile-section__txt')
ParseProfileAttribute(soup, profile, 'education', 'div', 'profile-section__txt profile-section__txt--education grey')
ParseProfileAttribute(soup, profile, 'city', 'span', 'js-location-label')
if profile.get('city'):
	profile['city'] = re.sub(',.*$', '', profile['city'])
return REASON.OK

def getProfileDataId(profileId):
cur.execute("SELECT id FROM profile_data WHERE profile_id=:profile_id;",{
		"profile_id": profileId
})
profileDataId = -1
row = cur.fetchone()
profileDataId = row[0] if row else -1
return profileDataId

def fillTable(profile, profileDataId, cur):
if profileDataId == -1:
	cur.execute("INSERT INTO profile_data(id) VALUES (null)")
	profileDataId = cur.lastrowid

interestsIds = []
for interest in profile['interests']:
	cur.execute("SELECT id FROM interest WHERE name=:interest;",{
			"interest": interest
	})
	row = cur.fetchone()
	if(row):
		interestsIds.append(row[0])
	else:
		cur.execute("INSERT INTO interest(id, name) VALUES (null, :interest)",{
			"interest": interest
		})
		interestsIds.append(cur.lastrowid)

education = profile['education']
educationId = -1
if education != '':
	cur.execute("SELECT id FROM education WHERE name=:education;",{
			"education": education
	})
	row = cur.fetchone()
	if(row):
		educationId = row[0]
	else:
		cur.execute("INSERT INTO education(id, name) VALUES (null, :education)",{
			"education": education
		})
		educationId = cur.lastrowid

city = profile['city']
cityId = -1
if city != '':
	cur.execute("SELECT id FROM city WHERE name=:city;",{
			"city": city
	})
	row = cur.fetchone()
	if(row):
		cityId = row[0]
	else:
		cur.execute("INSERT INTO city(id, name) VALUES (null, :city)",{
			"city": city
		})
		cityId = cur.lastrowid


for interestId in interestsIds:
	cur.execute('''
		SELECT profile_data_id FROM profile_interest 
		WHERE profile_data_id=:profile_data_id AND interest_id=:interest_id;
		''',{
			"profile_data_id": profileDataId,
			"interest_id": interestId
		})
	row = cur.fetchone()
	if(row is None):
		cur.execute("INSERT INTO profile_interest(profile_data_id, interest_id) VALUES (:profile_data_id, :interest_id)",{
			"profile_data_id": profileDataId,
			"interest_id": interestId 
		})

cur.execute('''
	UPDATE profile_data SET 
	age=?,
	name=?,
	profile_id=?,
	education_id=?,
	city_id=?,
	about=?
	WHERE Id=?
	''', (profile['age'], profile['name'], profile['id'], educationId, cityId, profile['about'], profileDataId))
return True

def removeProfileById(cur, id):
cur.execute('''
	DELETE FROM profile where id = ?
''', (id,))

firefoxProfile = webdriver.FirefoxProfile()
# 1 - Allow all images
# 2 - Block all images
# 3 - Block 3rd party images 
firefoxProfile.set_preference("permissions.default.image", 3)
driver = webdriver.Firefox(firefox_profile=firefoxProfile)
wait = WebDriverWait(driver, 3)
driver.start_client()
SignIn(driver)
filePath = 'id_data.db'
con = sqlite3.connect(filePath)
cur = con.cursor()
cur.execute('''
	CREATE TABLE IF NOT EXISTS education(
		id INTEGER PRIMARY KEY,
		name TEXT
	);''')
cur.execute('''
	CREATE TABLE IF NOT EXISTS interest(
		id INTEGER PRIMARY KEY,
		name TEXT
	);''')
cur.execute('''
	CREATE TABLE IF NOT EXISTS city(
		id INTEGER PRIMARY KEY,
		name TEXT
	);''')
cur.execute('''
	CREATE TABLE IF NOT EXISTS profile_interest(
		profile_data_id INTEGER,
		interest_id INTEGER,
		FOREIGN KEY (profile_data_id) REFERENCES profile_data(id),
		FOREIGN KEY (interest_id) REFERENCES interest(id)
	);''')
cur.execute('''
	CREATE TABLE IF NOT EXISTS profile_data(
		id INTEGER PRIMARY KEY,
		age INTEGER,
		name TEXT,
		profile_id INTEGER,
		education_id INTEGER,
		city_id INTEGER,
		about TEXT,
		FOREIGN KEY (profile_id) REFERENCES profile(id),
		FOREIGN KEY (education_id) REFERENCES education(id),
		FOREIGN KEY (city_id) REFERENCES city(id)
	);''')

cur.execute('''SELECT profile.id, profile.link FROM profile''')
try:
	scrappedProfiles = 0
	dbData = cur.fetchall()
	for data in dbData:
		profileId = data[0]
		profileDataId = getProfileDataId(profileId)
		if profileDataId != -1:
			#print('Profile %s already scrapped, skip it' % (profileId))
			continue

		profileLink = data[1]
		profile = {
			'id' : profileId,
			'link': profileLink
		}
		reason = ParseProfile(driver, profile)
		if reason == REASON.PAGE_DOESNT_EXIST:
			print('-', end='', flush=True)
			removeProfileById(cur, profileId)
			continue
		elif reason == REASON.CAPCHA:
			print('?', end='', flush=True)
			wait = WebDriverWait(driver, 300)
			continue
		else:			
			wait = WebDriverWait(driver, 3)

		isScrapped = fillTable(profile, profileDataId, cur)
		if isScrapped:
			scrappedProfiles += 1
			print('+', end='', flush=True)
		profileRow = cur.fetchone()
finally:
	print('Scrapped %s profiles' % (scrappedProfiles,))
	con.commit()
	con.close()
	driver.stop_client()
	driver.close()
	
