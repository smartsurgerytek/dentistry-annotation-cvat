## Prerequisite

#### Software
- gcloud
#### Files
- A SSH Key Pair
#### GCP Permissions
- `compute.instances.create`
####  **(Optional)** Environment Variables for CLI
 You can set these variables for later CLI commands usage.
```bash
export EMAIL=your_account@smartsurgerytek.com
export GCP_REGION=asia-east1
export GCP_ZONE="${GCP_REGION}-a"
export YOUR_NAME=name
export INSTANCE_NAME="${YOUR_NAME}-cvat-${GCP_ZONE}"
export PUBLIC_KEY_PATH=/path/to/your/public/key.pub
```
- `YOUR_NAME`: An arbitrary name for setting instance name, for example: `eason`.
- `PUBLIC_KEY_PATH`: Path to your public key. For example: `$HOME/.ssh/id_rsa.pub`. I used rsa. The key content is better to have a name prefix like `eason:ssh-rsa ABCDEFGHIJKLMNOPQRSTUVWXYZ123456790... eason.li@smartsurgerytek.com`.
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
gcloud config set project_you_want
```
## Create a Google Compute Instance
```bash
gcloud compute instances create $INSTANCE_NAME \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --machine-type=e2-custom-4-32768 \
  --boot-disk-size=200GB \
  --boot-disk-type=pd-balanced \
  --zone=${GCP_ZONE} \
  --tags=cvat-8080 \
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
### SSH into the Created VM
```bash
gcloud compute ssh $INSTANCE_NAME -- "export CVAT_HOST=${EXTERNAL_IP} && exec bash -l"
```
---
## Run CVAT
**NOTICE**: Commands in the following sections should be executed inside the Google Compute Engine (GCE) instance you created above, excepting `gcloud` commands.
### Clone this repo
```bash
git clone https://github.com/smartsurgerytek/dentistry-annotation-cvat.git
cd dentistry-annotation-cvat
```
### Install Docker
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
### Run CVAT
```bash
docker compose up -d
```
you need to attach your terminal into the `cvat_server` container to do some basic setup.
```bash
docker exec -it cvat_server python manage.py migrater
docker exec -it cvat_server python manage.py collectstatic
docker exec -it cvat_server python manage.py syncperiodicjobs
docker exec -it cvat_server python manage.py createsuperuser --username admin
```
Follow the prompt to setup email(option) and password.

You can check your IP address here:
```bash
echo $CVAT_HOST
```
Check if you can use your browser to open http://$CVAT_HOST:8080

### Setup GCP Domain
```bash
gcloud dns record-sets transaction start --zone=smartsurgerytek-net
gcloud dns record-sets transaction add $EXTERNAL_IP \
  --name="dev0.smartsurgerytek.net." \
  --ttl=300 \
  --type=A \
  --zone=smartsurgerytek-net
gcloud dns record-sets transaction execute --zone=smartsurgerytek-net
```

### Start CVAT in `smartsurgerytek.net` domain
Remember to compose down if you compose up before
```bash
docker compose down
```
Set `CVAT_HOST` environment variable, replace the `your_subdomain` with your sub-domain:
```bash
export CVAT_HOST=your_subdomain.smartsurgerytek.net
```
compose up again:
```bash
docker compose up -d
```
Check if you can use your browser to open http://your_subdomain.smartsurgerytek.net:8080

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
### Compose Up with Nuclio Container
```bash
docker compose -f docker-compose.yml -f components/serverless/docker-compose.serverless.yml up -d
```
### Clone `smartsurgerytek/dentistry-annotation-nuclio/` Repository
```bash
cd ~
git clone https://github.com/smartsurgerytek/dentistry-annotation-nuclio.git
cd dentistry-annotation-nuclio
```
### Deploy the Measurement Function
```bash
nuctl deploy measurement --path ./src/measurement/ --project-name cvat --platform local
```
If this is your first time to deploy, you have to what for a while due to it need to build the graphic library for pytorch, and it's huge.

### Upload Image
```bash

```

## Clean Up
### Remove a Google Compute Instance
```bash
gcloud compute instances delete $INSTANCE_NAME
```