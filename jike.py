#coding:utf-8

import urllib2
from bs4 import BeautifulSoup
import re
import zlib
from pymongo import MongoClient
import time
import random
import threading
import Queue
import os

topicqueue = Queue.Queue() #����һ�������ƴ�С�ĵĶ���
THREAD_NUM = 10 #�����̵߳ĸ���

class JikeSpider(threading.Thread):
	"""����������"""
	def __init__(self):
		threading.Thread.__init__(self)
		self.header = {
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36'
			}

	def start(self):
		global topicqueue
		while not topicqueue.empty():
			topicurl = topicqueue.get()
			topicPage = self.open_url(topicurl)
			self.get_topic(topicPage, topicurl) 
			time.sleep(random.uniform(1,3))
			topicqueue.task_done()

	def open_url(self, url):
		request = urllib2.Request(url, headers = self.header)
		try:
			response = urllib2.urlopen(request, timeout = 20)
			# print response.read()
			return response
		except urllib2.URLError, e :
				if hasattr(e, "code"):
					print "The server couldn't fulfill the request."
					print "Error code: %s" % e.code
				elif hasattr(e, "reason"):
					print "We failed to reach a server. Please check your url and read the Reason"
					print "Reason: %s" % e.reason

	def soup(self, topicPage):
		soup = BeautifulSoup(topicPage, 'lxml')
		return soup

	def get_topic(self, topicPage, url):
		soup = self.soup(topicPage)
		
		topic_content = soup.find('div', class_='topic-content')
		topic_url = url
		topic_title = topic_content.find('p', class_='title').text
		topic_subscribers = topic_content.find('p', class_='subscribers').text
		
		topic_url = self.handle_url(topic_url)
		topic_title = self.handle_title(topic_title)
		topic_subscribers = self.handle_subscribers(topic_subscribers)
		print topic_title + '    ' + str(topic_subscribers) + '    '+ topic_url

		topic = {}
		topic['url'] = topic_url
		topic['title'] = topic_title
		topic['subscribers'] = topic_subscribers

		topicqueue.put(topic_url) # ��topic��url����Queue
		
		collection = self.Connect_MongoDB() # �������ݿ�
		if not self.Query_MongoDB(collection, topic['url']): # ��ѯ�ü�¼�Ƿ��Ѵ������ݿ�
			self.Insert_MongoDB(collection, topic) # ���뻰���¼

		self.get_related_topics(soup, collection) # ��Ѱ�������,���������ݿ�

	def get_related_topics(self, soup, collection):
		topics = soup.find('div', id='related-topics').find_all('a', class_='related-topic-cell')
		for topic in topics:
			topic_url = topic.get('href')
			topic_title = topic.find('p', class_='title').text
			topic_subscribers = topic.find('p', class_='subscribers').text

			topic_url = self.handle_url(topic_url)
			topic_title = self.handle_title(topic_title)
			topic_subscribers = self.handle_subscribers(topic_subscribers)
			print topic_title + '    ' + str(topic_subscribers) + '    '+ topic_url

			topicqueue.put(topic_url) # ��topic��url����Queue
			
			topic = {}
			topic['url'] = topic_url
			topic['title'] = topic_title
			topic['subscribers'] = topic_subscribers

			if not self.Query_MongoDB(collection, topic['url']): # ��ѯ�ü�¼�Ƿ��Ѵ������ݿ�
				self.Insert_MongoDB(collection, topic) # ���뻰���¼

	def handle_url(self, url): # �滻//mΪhttp://share
		temp = re.sub(r'//m', r'http://share', url)
		return temp

	def handle_title(self, title):
		temp = ''.join(title.split()); # ȥ���ո񡢻��з�
		return temp

	def handle_subscribers(self, subscribers):
		temp = ''.join(subscribers.split()); # ȥ���ո񡢻��з�
		number = re.findall(r'\d+', temp)[0]
		return number

	def Connect_MongoDB(self):
		# ��������
		client = MongoClient('localhost', 27017)
		# ָ����Ҫ���в�����database��collection
		db = client.jikedb
		collection = db.topic_collection
		# �����������
		# collection.remove({})
		return collection

	def Insert_MongoDB(self, collection, topic):
		# ����
		result = collection.insert_one(topic)

	def Query_MongoDB(self, collection, topic_url):
		result = collection.find({'url':topic_url}).count()
		if result == 0:
			return False
		else:
			return True


def main():
	threads = []
	# ���ļ��ж�ȡTop20������url���������
	with open('jiketop20.txt', 'r') as f:
		while True:
			line = f.readline()
			if line:
				topicqueue.put(line)
			else:
				break
	
	for i in range(THREAD_NUM):
		spider = JikeSpider()
		spider.start()
		threads.append(spider)

	for thread in threads:
		thread.join()
	topicqueue.join()

if __name__ == '__main__':
	main()
