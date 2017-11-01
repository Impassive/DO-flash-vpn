import requests

from config import config

base_url = "https://api.digitalocean.com/v2"
droplet_url = "/droplets"
account_url = "/account"

headers = {
	"Content-Type": "application/json",
	"Authorization": "Bearer " + config['DO-token']
}

r = requests.get(url=base_url + droplet_url, headers=headers)
remList = []
for droplet in r.json()['droplets']:
	url = base_url + droplet_url + "/" + str(droplet['id'])
	r = requests.delete(url=url, headers=headers)
	print(r)