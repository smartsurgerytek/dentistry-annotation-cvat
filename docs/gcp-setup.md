## Prerequisite

#### Software
- gcloud
#### Files
- A SSH Key Pair
#### GCP Permissions
- `compute.instances.create`
####  **(Optional)** Environment Variables for CLI
 You can set these variables for later CLI commands usage. Recommand you copy & paste to somewhere and modify it.
```bash
export EMAIL=your_account@smartsurgerytek.com
export GCP_REGION=asia-east1
export GCP_ZONE="${GCP_REGION}-a"
export YOUR_NAME=name
export INSTANCE_NAME="${YOUR_NAME}-cvat-${GCP_ZONE}"
export PUBLIC_KEY_PATH=/path/to/your/public/key.pub
export GCP_SUBDOMAIN=your_subdomain
export CVAT_HOST="${GCP_SUBDOMAIN}.smartsurgerytek.net"
```
- `YOUR_NAME`: An arbitrary name for setting instance name, for example: `eason`.
- `PUBLIC_KEY_PATH`: Path to your public key. For example: `$HOME/.ssh/id_rsa.pub`. I used rsa. The key content is better to have a name prefix like `eason:ssh-rsa ABCDEFGHIJKLMNOPQRSTUVWXYZ123456790... eason.li@smartsurgerytek.com`.
- `GCP_SUBDOMAIN`: A subdomain, for example: `dev0`. This will concanate with the some URLs and DNS record settings.
#### gcloud CLI default project
You can use these command to check some configurations.
```bash
gcloud config get-value project
```
Output Example:
```bash
sandbox-446907
```
and if it's not the project you want. Use
```bash
gcloud config set project project_you_want
```
## GCP
```bash
gcloud compute instances create $INSTANCE_NAME \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --machine-type=e2-custom-4-32768 \
  --boot-disk-size=200GB \
  --boot-disk-type=pd-balanced \
  --zone=${GCP_ZONE} \
  --tags=cvat-server-8080 \
  --metadata-from-file ssh-keys=$PUBLIC_KEY_PATH
```

### List Google Compute Instances
```bash
gcloud compute instances list
```
Copy the External IP for later usage or export the variable. replace `xxx.xxx.xxx.xxx` below:
```bash
export EXTERNAL_IP=xxx.xxx.xxx.xxx
```
### Reserve an Static IP Address
```bash
gcloud compute addresses create $INSTANCE_NAME-ip --addresses $EXTERNAL_IP --region asia-east1
```
### Setup GCP Domain
```bash
gcloud dns record-sets transaction start --zone=smartsurgerytek-net
gcloud dns record-sets transaction add $EXTERNAL_IP \
  --name="${GCP_SUBDOMAIN}.smartsurgerytek.net." \
  --ttl=300 \
  --type=A \
  --zone=smartsurgerytek-net
gcloud dns record-sets transaction execute --zone=smartsurgerytek-net
```
### SSH into the Created VM
```bash
gcloud compute ssh --zone $GCP_ZONE $INSTANCE_NAME  -- "export CVAT_HOST=${CVAT_HOST} && exec bash -l"
```
---
**NOTICE**: Commands in the following sections should be executed inside the Google Compute Engine (GCE) instance you created above, excepting `gcloud` commands.
## Docker
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```
Verify Docker installation:
```bash
docker --version
```
My output is  `Docker version 27.5.1, build 9f9e405`

## CVAT
### Clone this repo
```bash
git clone -b sst-v24.06.01 https://github.com/smartsurgerytek/dentistry-annotation-cvat.git
cd dentistry-annotation-cvat
```

### Build & Run CVAT
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml build
docker compose -f docker-compose.yml -f components/serverless/docker-compose.serverless.yml up -d
```
you need to attach your terminal into the `cvat_server` container to do some basic setup.
```bash
docker exec -it cvat_server python manage.py migrate
docker exec -it cvat_server python manage.py collectstatic
docker exec -it cvat_server python manage.py syncperiodicjobs
docker exec -it cvat_server python manage.py createsuperuser --username admin
```
Follow the prompt to setup email(option) and password.

You can check your URL:
```bash
echo "http://${CVAT_HOST}:8080"
```
Check if you can use your browser to open http://$CVAT_HOST:8080

## Nuclio
### Install `nuctl`
```bash
curl -s https://api.github.com/repos/nuclio/nuclio/releases/latest \
			| grep -i "browser_download_url.*nuctl.*$(uname)" \
			| cut -d : -f 2,3 \
			| tr -d \" \
			| wget -O nuctl -qi - && chmod +x nuctl
sudo mv nuctl /usr/local/bin/
```
### Create a Project
```bash
nuctl create project cvat
```

### Clone `smartsurgerytek/dentistry-annotation-nuclio/` Repository
```bash
cd ~
git clone https://github.com/smartsurgerytek/dentistry-annotation-nuclio.git
cd dentistry-annotation-nuclio
```
### Deploy the Measurement & Segmentation Function
```bash
nuctl deploy measurement --path ./src/measurement/ --project-name cvat --platform local
nuctl deploy segmentation --path ./src/segmentation/ --project-name cvat --platform local
```
If this is your first time to deploy, you have to what for a while due to graphic pytorch library is huge.

After the deployment is done, back to your browser and go to the `Models` tab check your deployment.

## Clean Up
### Remove the Google Compute Instance
```bash
gcloud compute instances stop $INSTANCE_NAME
gcloud compute instances delete $INSTANCE_NAME
```

### Remove the static IP
```bash
gcloud compute addresses delete --region $GCP_REGION $INSTANCE_NAME-ip
```

### Remove the Domain Record
```bash
 gcloud dns record-sets delete "${CVAT_HOST}." --zone=smartsurgerytek-net --type=A
```