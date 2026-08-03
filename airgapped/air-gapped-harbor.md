# Appendix: VMware Bootstrap Registry Appliance Deployment Guide

## In this document, we will only capture the additional steps and/or differences that have not been addressed in the [primary air gap install document](/airgapped/air-gapped.md) ,specifically detailing the configuration and deployment of the  VMware Bootstrap Registry Appliance.  

## Introduction
In air-gapped scenarios, the lack of connectivity makes it challenging to deploy a Harbor Supervisor Service as platform registry for workloads and infrastructure. In such scenarios, a bootstrap registry is required which can bootstrap the platform registry.  
This document details using the VMware Bootstrap Registry Appliance as the Bootstrap Registry (Registry 0) to deploy Harbor Supervisor Service (v2.14.3) on vCenter.  
The process involves the following significant steps:

- Copy the relevant files and binaries to be moved to the air-gapped environment.
- Enable the Supervisor.
- Upload Kubernetes release OVAs to a Content Library.
- Create vSphere Namespace(s) for VKS Clusters(s).
- Configure the air-gapped Admin host in the air-gapped environment. 
- **(NEW) Deploy VMware Bootstrap Registry Appliance.**
- **(NEW) Install Contour and Harbor Supervisor Service to be used as Platform Registry.**
- Mirror Platform registry with the relevant container images to be used by the platform. 
- Install the relevant Supervisor Services.
- Deploy the VKS Cluster(s).
- Deploy the Tanzu Packages on the VKS Cluster(s).

## Terminology
* Bootstrap registry - An OCI-compliant Harbor registry will be deployed on the vCenter. This registry will be used exclusively to upload the binaries necessary to enable Contour and Harbor Supervisor services on the Supervisor. It will not be utilized for any other purpose.
* Platform registry - A Harbor Supervisor Service that performs all functionalities of an Enterprise grade Platform registry.

The data flow of packages, binaries, and images between the internet-connected and air-gapped environment can be summarized by the picture below -

<img width="1338" height="730" alt="image" src="https://github.com/user-attachments/assets/1ce442d7-b227-4665-b95b-0ca53e299bec" />


## Bill of Materials
Besides the BOM referenced in the [primary air gap install document](/airgapped/air-gapped.md), we will be leveraging the following additional components - 

|Component|Version|Sample Hostname|
|---------|-------|----------------------------------|
|vCenter|9.0.0.0 / 8.0.3.0|vcenter.env1.lab.test|
|Bootstrap Registry|Harbor v2.15.2|registry0.env1.lab.test|
|Platform/Enterprise Registry|Harbor v2.14.3|registry1.env1.lab.test|

## 1. Download all required Plugins, Binaries, and Images
Besides downloading all the plugins, binaries, and images addressed in the [primary air gap install document](/airgapped/air-gapped.md) -

### 1e. Download VMware Bootstrap Registry Appliance 
Before enabling Supervisor Services in an air-gapped environment, we must host images in a bootstrap container registry. This bootstrap repository will be used exclusively to host the necessary images to enable Contour and Harbor Supervisor Services; it will not be utilized for any other purpose. Download the official, fully supported production-grade VMware Bootstrap Registry Appliance OVA from the Broadcom/vCenter software portal. This appliance is pre-hardened on Photon OS 5.0 and natively hosts a secure OCI Harbor registry.
* Download Location for vSphere 8.0 - Broadcom Support Portal - My Downloads - vSphere - VMware vSphere Standard - 8.0 - Drivers & Tools - BOOTSTRAP_APPLIANCE-2.15.2+vmware.1-25635995.ova
* Download Location for VCF 9.0 - Broadcom Support Portal - My Downloads - VMware Cloud Foundation - VMware Cloud Foundation 9 - 9.0.2 - VMware vCenter - Drivers & Tools - BOOTSTRAP_APPLIANCE-2.15.2+vmware.1-25635995.ova

### 1f. Download Trivy Database for Platform Registry (Harbor Supervisor Service)
The Trivy vulnerability scanning database is available for download from gcr.io and is updated periodically. In an air-gapped environment, this database must be periodically downloaded to the Bootstrap machine and then moved to the air-gapped environment to be installed on the Platform container registry (Harbor Supervisor Service). 

