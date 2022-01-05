#!/usr/bin/env python
# coding: utf-8
# vim:fileencoding=utf-8

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

def SignIn(driver):
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

def InputElement(driver, name, text):
	wait = WebDriverWait(driver, 10)
	while(True):
		try:
			elem = wait.until(EC.presence_of_element_located((By.NAME, name)))
			elem.clear()
			elem.send_keys(text)
		finally:
			break

def AcceptElementInput(driver, name):
	elem = driver.find_element_by_name(name)
	elem.send_keys(Keys.RETURN)

def ClickElement(driver, xpath):
	while(True):
		try:
			elem = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
			elem = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
			ActionChains(driver).move_to_element(elem).click().perform()
		finally:
			break

def TryClickElement(driver, xpath):
	try:
		elem = driver.find_element_by_xpath(xpath)
		if(elem is not None):
			ClickElement(driver, xpath)
	except:
		pass

def ScrollPageToBottom(driver):
	driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

def ParseContent(content, cur):
	soup = bs.BeautifulSoup(content, 'html.parser')
	elements = soup.find_all('figure', class_="user-card js-folders-user-card js-tutorial-user-card")

	parsedUsersCount = 0
	for elem in elements:
		userId = elem.get('data-user-id')
		link = 'https://badoo.com/profile/0'+userId
		cur.execute("SELECT Id FROM Profile WHERE Id=:Id;",{
			"Id": userId
		})
		if(len(cur.fetchall())):
			cur.execute("UPDATE Profile SET Link=? WHERE Id=?", (link, userId))
		else:
			cur.execute("INSERT INTO Profile(Id, Link) VALUES (:Id, :Link)",{
				"Id": userId,
			 	"Link": link
			})
			parsedUsersCount += 1
	return parsedUsersCount

def GoToPrevPage(driver):
	ScrollPageToBottom(driver)
	ClickElement(driver, '/html/body/div[3]/div[1]/main/div[1]/section/div[3]/section/div[2]/div/div[1]/a')

def GoToNextPage(driver):
	ScrollPageToBottom(driver)
	ClickElement(driver, '/html/body/div[2]/div[2]/main/div[1]/section/div[3]/section/div[2]/div/a[9]')

def GetCurrentpageNumber(driver):
	currentPageNumber = re.sub(r'\D', '', driver.current_url)
	if(currentPageNumber == ''):
		currentPageNumber = 1
	return int(currentPageNumber)

def ScanPage(driver, cur, pageNum):
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

	wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'user-card')))
	print('Scanning page {0}: {1}'.format(pageNum, driver.current_url))
	htmlContent = driver.page_source
	return ParseContent(htmlContent, cur)

profile = webdriver.FirefoxProfile()
# 1 - Allow all images
# 2 - Block all images
# 3 - Block 3rd party images 
profile.set_preference("permissions.default.image", 2)
driver = webdriver.Firefox(firefox_profile=profile)
wait = WebDriverWait(driver, 10)

SignIn(driver)

while('search' not in driver.current_url):
	xpath = '/html/body/div[2]/div[2]/aside/div/div/div/div[1]/div/div[3]/div/a[2]'
	ClickElement(driver, xpath)

print('Current page: {0}'.format(driver.current_url))

filePath = 'id_data.db'
con = sqlite3.connect(filePath)
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS Profile(Id INTEGER PRIMARY KEY, Link TEXT);")

cur.execute("SELECT Id FROM Profile")
print('%s users stored in database' % (len(cur.fetchall())))

parseCounter = 0
con.row_factory = sqlite3.Row
cur = con.cursor()

try:
	for pageNum in range(1, 5000):
		parseCounter += ScanPage(driver, cur, pageNum)
		print('Collected {0} ids'.format(parseCounter))	
finally:
	con.commit()
	con.close()
	print('%s users added' % (parseCounter))

driver.close()
