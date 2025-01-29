# Deploying a model server on a small VM

Deploy a model in the hackiest, simplest way possible - by starting a process on a manually created VM.

1. Train a model.
```bash
cd ~/designing-ml-systems/examples/simple-deploy-model/
python -m pip install -r requirements.txt
python train.py
```

2. Create a VM with public endpoints exposed and Python installed.
```bash
gcloud compute instances create model-server \
    --zone=us-central1-a \
    --machine-type=n1-standard-4 \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --tags=http-server,https-server \
    --boot-disk-size=100GB \
    --metadata=startup-script='#! /bin/bash
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip build-essential libssl-dev libffi-dev python3-dev gfortran libopenblas-dev liblapack-dev'
``````

3. You might need to create a firewall rule as well.

```bash
gcloud compute firewall-rules create default-allow-http \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:80 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=http-server
```

4. Copy files to GCS.
Note: this is copying to machine-learning-workspace project b/c of quota-project issue, but let's keep going for now.

```bash
gsutil mb gs://${USER}
gsutil cp -r ~/Code/mvc/simple-deploy-model gs://${USER}/mvc/simple-deploy-model
```


5. SSH into the instance.
```bash
gcloud compute ssh model-server --zone=us-central1-a
```

You'll need to create an SSH password.

6. Copy files down from GCS.

```bash
gsutil cp -r gs://arubino/mvc/simple-deploy-model .
cd simple-deploy-model
```

7. Install requirements.

```bash
sudo python3 -m venv .venv
source .venv/bin/activate
sudo .venv/bin/pip3 install --upgrade pip
sudo .venv/bin/pip3 install -r requirements.txt
```

8. Start the model server on port 80.

```bash
sudo .venv/bin/uvicorn app:app --reload --port 80 --host "0.0.0.0"
```

9. Make a request to the public IP.

```bash
EXTERNAL_IP=IPADDRESS
curl -X POST "http://$EXTERNAL_IP/predict" \
     -H "Content-Type: application/json" \
     -d '{"feature_1": "2025-01-25"}'
```

10. Delete the instance.

```bash
gcloud compute instances delete model-server \
    --zone=us-central1-a
```