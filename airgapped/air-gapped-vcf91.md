# VKS Deployment Guide for VCF 9.1.0 Air-Gapped Environments

## Introduction
The complete procedure to install a VKS cluster with additional VKS add-ons within an air-gapped environment involves the following significant steps:

- Copy the relevant files and binaries to be moved to the air-gapped environment.
- Enable the Supervisor.
- Upload Kubernetes release OVAs to a Content Library.
- Create vSphere Namespace(s) for VKS Clusters(s).
- Configure the air-gapped Admin host in the air-gapped environment. 
- Import OCI images of supervisor services or VKS add-ons to the distribution docker registry on Software Depot.
- Install the relevant Supervisor Services.
- Deploy the VKS Cluster(s).
- Deploy the VKS add-ons on the VKS Cluster(s).

The data flow of packages, binaries, and images between the internet-connected and air-gapped environment can be summarized by the picture below -

![image](/airgapped/ocireg-dataflow.png)

## Terminology
* **Bastion Host** A host (preferably a Linux VM) that is connected to the Internet or has access to download packages, binaries, and images from the Internet.
* **Admin Host** A host (preferably a Linux VM) within the air-gapped environment without internet access. The Admin host generally has network connectivity to all the hosts in the air-gapped environment. Files downloaded from the Internet to the Bastion host are transferred to the Admin Machine, and administrators can use it to interact with the platform.
* **VCF CLI** A plugin-based CLI that is used to interact with the Supervisor and VKS clusters
* **VKS add-ons** VKS add-ons enable administrators and users to add and manage standard services and add-ons on Kubernetes clusters using the VCF CLI or Carvel Custom Resources.

## Prerequisites
For VCF / VVF 9.1.0 deployments, the distribution docker registry in VCF Software Depot can be used as the OCI compliant registry to host OCI images for Supervisor Services and VKS add-ons, and please follow this VKS deployment guide for Air-Gapped Environments.
For VCF / VVF deployments based on prior-9.1.0 releases, an Enterprise OCI-compliant registry is required, and please follow this [document](/airgapped/air-gapped.md) for VKS deployment in Air-Gapped environments.

## Bill of Materials
The table below provides sample hostnames and versions used throughout the document for easy reference -

|Component|Version|Sample Hostname (where applicable)|
|---------|-------|----------------------------------|
|Bastion Host|Ubuntu 24.04.4|bastion.internet.lab.test|
|Admin Host (Air-gapped)|Ubuntu 24.04.4 (identical to the Bastion Host)|admin.env1.lab.test|
|vCenter|9.1.0|vcenter.env1.lab.test|
|ESXi|9.1.0|esxi[0..xxx].env1.lab.test|
|Supervisor|9.1.0|supervisor0.env1.lab.test|
|Enterprise Registry||registry1.env1.lab.test|
|TKC|v1.32.10/v1.33.6/v1.34.2|workload-vsphere-vks1|
|VKS Add-ons|3.6.0-20260211||
|VKS Service|3.6.1||