```bash
TRIVY_TEMP_DIR=$(mktemp -d)
echo $TRIVY_TEMP_DIR

sudo curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sudo sh -s -- -b /usr/local/bin v0.58.0

### Sample output
### aquasecurity/trivy info checking GitHub for tag 'v0.58.0'
### aquasecurity/trivy info found version: 0.58.0 for v0.58.0/Linux/64bit
### aquasecurity/trivy info installed /usr/local/bin/trivy

trivy --cache-dir $TRIVY_TEMP_DIR image --download-db-only  

### Sample output
### 2025-01-04T00:10:09Z	INFO	[vulndb] Need to update DB
### 2025-01-04T00:10:09Z	INFO	[vulndb] Downloading vulnerability DB...
### 2025-01-04T00:10:09Z	INFO	[vulndb] Downloading artifact... repo="mirror.gcr.io/aquasec/trivy-db:2"
### 58.26 MiB / 58.26 MiB [----------------------------------------------] 100.00% 21.18 MiB p/s 3.0s
### 2025-01-04T00:10:14Z	INFO	[vulndb] Artifact successfully downloaded	### repo="mirror.gcr.io/aquasec/trivy-db:2"
```

### Summary
Copy **these additional files** to the Admin host within the air-gapped environment. 

## Complete Steps 2, 3, 4, and 5 referenced in the [primary air gap install document](/airgapped/air-gapped.md)

## Deploy VMware Bootstrap Registry Appliance
Deploying the VMware Bootstrap Registry OVA follows the same process as deploying any other OVA in vCenter. During the deployment in vCenter (or via ovftool / CLI deployment), you must configure system parameters under the Customize Template step.
During this stage, SSL/TLS certificate configuration offers two options:

### Option 1: Generate-New (Auto-Generated Certificate)
When selecting Generate-New, the appliance automatically generates a private Root CA and signs a new SSL/TLS server certificate matching the configured appliance FQDN during firstboot initialization.

#### Step-by-Step Instructions:
* In the vCenter Deploy OVF Template wizard, proceed to the Customize Template screen.
* Locate the Certificate Configuration section and set Certificate Type to Generate-New.
* Fill in the required certificate subject fields:
* Business Unit Name: Department or business unit (e.g., Finance).
* CA Common Name: Root CA Common Name (e.g., ca.example.com). Note: Must differ from server_fqdn.
* Country Name: 2-letter ISO country code (e.g., US).
* County Name: Locality or county name (e.g., Palo Alto).
* Organization Name: Company or organization name (e.g., Broadcom).
* State Name: State or province name (e.g., California).
* Configure remaining networking properties (IP, FQDN, DNS, Gateway, Passwords) and click Next / Finish to complete deployment.


### Option 2: Customer-Provided (Custom Certificate)
When selecting Customer-Provided, administrators supply custom SSL/TLS server certificates, private keys, and trusted CA certificate bundles encoded in Base64 format during OVA import.

#### Step-by-Step Instructions:
* Prepare your custom X.509 PEM certificate files on your administrative workstation:
* Server Certificate file (server.crt)
* Server Private Key file (server.key)
* Root / Intermediate CA Certificate file (ca.crt)
* Encode each certificate file into a single-line Base64 string:
* Linux/MacOS Terminal
```bash
base64 -w 0 server.crt
base64 -w 0 server.key
base64 -w 0 ca.crt
```
* Windows Powershell
```bash
[Convert]::ToBase64String([IO.File]::ReadAllBytes("server.crt"))
[Convert]::ToBase64String([IO.File]::ReadAllBytes("server.key"))
[Convert]::ToBase64String([IO.File]::ReadAllBytes("ca.crt"))
```
* In the vCenter Deploy OVF Template wizard, proceed to the Customize Template screen.
* Locate the Certificate Configuration section and set Certificate Type to Customer-Provided (default).
* CA Cert: Paste Base64 string of ca.crt. (Optional when using public certificates from vendors such as DigiCert).
* Server Cert: Paste Base64 string of server.crt.
* Key of Server Certificate: Paste Base64 string of server.key.
* Configure remaining networking properties and click Next / Finish to complete deployment.


