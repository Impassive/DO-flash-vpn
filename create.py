import requests
import time
import paramiko
from getpass import getpass

from config import config

# Create droplet
base_url = "https://api.digitalocean.com/v2"
droplet_url = "/droplets"
account_url = "/account"

headers = {
	"Content-Type": "application/json",
	"Authorization": "Bearer " + config['DO-token']
}

data = {
	"name": config['droplet-name'],
	"region": config['droplet-region'],
	"size": config['droplet-size'],
	"image": config['droplet-image'],
	"ssh_keys": config['droplet-ssh-keys']
}

# Create droplet
print('Creating droplet...')
r = requests.post(base_url + str(droplet_url), json=data, headers=headers)

droplet_id = r.json()['droplet']['id']


# Wait while creating
while True:
	print('.', end=" ")
	# get droplet - check if locked - wait 5 sec if is locked
	r = requests.get(base_url + droplet_url + "/" + str(droplet_id), headers=headers)

	if not r.json()['droplet']['locked']:
		break
	time.sleep(5)

print('')
print('Droplet created!')

# Get IP address of droplet
host = r.json()['droplet']['networks']['v4'][0]['ip_address']

print("Droplet's IP address: " + host)
user = 'root'

# Start client and auto add new server to known hosts list
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print('Unlocking private certificate...')
passw = getpass("Enter private key password: ")

print('SSH connecting...')
# Get private key and connect
pkey = paramiko.RSAKey.from_private_key_file(config['private-key-file'], password=passw)
client.connect(hostname=host, username=user, pkey=pkey)
print('SSH connected!')

# --------------------------------
def wait(intuple):
	l_stdin, l_stdout, l_stderr = intuple[0], intuple[1], intuple[2]
	for line in str(l_stdout.read(), 'utf-8').splitlines():
		print(line)
	print()
	for line in str(l_stderr.read(), 'utf-8').splitlines():
		print(line)

	input("Press <ENTER> to continue...")
	return l_stdin, l_stdout, l_stderr

# ------------------------------------------------------------
# Droplet configuration
#
# ---------------------
# update && upgrade && autoremove
print('Updating system...')
wait(client.exec_command("apt update && apt-get -y upgrade && apt-get autoremove"))
# ---------------------
#
# ---------------------
# Create user

print("Creating user...")
stdin, stdout, stderr = client.exec_command("adduser " + config['droplet-username'] + " --quiet", get_pty=True)
# Type pass
passw = getpass('Type user password: ')
stdin.write(passw + '\n')
stdin.flush()

# Retype pass
passw = getpass('Retype user password: ')
stdin.write(passw + '\n')
stdin.flush()

# Other information leave default
for i in range(6):
	stdin.write('\n')
	stdin.flush()
print('User ' + config['droplet-username'] + ' created')
# ---------------------

# ---------------------
# Add user to sudo
stdin, stdout, stderr = client.exec_command("adduser " + config['droplet-username'] + " sudo")
print(stdout.read())
# ---------------------

# ---------------------
# Export key
print('Creating .ssh directory and echoing public key to authorized_keys...')
stdin, stdout, stderr = client.exec_command("mkdir -p /home/" + config['droplet-username'] + "/.ssh")
stdin, stdout, stderr = client.exec_command("echo '" + config['ssh-public-key'] + "' > /home/" +
                                            config['droplet-username'] + "/.ssh/authorized_keys")
print('Done.')
# ---------------------

# ---------------------
# install requirements
stdin, stdout, stderr = wait(client.exec_command("apt install apt-transport-https ca-certificates curl software-properties-common"))
# ---------------------

# ---------------------
# add official docker gpg key
print("Adding Docker's GPG key...")
stdin, stdout, stderr = client.exec_command("curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -")
# ---------------------

# ---------------------
# Add docker's repo
print("Adding docker's repo...")
stdin, stdout, stderr = wait(client.exec_command('sudo add-apt-repository "deb [arch=amd64] '
                                                 'https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"'))
# ---------------------

# ---------------------
# Install docker
print("Installing docker...")
stdin, stdout, stderr = wait(client.exec_command("apt-get update && apt-get -y install docker-ce"))
# ---------------------

