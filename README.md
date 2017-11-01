# DO-flash-vpn
Simple script that order new droplet on DigitalOcean and deploy OVPN infrastructure in it.  
Usage:
1. create config.py from example
2. "python3 create.py" - for new droplet
3. "python3 delete_all.py" - for deleting all existing

Prerequisites:
* python 3 with modules installed
* working account on DigitalOcean
* imported public key in DigitalOcean account

Algo's steps:
1. Order new droplet (virtual machine)
2. Open SSH connection by using certificate
3. Update  && upgrade system
4. Create new user (default is root usually), add him to sudoers and add public key
5. Install requirements & docker-ce 
6. Start robhaswell/squid-authenticated container (Squid with user/passw auth)
7. Create OVPN infrastructure, start server daemon.
8. Generates client's certificate and download it through sftp to user