Once Bootstrap Registry  is deployed and running, login to the Harbor UI using the `admin` user and the password provided during deployment.


### Add the Bootstrap Registry certificate to the Supervisor
The Supervisor must trust the Bootstrap registry certificate. To perform this step, navigate to Workload Management -> Supervisor -> Configure -> Container Registries. Click on Add Registry. 

![image](add-cert2.png)

Input the Registry host URL, TLS Certificate of the registry (the content of `registry0.crt`), Username, and Password. Note that while the UI states that the Username and Password are optional, they are currently mandatory.

![image](add-cert3.png)

### Add the Bootstrap Registry certificate to the Admin host Trust Store
You can use the commands below to add the Bootstrap Harbor certificate to the Admin host trust store. 

```bash
## Commands specific to Ubuntu
sudo cp registry0.crt /usr/local/share/ca-certificates 
sudo update-ca-certificates
```

Once the certificate is added to the trust store, log in to the Bootstrap Harbor endpoint using Docker. 

```bash
## Restart Docker Service
systemctl reload docker
systemctl restart docker

## Command to Login to Harbor Endpoint
docker login <repo-endpoint>


## Enter the username and password when prompted. The expected output is shown below:
=====
WARNING! Your password will be stored unencrypted in /root/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credential-stores

Login Succeeded
=====
```

### Upload Harbor and Contour Supervisor Services to the Enterprise Registry
Create a project, `sup-services,` with public access within the Bootstrap registry to upload Contour and Harbor Supervisor Services that must be installed on the Supervisor.


The Contour and Harbor Supervisor Services image bundle binaries downloaded in Step 1d must now be uploaded to the Bootstrap Harbor registry. Follow [steps 4 and 5 from the official documentation](https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere-supervisor/8-0/vsphere-supervisor-services-and-workloads-8-0/deploying-supervisor-services-from-a-private-container-image-registry/relocate-supervisor-services-to-a-private-registry.html) to complete this critical step. While the official documentation refers to the `imgpkg` binary to perform the download function, the Tanzu CLI's `imgpkg plugin` performs an identical function. 

```bash
## Sample Commands
tanzu imgpkg copy --tar contour-v1.33.1.tar --to-repo registry0.env1.lab.test/sup-services/contour --cosign-signatures
tanzu imgpkg copy --tar harbor-v2.14.3.tar   --to-repo registry0.env1.lab.test/sup-services/harbor  --cosign-signatures
```

Additionally, the corresponding Contour and Harbor Supervisor Service YAMLs need to be updated with the new Bootstrap registry valid location -

```yaml
# Contour.yaml
...
Template:
  Spec:
    Fetch:
    - imgpkgBundle:
        image: registry0.env1.lab.test/sup-services/contour:v1.33.1_vmware.2-vks.1
...
```

```yaml
# harbor.yaml
...
Template:
  Spec:
    Fetch:
    - imgpkgBundle:
        image: registry0.env1.lab.test/sup-services/harbor:2.14.3_vmware.2-vks.1
...
```

Once completed, add the required Supervisor Services to the Supervisor using the [steps provided in the documentation](https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere-supervisor/8-0/vsphere-supervisor-services-and-workloads-8-0/deploying-supervisor-services-from-a-private-container-image-registry/install-and-use-the-supervisor-service.html).

## Install Contour and Harbor Supervisor Service to be used as Platform Registry

Follow the directions to install Contour and Harbor as Supervisor Service provided [here](https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere-supervisor/8-0/vsphere-supervisor-services-and-workloads-8-0/installing-and-configuring-harbor-and-contour.html). 

### Harbor customization
For an air-gapped install, we have to disable the Trivy scanner from trying to update its database from the internet. To do so, we must append the following section at the end of the sample `harbor-data-values.yml` file. 

```yaml
# harbor-data-values.yml

trivy:
  enabled: true
  skipUpdate: true
  offline scan: true
```
---
## Complete Steps 6, 7, and 8 referenced in the primary air-gapped document.
While completing these steps, replace the reference to the Enterprise Registry with the Platform Registry (Harbor Supervisor Service)
