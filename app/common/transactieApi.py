import requests as r
import time as t
import subprocess
import json
from .asyncScheduler import asyncScheduler
import math
import os
import asyncio
import threading

DIR = os.path.dirname(__file__)

class transactieApi(object):
	def __init__(self, url, streepsysteem):
		self.url = url
		self.streepsysteem = streepsysteem
		self.session = r.Session()
		self.session.auth = ....
		self.timeDiff = self.calculateTimeDifference()
		self.processedIds = []
		self.processingTimes = []

	def findTransaction(self, transactions, productId, userId):

		for transaction in reversed(transactions):
			if(transaction['user_id'] == userId and transaction['product_id'] == productId):
				return transaction
		return False

	def calculateTimeDifference(self):
		self.streepsysteem.resetTradingProxy()

		self.streepsysteem.streep(	self.streepsysteem.proxyId,
									self.streepsysteem.cashUser)

		time = t.time()

		transaction = self.findTransaction(	self.getData(time+60 + 3600, 120 + 7200),
											self.streepsysteem.proxyId,
											self.streepsysteem.cashUser)

		if(not transaction):
			raise Exception('Could not calculate proper time difference...')

		return math.ceil(time - transaction['purchase_time'])

	def cleanUpResponse(self, transactions):
		for i, transaction in enumerate(transactions):
			transactions[i]['product_id'] = int(transaction['product_id'])
		return transactions

	def getData(self, endTime, interval):
		if(hasattr(self, 'timeDiff')):
			endTime = endTime - self.timeDiff


		URL = (
			self.url + '/media/output/export_purchases.php?start_time={start_time}&end_time={end_time}'
		).format(start_time=endTime-interval, end_time=endTime)

		print(URL)

		response = self.session.get(URL)

		print('we are making a request')
		convertedResponse = self.cleanUpResponse(response.json())
			
		return convertedResponse

	def cleanUpOldTransactions(self, history):
		self.processedIds[:] = [self.processedIds[i] for i, time in enumerate(self.processingTimes) if time > history]
		self.processingTimes[:] = [time for time in self.processingTimes if time > history]

	def __filterOutProcessedTransactions(self, transactions, history):
		result = []

		self.cleanUpOldTransactions(history)

		for transaction in transactions:
			if not (transaction['purchase_id'] in self.processedIds):
				result.append(transaction)
				self.processedIds.append(transaction['purchase_id'])
				self.processingTimes.append(transaction['purchase_time'])

		return result

	def __createScheduledProcessor(self, interval, safetyMargin, callback):
		def scheduledProcessor():
			evalTime = t.time()
			transactions = self.getData(evalTime, interval+safetyMargin)
			callback(self.__filterOutProcessedTransactions(transactions, evalTime-interval-safetyMargin*2))
		return scheduledProcessor

	def streamData(self, interval, safetyMargin, callback):
		def schedulingThread():
			loop = asyncio.new_event_loop()
			scheduled = asyncScheduler(interval, self.__createScheduledProcessor(interval, safetyMargin, callback), loop)
			loop.run_forever()
		thread = threading.Thread(target=schedulingThread)
		thread.start()
		return thread
