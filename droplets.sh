apt update && apt upgrade -y && apt autoremove -y

apt install -y ssh

adduser kell
adduser kell sudo

# Export my key
mkdir -p /home/kell/.ssh
echo 'ssh-rsa AAAAB3NzaC1yc2EAAAABJQAAAQEAsI98Ue2j+H2YcH4+GdOPHaooGcrOB26glK8T3d87DVdRVPkUpO99rzZfk4NlkFGn6eKIPOC65CkwKPMR7vCBvDGv8rfvWPMY3s8tWk7Sklr5TISP/jOztB6F3HxYVaEr9jTc7zyfJMAb0J8xCBVc52+CpF0Wy2S3rX6JlvpX1S6tjKxgYDgXfxV5DM7TSXFBKnm7orVa82h5PSbEgQ2eG3gc8P86hHTgJVdT/z21EH82E8i+6A8x4oxN6TDk2YlU69CpZe564+Fd1rbZnq2Y+o2uA0wS/7Mi70nr/JqlOODD8JgO9bWdhL4/4ki1GMeGak54JSRoFonw5gmQ+qa7gw== kell_s notebook' > /home/kell/.ssh/authorized_keys

# install requirements
apt install \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common
	
# add official docker gpg key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

# Add docker's repo
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
   
# Install docker
apt update && apt install -y docker-ce

# Run squid container
echo "Squid installation..."
read -p "Please enter username for squid: " sq_username
read -p "Enter password for squid: " sq_password

# Start Squid container
docker run --name squid -d -e SQUID_USERNAME=$sq_username -e SQUID_PASSWORD=$sq_password -p 3128:3128 robhaswell/squid-authenticated

# OVPN data 
OVPN_DATA="ovpn-data-kell"

# Create docker volume for ovpn
docker volume create --name $OVPN_DATA

read -p "Enter ip addres of main network interface: " ovpn_ip

# Generate config
docker run -v $OVPN_DATA:/etc/openvpn --rm kylemanna/openvpn ovpn_genconfig -u udp://$ovpn_ip

# Initialize PKI infrastructure
docker run -v $OVPN_DATA:/etc/openvpn --rm -it kylemanna/openvpn ovpn_initpki

# Start main ovpn process
docker run --name ovpn-server -v $OVPN_DATA:/etc/openvpn -d -p 1194:1194/udp --cap-add=NET_ADMIN kylemanna/openvpn

# Generate certificate for kell's notebook
read -p "Enter name for client's certificate: " clientname
docker run -v $OVPN_DATA:/etc/openvpn --rm -it kylemanna/openvpn easyrsa build-client-full $clientname nopass

# Export 
docker run -v $OVPN_DATA:/etc/openvpn --rm kylemanna/openvpn ovpn_getclient $clientname > /home/kell/$clientname.ovpn