Additionally, it is crucial to have the following packages and binaries installed on both the Bastion and Admin Host - 
* `wget`
* `curl`
* `docker` (Preferably from the Docker website [https://docs.docker.com/engine/install/])
* `jq`
* `yq` (Some Linux distributions come with their implementation of yq. These packages are not the latest and/or provide the full functionalities. The newest version of the yq package can be downloaded from [https://github.com/mikefarah/yq/releases])
* `openssl` for certificate generation and validations.
* `imgpkg` to pull and push Carvel package images, install doc reference: [https://carvel.dev/imgpkg/docs/develop/install/#via-script-macos-or-linux].
* `python3` to run the python 3 based image migration script, install doc reference: [https://www.python.org/downloads/].
* Additional troubleshooting and diagnostic tools as needed. 

## 1. Download all required Plugins, Binaries, and Images
This document utilizes an Ubuntu 24.04.4-based Bastion host (**bastion.internet.lab.test**) for this stage. Below are the key plugins and packages that must be downloaded, each playing a critical role in the platform deployment process.

### 1a. Kubernetes Release OVA files
Kubernetes releases provide the Kubernetes software distribution for VKS clusters. VMware distributes Kubernetes releases as virtual machine templates, which you synchronize with the platform using a vCenter Content Library. Download the latest Kubernetes release files from https://wp-content.broadcom.com/v2/latest/. The versions to be downloaded may depend on the workload requirements. It would be the best to download three or more of the latest versions. Follow [Step #11 from the official documentation](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vsphere-supervisor-services-and-standalone-components/9-1/managing-vsphere-kubernetes-service/administering-kubernetes-releases-for-tkg-service-clusters/create-a-local-content-library-for-air-gapped-cluster-provisioning.html) to download the relevant Kubernetes release files for each version.  

### 1b. VCF CLI and Plugins
While the VCF CLI and its plugins will be installed on the Bastion host (`bastion.internet.lab.test`), they must also be copied to the Admin Machine as part of the file transfer process. When this document was written, VCF CLI 9.1.0 is supported with vSphere and Supervisor 9.1.0. The steps below involve installing the VCF CLI on the Bastion host, which is necessary to download the VCF CLI plugins. Plugins can be downloaded and installed as required. The required VCF CLI binary can be downloaded from the home page of the vSphere Supervisor or from VCF Automation Tenant Portal in VCF online deployments, in internet restricted environments, follow [Installing the VCF CLI in Internet Restricted Environments](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/building-your-cloud-applications/getting-started-with-the-tools-for-building-applications/installing-and-using-vcf-cli-v9/installing-the-vcf-cli-in-internet-restricted-environments(2).html) to download VCF Consumption CLI and plugins, the steps are summarized as below.

```bash
## Download VCF CLI and VCF CLI Plugins
1. Open a browser and navigate to https://support.broadcom.com.
2. Login with your account credentials.
3. Navigate to `My Downloads` page and search for `VCF consumption CLI`.
4. Click on `VCF consumption CLI` to navigate to the VCF consumption CLI download page.
5. Click on `CLI` link, then select release version 9.1.0 to download the desired VCF CLI tar for the target OS to run VCF CLI commands.
6. Click on `Plugin-Bundles` link, then select release version 9.1.0 to download the desired VCF CLI plugin bundle tar for the target OS to run VCF CLI commands.

## Install VCF CLI on the bastion host (Linux/amd64 example)
tar -xzvf ./VCF-Consumption-CLI-Linux_AMD64-9.1.0.tar.gz
sudo install ./vcf-cli-linux_amd64 /usr/local/bin/vcf

## Verify the installation
vcf version

## Install the desired VCF CLI plugins on the bastion host from the plugin bundle
mkdir -p ~/vcf-plugin-bundle
tar -xvzf VCF-Consumption-CLI-PluginBundle-Linux_AMD64-9.1.0.tar.gz -C ~/vcf-plugin-bundle/

## Install a single plugin (example: vm) or all plugins
vcf plugin install vm  --local-source ~/vcf-plugin-bundle/
vcf plugin install all --local-source ~/vcf-plugin-bundle/

## Verify the plugins are installed
vcf plugin list
```

### 1c. VKS Add-ons
VKS add-ons enable administrators and users to use the VCF CLI or Carvel Custom Resources to add and manage standard services and add-ons on Kubernetes clusters. With VKS add-ons, you can deploy various add-ons to VKS Clusters, such as cert-manager, Contour, Prometheus, Grafana, and more. Download the relevant the VKS add-on bundle using the following command via the image migrator python script -

```bash
./oci_image_depot_migrator.py download -s projects.packages.broadcom.com/vsphere/supervisor/vks-standard-packages/3.6.0-20260211/vks-standard-packages:3.6.0-20260211
```

### 1d. Binaries and YAML files required for Supervisor Services
Supervisor Services are Carvel packages and are defined by their configuration file. The configuration file contains the reference to the image that holds the package manifest. As a prerequisite for migrating the Supervisor Services to the distribution docker registry on Software Depot, we need to extract the value of the image containing the package manifest. To do so, we can download the configuration YAML file with `legacy` in the file name and look for the following key - `spec.template.spec.fetch.imgpkgBundle[].image` for the Package object. For example, in the configuration file for the ArgoCD Operator 9.1.0: `supervisor-service-argocd-legacy-1.1.0-25166333.yml`, the value is the image that would need to be migrated to the air-gapped environment: `projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service:v1.1.0_vmware.1`.

```yaml
...
---
apiVersion: data.packaging.carvel.dev/v1alpha1
kind: Package
metadata:
  name: argocd-service.vsphere.vmware.com.1.1.0-25100889
spec:
  refName: argocd-service.vsphere.vmware.com
  template:
    spec:
      deploy:
      - kapp: {}
      fetch:
      - imgpkgBundle:
          image: projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service:v1.1.0_vmware.1
...
```

####, E.g., Download ArgoCD Supervisor Service Binaries and associated YAML files.
When writing this document, the latest version of the ArgoCD Supervisor Service is “v1.1.0”. Please refer to ​​the vSphere Supervisor Services page on Broadcom Support Portal to check for the updated versions. There will be 2 configuration files for version v1.1.0: `supervisor-service-argocd-legacy-1.1.0-25166333.yml` and `supervisor-service-argocd-depot-1.1.0-25166333.yml`. Download both files required for the ArgoCD Supervisor Service. Locate the value of the image from the `supervisor-service-argocd-legacy-1.1.0-25166333.yml` file as described above. The second configuration file `supervisor-service-argocd-depot-1.1.0-25166333.yml` (without `legacy` in the name) is the configuration file that should be used to register and install on a Supervisor 9.1.0.

You can execute the following command from the Bastion host to download the image bundle as a tarball.

```bash
## Download Contour Binaries
./oci_image_depot_migrator.py download -s projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service:v1.1.0_vmware.1
```
A bundle tar file will be downloaded to the same directory as the python script by default, perform similar steps for other Supervisor Services that must be installed in the air-gapped environment. The configuration YAML files of Supervisor Services can be discovered on [Broadcom Support Portal](https://support.broadcom.com) by searching for `supervisor services` and clicking on `vSphere Supervisor Services` after login and navigating to `My Downloads`.

The table below provides the sample list of Supervisor Services that can be downloaded from Broadcom Support Portal and installed on the platform -

|Service Name|Type|Version|
|------------|----|-------|
|VKS Service|Core|3.6.1|
|Contour|Standard|1.33.1|
|Harbor|Standard|2.14.2|
|Consumption Interface|Standard|9.1.0|
|ExternalDNS|Standard|v0.18.0|
|ArgoCD|Standard|1.1.0|

### Summary
The following files, binaries, and packages have been successfully downloaded in this section and **must be transferred to the Admin host**.
* Kubernetes Release OVA files.
* VCF CLI tar (e.g. `VCF-Consumption-CLI-Linux_AMD64-9.1.0.tar.gz`).
* VCF CLI plugin bundle tar (e.g. `VCF-Consumption-CLI-PluginBundle-Linux_AMD64-9.1.0.tar.gz`).
* kubectl binary (extracted from `vsphere-plugin.zip`).
* VKS Add-on bundle tar produced by the image migrator (e.g. `vks-standard-packages-3.6.0-20260211.tar`). This file can be gzipped if needed.
* Supervisor Service image bundle tars and their configuration YAML files.

## 2. Enable the Supervisor
Using the steps and directions in the official [documentation](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/vsphere-supervisor-installation-and-configuration.html), configure the required networking, storage policies, and profiles and enable the Supervisor on `vcenter.env1.lab.test`.

## 3. Create a Kubernetes release content library and upload Kubernetes release images
The Kubernetes release OVAs downloaded on the Bastion host and copied to the Admin host must be uploaded to a Content library within the vCenter. Before proceeding, a local content library must be created. The "Create a Local Content Library (for Air-Gapped Cluster Provisioning)" [documentation](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/vsphere-supervisor-installation-and-configuration/updating-vsphere-supervisor/updating-the-vsphere-with-tanzu-environment/configuring-a-subscribed-content-library-for-supervisor-images-in-air-gapped-environment/create-a-remote-content-library-pulisher-in-a-local-environment.html) provides instructions on creating and importing Kubernetes Release (Kr) images into the content library. **Step #12** provides details on files (downloaded previously in step 1a) that need to be uploaded to the local content library.

## 4. Create vSphere Namespace(s) for VKS Clusters(s)
If not already created, a vSphere namespace should be created. Refer to "[Create and Configure a vSphere Namespace on the Supervisor](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/vsphere-supervisor-installation-and-configuration/configuring-and-managing-vsphere-namespaces/create-and-configure-a-vsphere-namespace.html)" to configure the vSphere Namespace.

## 5. Configure Admin host
The Admin host (**admin.env1.lab.test**) is essential to the next deployment stage. It performs crucial tasks such as uploading binaries and image bundles to the repository, deploying VKS Clusters, and deploying Add-on packages on the VKS Clusters. As the control center, this machine enables effective deployment management and repository coordination. This document uses an `Ubuntu 24.04.4` machine with *Docker* installed on the Admin Machine. If Docker isn't installed, please review the [official documentation](https://docs.docker.com/engine/install/ubuntu/) for installation guidance. The instructions may have to be modified for an airgapped installation. The recommended system configuration is as follows:
* CPU: 2 vCPUs
* Memory: 4 GB
* Storage: 150–200 GB of free space

Note: Before moving forward, verify that all the files mentioned in the Summary section in Step 1 have been successfully copied to the Admin host.

### 5a. Download and Install kubectl CLI
`kubectl` is the command-line tool used to interact with Kubernetes clusters. It allows users to manage and inspect resources within a Kubernetes environment. `kubectl-vsphere` is a VMware-specific plugin for `kubectl` that enables administrators and developers to interact with the Supervisor and manage VKS clusters running on vSphere. It is deprecated since vSphere 9.1.0, and not needed here.

You can download and install the `kubectl` plugin to your Admin machine by accessing the Supervisor Cluster Kube-API server endpoint UI or using the command below.

```bash
wget https://<Supervisor-KubeAPI-Endpoint>/wcp/plugin/linux-amd64/vsphere-plugin.zip --no-check-certificate

## Sample Command:
wget https://supervisor0.env1.lab.test/wcp/plugin/linux-amd64/vsphere-plugin.zip --no-check-certificate

## After downloading the vsphere-plugin.zip file, use the following commands to unzip it and add the kubectl binary to the executable path.
unzip ./vsphere-plugin.zip
cd ./bin
sudo install kubectl /usr/local/bin/kubectl

## Verify the version by executing the below command
kubectl version
```

### 5b. Login to Supervisor
If not logged in, log in to the Supervisor using VCF CLI. Note the VCF CLI and needed CLI plugins are expected to be already installed during the Baston host setup.

```bash
# Connect to vSphere Namespace using VCF CLI
vcf context create <context-name> --endpoint <SupervisorAPIEndpoint> --username <sso_username> --type k8s --insecure-skip-tls-verify
vcf context use <context-name>:<namespace-name>

## Sample Command
vcf context create supervisor1 --endpoint https://supervisor0.env1.lab.test --username administrator@vsphere.local --type k8s --insecure-skip-tls-verify
vcf context use supervisor1:ns01
```

### 5c. Enable OCI image upload on Software Depot

Follow the following steps to enable OCI image upload on Software Depot:

#### 5c1. Create a config JSON file as config.json with the following config:
```
{
  "spec": {
    "configuration": {
      "oci": {
        "offlineWriteEnabled": true
      }
    }
  }
}

#### 5c2. Apply the config.json to Software Depot via API by following commands below after login to VCF OPS:
```
# Discover the VCF services runtime FQDN by login to VCF OPS and navigate to Build --> Lifecycle --> VCF management --> Components, and export as env variable.
export PLATFORM_HOST=https://{VCF_SERVICES_RUNTIME_FQDN};

# Export OPS admin and password as env variable.
export ADMIN_PASSWORD='{OPS_ADMIN_PASSWORD}';
export ADMIN_USERNAME='{OPS_ADMIN_USERNAME}';

# Get access token via the OPS admin login.
export TOKEN=`curl -k -XPOST  ${PLATFORM_HOST}/api/v1/identity/token \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data grant_type=password \
  --data "username=${ADMIN_USERNAME}" \
  --data "password=${ADMIN_PASSWORD}" | jq -r '.access_token'`;

echo "token is $TOKEN";

# Discover the component ID of the `vcf-fleet-depot` component.
export VCF_FLEET_DEPOT_COMPONENT_ID=$(curl -H"Authorization: Bearer ${TOKEN}" -k ${PLATFORM_HOST}/api/v1/components | jq -r '.components[] | select(.name == 'vcf-fleet-depot') | .id')

# Apply the config to the Software Depot, this will return a task ID.
export TASK_ID=$(curl -k -XPOST -H"Authorization: Bearer ${TOKEN}" ${PLATFORM_HOST}/api/v1/components/${VCF_FLEET_DEPOT_COMPONENT_ID}?action=apply -d @./config.json | jq -r '.id')

# monitor the task until the task status returns succeeded.
curl -k -XGET -H"Authorization: Bearer ${TOKEN}" ${PLATFORM_HOST}/api/v1/tasks/${TASK_ID} | jq | grep status
```

## 6. Ensure regional Harbor is configured on Supervisor.

In a VCF deployment with VCF Automation installation, follow this [documentation](https://author-techdocs2-prod.adobecqms.net/content/output/sites/docworks-preview/installing-and-configuring-supervisor-services-ditamap/using-harbor-as-vcf-service/using-harbor-as-a-vcf-service.html?wcmmode=disabled) to install and configure regional Harbor as a VCF service on a Supervisor in a VCF region. If the VCF deployment doesn't have VCF Automation or it's a VVF deployment, follow this [documentation](https://author-techdocs2-prod.adobecqms.net/content/output/sites/docworks-preview/instaiing-and-configuring-supervisor-services-ditamap/using-harbor-as-vcf-service/installing-and-configuring-harbor-and-contour/deploy-harbor-supervisor-service-in-vvf-without-vcfa.html?wcmmode=disabled) to install Harbor Supervisor Service on the Supervisor.

## 7. Upload Packages to the Software Depot

### 7a. Upload VKS Add-on Packages to the distributon registry on Software Depot
The VKS Add-on package bundle, downloaded in Step 1c, must be uploaded to the Enterprise registry using the provided python script. 

```bash
## Sample Command
./oci_image_depot_migrator.py upload -s projects.packages.broadcom.com/vsphere/supervisor/vks-standard-packages/3.6.0-20260211/vks-standard-packages:3.6.0-20260211 -t fleet-10-144-79-70.vcfd.broadcom.net
```

In case the admin host is in DMZ and has connectivity to projects.packages.broadcom.com, the VKS Add-on packages can be copied from projects.packages.broadcom.com directly to Software Depot by using below command.

```bash
## Sample Command
./oci_image_depot_migrator.py copy -s projects.packages.broadcom.com/vsphere/supervisor/vks-standard-packages/3.6.0-20260211/vks-standard-packages:3.6.0-20260211 -t fleet-10-144-79-70.vcfd.broadcom.net
```

### 7b. Upload Supervisor Services to the distributon registry on Software Depot
All the Supervisor Services image bundle binaries downloaded in Step 1d must be uploaded to the Software Depot by using the provided oci_image_depot_migrator.py script.

```bash
## Sample Command
./oci_image_depot_migrator.py upload -s projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service:v1.1.0_vmware.1 -t fleet-10-144-79-70.vcfd.broadcom.net
```

In case the admin host is in DMZ and has connectivity to projects.packages.broadcom.com, the Contour Supervisor service images can be copied from projects.packages.broadcom.com directly to Software Depot.

```bash
## Sample Command
./oci_image_depot_migrator.py copy -s projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service:v1.1.0_vmware.1 -t fleet-10-144-79-70.vcfd.broadcom.net
```

## 8. Deploy VKS Cluster(s)

### 8a. Update vSphere Kubernetes Service (VKS) to the latest version
When writing the documentation, the latest VKS release was v3.6.3. Since each VKS release introduces additional features and fixes, we must apply these updates to make the new features and fixes available. This document will update the core VKS from 3.6.1 to 3.6.3. Follow the relevant sections in the [documentation](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vsphere-supervisor-services-and-standalone-components/latest/managing-vsphere-kubernetes-service/installing-and-upgrading-the-tkg-service/upgrade-the-tkg-service-version.html) to complete the upgrade. 

### 8b. Deploy a Workload Cluster
Deploying a VKS Cluster (using an Ubuntu image). Review each section at a minimum and adjust the necessary fields as needed. Refer to the [“Using the Cluster v1beta1 API” documentation](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vsphere-supervisor-services-and-standalone-components/9-1/managing-vsphere-kuberenetes-service-clusters-and-workloads/provisioning-tkg-service-clusters/workflow-for-provisioning-tkg-clusters-using-kubectl.html) for more configuration options.
* Control Plane Size:  
** Nodes: 1 or 3 for high availability 
** vCPUs: 4, Memory: 16GB, Storage: 50GB
* Worker Node Size: 
** Nodes: 3 for a standard-size stack 
** vCPUs: 4, Memory: 16GB, Storage: 50GB

While `v1beta1` provides numerous configuration options, the following additional variables may be added for a default `podSecurityStandard` and additional certificate `trust.` 
```yaml
## vksConfig.yaml
...
    variables:
      - name: podSecurityStandard
        value:
          audit: restricted
          auditVersion: latest
          enforce: privileged
          enforceVersion: latest
          warn: privileged
          warnVersion: latest
#      Uncomment the below lines if using an Enterprise registry. See above section 8b 
#      - name: trust
#        value: 
#          additionalTrustedCAs:
#          - name: additional-ca-1
...
```

```bash
## If using Enterprise registry with a private certificate. Please take a look at section 8b.
kubectl apply -f <additional-ca-1.yaml> -n ns01

## Deploy VKS cluster
kubectl create -f <vksConfig.yaml> -n ns01

## Command to check the status of Cluster Creation
Kubectl get cluster -n ns01
kubectl describe cluster workload-vsphere-vks1 -n ns01
```

### 8c. Deploy VKS Add-on Package(s) on Workload Cluster
VKS Add-on packages can be deployed from the VKS Standard repository using the VCF CLI from the Admin host. We will use `cert-manager` as an example to demonstrate the ease of deploying these packages. We must first add the package repository to the VKS Cluster to install the cert-manager.

Login to the VKS workload cluster using the VCF CLI from the Admin machine. The `kubectl-vsphere` plugin is deprecated in vSphere 9.1.0; use `vcf context` instead.

```bash
## Create a VCF CLI context for the Supervisor (if not already created in 5b)
vcf context create <context-name> --endpoint <SupervisorAPIEndpoint> --username <sso_username> --type k8s --insecure-skip-tls-verify

## Switch the active context to the target VKS workload cluster
vcf context use <context-name>:<vsphere-namespace>:<vks-cluster-name>

## Sample Commands
vcf context create supervisor1 --endpoint https://supervisor0.env1.lab.test --username administrator@vsphere.local --type k8s --insecure-skip-tls-verify
vcf context use supervisor1:ns01:workload-vsphere-vks1
```

The default package repository pointing to regional Harbor should be automatically configured after the regional Harbor is installed and configured successfully, check addon repository and list the available packages.
```bash
vcf package repository list -n tkg-system

## Sample Output
  NAME            SOURCE                                                                  STATUS
  vks-standard  (imgpkg) depot.kube-system.svc/vcf/vks-standard-packages/packages/standard/repo  Reconcile succeeded

vcf package available list -n tkg-system

## Sample Output
  NAME                                            DISPLAY-NAME
  cert-manager.tanzu.vmware.com                   cert-manager
  cluster-autoscaler.tanzu.vmware.com             autoscaler
  contour.tanzu.vmware.com                        contour
  external-csi-snapshot-webhook.tanzu.vmware.com  external-csi-snapshot-webhook
  external-dns.tanzu.vmware.com                   external-dns
  fluent-bit.tanzu.vmware.com                     fluent-bit
  fluxcd-helm-controller.tanzu.vmware.com         Flux Helm Controller
  fluxcd-kustomize-controller.tanzu.vmware.com    Flux Kustomize Controller
  fluxcd-source-controller.tanzu.vmware.com       Flux Source Controller
  grafana.tanzu.vmware.com                        grafana
  harbor.tanzu.vmware.com                         harbor
  multus-cni.tanzu.vmware.com                     multus-cni
  prometheus.tanzu.vmware.com                     prometheus
  vsphere-pv-csi-webhook.tanzu.vmware.com         vsphere-pv-csi-webhook
  whereabouts.tanzu.vmware.com                    whereabouts
```

Install cert-manager using the commands below.
```bash
## Command to list the versions of cert-manager available
vcf package available list cert-manager.tanzu.vmware.com -A

## Sample Output
  NAMESPACE   NAME                           VERSION                 RELEASED-AT
  tkg-system  cert-manager.tanzu.vmware.com  1.1.0+vmware.1-tkg.2    2020-11-24 18:00:00 +0000 UTC
  tkg-system  cert-manager.tanzu.vmware.com  1.1.0+vmware.2-tkg.1    2020-11-24 18:00:00 +0000 UTC
  tkg-system  cert-manager.tanzu.vmware.com  1.11.1+vmware.1-tkg.1   2023-01-11 12:00:00 +0000 UTC
  tkg-system  cert-manager.tanzu.vmware.com  1.12.10+vmware.2-tkg.2  2023-06-15 12:00:00 +0000 UTC
  tkg-system  cert-manager.tanzu.vmware.com  1.12.2+vmware.2-tkg.2   2023-06-15 12:00:00 +0000 UTC
  tkg-system  cert-manager.tanzu.vmware.com  1.5.3+vmware.2-tkg.1    2021-08-23 17:22:51 +0000 UTC
  tkg-system  cert-manager.tanzu.vmware.com  1.5.3+vmware.4-tkg.1    2021-08-23 17:22:51 +0000 UTC

## Command to install cert-manager
vcf package install cert-manager --package cert-manager.tanzu.vmware.com --namespace <namespaceName> --version <1.12.10+vmware.2-tkg.2>

## Verify the cert-manager pods
kubectl get pods -n cert-manager
NAME                                       READY   STATUS    RESTARTS   AGE
cert-manager-6778554f58-jhvb8              1/1     Running   0          54s
cert-manager-cainjector-575468965b-xrzf4   1/1     Running   0          54s
cert-manager-webhook-567f6945f-8m8d6       1/1     Running   0          54s
```

Note: In the sample commands provided, the cert-manager application will be deployed in the `namespaceName` namespace, with all required pods created in the `cert-manager` namespace. If a namespace named `cert-manager` already exists, the package deployment will use that existing namespace. If the package installation fails, label the `cert-manager` namespace with `pod-security.kubernetes.io/enforce=privileged` and delete all the ReplicaSets under the `cert-manager` namespace. This will prompt the deployment to recreate the ReplicaSets and the necessary pods.
