import requests
import os
import datetime
import csv
import re
from bs4 import BeautifulSoup

ZENDESK_API_TOKEN = os.getenv("API_TOKEN")
ZENDESK_USER_EMAIL = os.getenv("USER_EMAIL")
ZENDESK_PREFIX = 'https://'
ZENDESK_DOMAIN = '.zendesk.com'
ZENDESK_SUBDOMAIN = 'subdomain'
ZENDESK_FULL_URL = ZENDESK_PREFIX + ZENDESK_SUBDOMAIN + ZENDESK_DOMAIN
language = 'en-gb'
currentdate = datetime.datetime.now()


date = datetime.date.today()
backup_path = os.path.join(str(date),ZENDESK_SUBDOMAIN, language)
if not os.path.exists(backup_path):
    os.makedirs(backup_path)

log = []
credentials = f'{ZENDESK_USER_EMAIL}/token', ZENDESK_API_TOKEN
currentdir = os.getcwd()
article_endpoint = f'{ZENDESK_FULL_URL}/api/v2/help_center/articles.json'

while article_endpoint:
    response = requests.get(article_endpoint, auth=credentials)
    if response.status_code != 200:
        print(f'Failed to retrieve articles with error {response.status_code}')
        exit()
    data = response.json()
    print (response.status_code)

    for article in data['articles']:
        
        ##Is there any content?
        if article['body'] is None:
            continue

        if article['draft'] == True:
            continue

        articlebody = BeautifulSoup(article["body"])

        ##Get the attachments
        attachments_endpoint = f'{ZENDESK_FULL_URL}/api/v2/help_center/articles/{article["id"]}/attachments'

        for img in articlebody.findAll('img'):
            img['src'] = img['src'][img['src'].find(f'/hc/article_attachments'):]

        while attachments_endpoint:
            attachments_response = requests.get(attachments_endpoint, auth=credentials)
            if attachments_response.status_code != 200:
                print(f'Failed to retrieve articles with error {attachments_response.status_code}')
                exit()
            attachments_data = attachments_response.json()

            ##loop through to get the data
            for attachment in attachments_data["article_attachments"]:
                if attachment['url'] is None:
                    continue

                ##parse the content_url + file_name                            
                attachment_url = f'{attachment["content_url"]}/{attachment["file_name"]}'
                attachment_data = requests.get(attachment_url, auth=credentials)
                attachment_filename = f'{attachment["file_name"]}'

                hcarticle = os.path.join("hc","article_attachments")
                hc_artcile_id = os.path.join(hcarticle, f'{attachment["id"]}')
                base_article_path = os.path.join(backup_path, hc_artcile_id)
                if not os.path.exists(base_article_path):
                    os.makedirs(base_article_path)

                with open(os.path.join(base_article_path, attachment_filename), mode='wb') as a:
                    a.write(attachment_data.content)
                
                for img in articlebody.findAll('img', src=re.compile(f'hc/article_attachments/{attachment["id"]}')):
                    img['src'] = f'hc/article_attachments/{attachment["id"]}/{attachment["file_name"]}'
                    img['style'] = 'max-width:1000px'
                    print(img['src'])

            attachments_endpoint = attachments_data.get('next_page', None)

        article_html = str(articlebody)

        originalurl = '<p>Original Article - <a href=' + article['html_url'] + '">' + article['html_url'] + '</a></p>'
        title = '<h1>' + article['title'] + '</h1>'
        filenamehtml = f'{article["id"]}.html'
        with open(os.path.join(backup_path, filenamehtml), mode='w', encoding='utf-8') as f:
            f.write(originalurl + '\n' + title + '\n' + article_html + '\n')
            
        print(f'{article["id"]} copied!')
        log.append((filenamehtml, article['title'], article['author_id']))

    article_endpoint = data.get('next_page', None)

with open(os.path.join(backup_path, '_log.csv'), mode='wt', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(('File', 'Title', 'Author ID'))
    for article in log:
        writer.writerow(article)