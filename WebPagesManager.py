import time
import os.path
import sqlite3
import sys

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
	'signup': 'https://badoo.com/signup/'
}

class WebPagesManager:
	
	def __init__(self, name):
		profile = webdriver.FirefoxProfile()
		profile.set_preference("permissions.default.image", 2)
		driver = webdriver.Firefox(firefox_profile=profile)
		wait = WebDriverWait(driver, 10)

def SignIn(self, driver):
	driver.get(urlDict['login'])
	print('Current page: {0}'.format(driver.current_url))

	cookiesFile = 'cookies.pkl'
	if(os.path.exists(cookiesFile)):
		cookies = pickle.load(open(cookiesFile, "rb"))
		print('Loading cookies: {0}', len(cookies))
		for cookie in cookies:
		    driver.add_cookie(cookie)
		print('Signing in')
		driver.get(urlDict['encounters'])
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
				pass

	cookies = driver.get_cookies()
	print('Dumping cookies: {0}', len(cookies))
	pickle.dump(cookies, open(cookiesFile,"wb"))

	while('search' not in driver.current_url):
		xpath = '/html/body/div[2]/div[2]/aside/div/div/div/div[1]/div/div[1]/div[4]/div/a[2]'
		ClickElement(driver, xpath)
	print('Current page: {0}'.format(driver.current_url))

	def InputElement(self, driver, name, text):
		wait = WebDriverWait(driver, 10)
		while(True):
			try:
				elem = wait.until(EC.presence_of_element_located((By.NAME, name)))
				elem.clear()
				elem.send_keys(text)
			finally:
				break

	def AcceptElementInput(self, driver, name):
		elem = driver.find_element_by_name(name)
		elem.send_keys(Keys.RETURN)

	def ClickElement(self, driver, xpath):
		while(True):
			try:
				elem = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
				elem = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
				ActionChains(driver).move_to_element(elem).click().perform()
			finally:
				break

	def TryClickElement(self, driver, xpath):
		try:
			elem = driver.find_element_by_xpath(xpath)
			if(elem is not None):
				ClickElement(driver, xpath)
		except:
			pass

	def ScrollPageToBottom(self, driver):
		driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

	def ParseContent(self, content, parsedData):
		soup = bs.BeautifulSoup(content, 'html.parser')
		elements = soup.find_all('figure', class_="user-card js-folders-user-card")

		parsedUsersCount = 0
		for elem in elements:
			userId = elem.get('data-user-id')
			if(userId in parsedData):
				continue
			parsedUsersCount += 1
			parsedData[userId] = {}
			parsedData[userId]['Link'] = 'https://badoo.com/profile/0'+userId
		print('Collected {0} ids'.format(parsedUsersCount))	

	def GoToPrevPage(self, driver):
		ScrollPageToBottom(driver)
		ClickElement(driver, '/html/body/div[2]/div[2]/main/section/div[2]/div[1]/a')

	def GoToNextPage(self, driver):
		ScrollPageToBottom(driver)
		ClickElement(driver, '/html/body/div[2]/div[2]/main/section/div[2]/div[10]/a')

	def GetCurrentpageNumber(self, driver):
		currentPageNumber = re.sub(r'\D', '', driver.current_url)
		if(currentPageNumber == ''):
			currentPageNumber = 1
		return int(currentPageNumber)

	def ScanPage(self, driver, parsedData, pageNum):
		pageUrlPart = 'search'
		if(pageNum > 1):
			pageUrlPart += '?page='+str(pageNum)


		while(pageUrlPart not in driver.current_url):
			currentPageNumber = GetCurrentpageNumber(driver)
			# Sometime driver misclick (maybe) and get into someone's profile,
			# so I take it one step back in history.
			if('profile' in driver.current_url):
				print('Misclick!')
				driver.back()
			# Sometimes ad panel showing up - so I need to deal with it. 
			TryClickElement(driver, '/html/body/aside/section/div[1]/div/div[1]/div[2]/i')
			TryClickElement(driver, '/html/body/aside/section/div[1]/div/div[3]/i')

			if(pageNum > currentPageNumber):
				GoToNextPage(driver)
			elif(pageNum < currentPageNumber):
				GoToPrevPage(driver)

		wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'users-card')))
		print('Scanning page {0}: {1}'.format(pageNum, driver.current_url))
		htmlContent = driver.page_source
		ParseContent(htmlContent, parsedData)

filePath = 'id_data.db'
con = sqlite3.connect(filePath)
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS Profile(Id INTEGER PRIMARY KEY, Link TEXT);")

parsedData = {}
con.row_factory = sqlite3.Row
cur = con.cursor()
cur = cur.execute("SELECT Id, Link FROM Profile;")
rows = cur.fetchall()
print('{0} rows fetched'.format(len(rows)))
for row in rows:
	parsedData[row['Id']] = {}
	parsedData[row['Id']]['Link'] = row["Link"]
	print("{0} {1}".format(row["Id"], row["Link"]))

try:
	for pageNum in range(1, 500):
		ScanPage(driver, parsedData, pageNum)
finally:
	print('Saving {0} users'.format(len(parsedData)))
	cur = con.cursor()
	for key in parsedData:
		Id = key
		Link = parsedData[key]['Link']
		print("{0} {1}".format(Id, Link))
		cur.execute("SELECT Id FROM Profile WHERE Id=:Id;",{
			"Id": Id
		})
		if(cur.rowcount == 0):
			cur.execute("INSERT INTO Profile(Id, Link) VALUES (:Id, :Link)",{
				"Id": Id,
			 	"Link": Link
			 })
		else:
			cur.execute("UPDATE Profile SET Link=? WHERE Id=?", (Link, Id))
	con.commit()
	con.close()