# ---------------------
# Run squid container
print("Starting Squid container...")
sq_username = input("Enter username for squid: ")
sq_password = getpass("Enter password for squid: ")
print('Downloading and creating Squid container...')
stdin, stdout, stderr = wait(client.exec_command("docker run --name squid -d -e SQUID_USERNAME={0} -e SQUID_PASSWORD={1}"
                                                 " -p 3128:3128 robhaswell/squid-authenticated"
                                                 .format(sq_username, sq_password)))

# ---------------------
"""
"""
# ---------------------
# Run ovpn container
print("Generating OVPN infrastructure...")

OVPN_DATA = "ovpn-data-" + config['droplet-username']

print("Creating volume...")
stdin, stdout, stderr = wait(client.exec_command("docker volume create --name " + OVPN_DATA))

print("Generating config...")
stdin, stdout, stderr = wait(client.exec_command("docker run -v {0}:/etc/openvpn --rm "
                                                 "kylemanna/openvpn ovpn_genconfig -u udp://{1}"
                                                 .format(OVPN_DATA, host)))

print("Initializing PKI infrastructure...")
stdin, stdout, stderr = client.exec_command("docker run -v {0}:/etc/openvpn --rm -it kylemanna/openvpn ovpn_initpki"
                                            .format(OVPN_DATA),
                                            get_pty=True)
passw = getpass('Enter PEM passphrase: ')
stdin.write(passw + '\n')
stdin.flush()
passw = getpass('Verifying - Enter PEM passphrase: ')
stdin.write(passw + '\n')
stdin.flush()
stdin.write('\n')
stdin.flush()

# Wait until key generated
# TODO: shitcode but works, refactor it
print('Generating 2048 prime number. This is going to take a long time...')
while True:
	ch = str(stdout.read(1))
	if ch == "b'*'":
		break
print('Key generated')
time.sleep(5)

# Ask for some
passw = getpass('Enter pass phrase for ca.key: ')
stdin.write(passw + '\n')
stdin.flush()

stdin.write(passw + '\n')
stdin.flush()
stdout.read()

# Start main daemon
print('Starting OVPN server daemon...')
stdin, stdout, stderr = wait(client.exec_command("docker run --name ovpn-server -v "
                                                 "{0}:/etc/openvpn -d -p 1194:1194/udp "
                                                 "--cap-add=NET_ADMIN kylemanna/openvpn"
                                                 .format(OVPN_DATA)))
print('Done')


# Generate client certificate
cert_name = input("Enter name for client's certificate: ")
print("Generating client's certificate...")

stdin, stdout, stderr = client.exec_command("docker run -v "
                                                 "{0}:/etc/openvpn --rm -it "
                                                 "kylemanna/openvpn easyrsa build-client-full "
                                                 "{1} nopass"
                                                 .format(OVPN_DATA, cert_name),
                                            get_pty=True)
time.sleep(4)
stdin.write(passw + '\n')
stdin.flush()
print('Done')


# Export client's certificate
stdin, stdout, stderr = wait(client.exec_command("docker run -v "
                                                 "{0}:/etc/openvpn --rm "
                                                 "kylemanna/openvpn ovpn_getclient "
                                                 "{1} > /home/{2}/{1}.ovpn"
                                                 .format(OVPN_DATA,
                                                         cert_name,
                                                         config['droplet-username'],
                                                         )))
print("Client's certificate was exported to /home/{0}/{1}.ovpn".format(config['droplet-username'], cert_name))


# Download cert through sftp
print("Downloading client's certificate...")

sftp = client.open_sftp()
localpath = config['ovpn-directory'] + "\\" + cert_name + ".ovpn"
remotepath = "/home/{0}/{1}.ovpn".format(config['droplet-username'], cert_name)
sftp.get(remotepath, localpath)
sftp.close()
print('Done')
client.close()
# ---------------------

print()
print('Server deployed. \n'
      'OVPN container deployed and running. \n'
      'Squid container deployed and running. \n'
      'Certificate downloaded to ' + localpath)
