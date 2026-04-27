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

![image](/airgapped/depotreg-dataflow.png)

## Terminology
* **Bastion Host** A host (preferably a Linux VM) that is connected to the Internet or has access to download packages, binaries, and images from the Internet.
* **Admin Host** A host (preferably a Linux VM) within the air-gapped environment without internet access. The Admin host generally has network connectivity to all the hosts in the air-gapped environment. Files downloaded from the Internet to the Bastion host are transferred to the Admin Machine, and administrators can use it to interact with the platform.
* **VCF CLI** A plugin-based CLI that is used to interact with the Supervisor and VKS clusters
* **VKS add-ons** VKS add-ons enable administrators and users to add and manage standard services and add-ons on Kubernetes clusters using the VCF CLI or Carvel Custom Resources.

## Prerequisites
* This guide is for VCF / VVF 9.1.0 deployments, the distribution docker registry in VCF Software Depot can be used as the OCI compliant registry to host OCI images for Supervisor Services and VKS add-ons, and please follow this VKS deployment guide for Air-Gapped Environments.
* For VCF / VVF deployments based on prior-9.1.0 releases, an Enterprise OCI-compliant registry is required, and please follow this [document](/airgapped/air-gapped.md) for VKS deployment in Air-Gapped environments.

## Bill of Materials
The table below provides sample hostnames and versions used throughout the document for easy reference -

|Component|Version|Sample Hostname (where applicable)|
|---------|-------|----------------------------------|
|Bastion Host|Ubuntu 24.04.4|bastion.internet.lab.test|
|Admin Host (Air-gapped)|Ubuntu 24.04.4 (identical to the Bastion Host)|admin.env1.lab.test|
|vCenter|9.1.0|vcenter.env1.lab.test|
|ESXi|9.1.0|esxi[0..xxx].env1.lab.test|
|Supervisor|9.1.0|supervisor0.env1.lab.test|
|VKS cluster|1.34.2|workload-vsphere-vks1|
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

### 1a. vSphere Kubernetes Release OVA files
VSphere Kubernetes releases (VKR) provide the Kubernetes software distribution for VKS clusters. VMware distributes Kubernetes releases as virtual machine templates, which you synchronize with the platform using a vCenter Content Library. Download the latest Kubernetes release files from https://wp-content.broadcom.com/v2/latest/. The versions to be downloaded may depend on the workload requirements. It would be the best to download three or more of the latest versions. Follow [Step #11 from the official documentation](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vsphere-supervisor-services-and-standalone-components/9-1/managing-vsphere-kubernetes-service/administering-kubernetes-releases-for-tkg-service-clusters/create-a-local-content-library-for-air-gapped-cluster-provisioning.html) to download the relevant Kubernetes release files for each version. The VKR release that's released with VCF 9.1.0 is on version 1.34.2.

### 1b. VCF CLI and Plugins
While the VCF CLI and its plugins will be installed on the Bastion host (`bastion.internet.lab.test`), they must also be copied to the Admin Machine as part of the file transfer process. When this document was written, VCF CLI 9.1.0 is supported with vSphere and Supervisor 9.1.0. The steps below involve installing the VCF CLI on the Bastion host, which is necessary to download the VCF CLI plugins. Plugins can be downloaded and installed as required. In VCF online deployments the required VCF CLI binary can be downloaded from the home page of the vSphere Supervisor or from VCF Automation Tenant Portal, in internet restricted environments that this guide applies, follow [Installing the VCF CLI in Internet Restricted Environments](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/building-your-cloud-applications/getting-started-with-the-tools-for-building-applications/installing-and-using-vcf-cli-v9/installing-the-vcf-cli-in-internet-restricted-environments(2).html) to download VCF Consumption CLI and plugins, the steps are summarized as below.

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

## Install a single plugin (example: addon) or all plugins
vcf plugin install addon  --local-source ~/vcf-plugin-bundle/
vcf plugin install all --local-source ~/vcf-plugin-bundle/

## Verify the plugins are installed
vcf plugin list
```

### 1c. Binaries and YAML files required for Supervisor Services
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
When writing this document, the latest version of the ArgoCD Supervisor Service is “1.1.0”. Please refer to ​​the vSphere Supervisor Services page on Broadcom Support Portal to check for the updated versions. There will be 2 configuration files for version 1.1.0: `supervisor-service-argocd-legacy-1.1.0-25166333.yml` and `supervisor-service-argocd-depot-1.1.0-25166333.yml`. Download both files required for the ArgoCD Supervisor Service. Locate the value of the image from the `supervisor-service-argocd-legacy-1.1.0-25166333.yml` file as described above. The second configuration file `supervisor-service-argocd-depot-1.1.0-25166333.yml` (without `legacy` in the name) is the configuration file that should be used to register and install ArgoCD Supervisor Service on a Supervisor 9.1.0 cluster.

You can execute the following command from the Bastion host to download the image bundle as a tarball via the [oci_image_depot_migrator.py python script](/airgapped/scripts/oci_image_depot_migrator.py). Note the script requires executable imgpkg CLI and python 3 runtime installed on the Baston host.

```bash
## How to run oci_image_depot_imgrator.py migrator script.
./oci_image_depot_migrator.py --help

## Sample output
usage: oci_image_depot_migrator.py [-h] -s REPO [-t FQDN] [--work-dir WORK_DIR] ACTION

Migrate OCI images from projects.packages.broadcom.com to a target Software Depot.

Action is a required positional argument:
  download | upload | copy | map-target-repo

Common options:
  -s / --source-image-repo  REPO   always required
  -t / --target-depot-fqdn  FQDN   required for upload, copy, map-target-repo
  --work-dir DIR                   where tars and depot-ca.crt live (default: cwd)

positional arguments:
  ACTION                download | upload | copy | map-target-repo (see examples below).

options:
  -h, --help            show this help message and exit
  -s REPO, --source-image-repo REPO
                        Source bundle reference, e.g. projects.packages.broadcom.com/.../image:tag
  -t FQDN, --target-depot-fqdn FQDN
                        Target Software Depot FQDN. Required for upload, copy, and map-target-repo.
  --work-dir WORK_DIR   Directory for .tar, depot-ca.crt, and imgpkg cwd. Default: current working directory.

Actions:
  download          Download OCI tars to local --work-dir.
                    Uses imgpkg copy -b <REPO> --to-tar <derived>.tar.
                    Requires -s. -t is not required. The tar is kept on disk.

  upload            Upload an existing OCI tar to the target depot.
                    Expects a tar under --work-dir whose name matches the one
                    that download would produce for the same -s argument.
                    Requires -s and -t. Tar and depot CA are deleted on success.

  copy              Copy OCI images from source repo to target depot.
                    Does download + upload in one run and expects connectivity to both source and target.
                    Requires -s and -t. Temporary tar and depot CA are deleted on success.

  map-target-repo   Print the target Software Depot repo URL for a given OCI image (no tag).
                    Pure path conversion; does not run imgpkg to download or upload.
                    Requires -s and -t.

Tar naming:
  Basename is derived from the last segment of the source reference.
  ':' and unsafe characters are normalized.
  Example: .../argocd-service:v1.1.0_vmware.1 -> argocd-service-v1.1.0_vmware.1.tar

Examples:
  oci_image_depot_migrator.py copy \
      -s 'projects.packages.broadcom.com/.../argocd-service:v1.1.0_vmware.1' \
      -t 'fleet-10-144-79-70.vcfd.broadcom.net'

  oci_image_depot_migrator.py download \
      -s 'projects.packages.broadcom.com/.../image:tag'

  oci_image_depot_migrator.py upload \
      -s 'projects.packages.broadcom.com/.../image:tag' \
      -t 'fleet-10-144-79-70.vcfd.broadcom.net'

  oci_image_depot_migrator.py map-target-repo \
      -s 'projects.packages.broadcom.com/.../image:tag' \
      -t 'fleet-10-144-79-70.vcfd.broadcom.net'

## Download ArgoCD Supervisor Service Binaries
./oci_image_depot_migrator.py download -s projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service:v1.1.0_vmware.1

## Sample output
oci_image_depot_migrator — download operation:
  Download the image bundle from the source repository as a local tar file (imgpkg copy -b … --to-tar). The tar is kept after this command finishes.

  Source bundle:  projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service:v1.1.0_vmware.1
  Work directory: /root
  Output tar:       /root/argocd-service-v1.1.0_vmware.1.tar

+ imgpkg copy -b projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service:v1.1.0_vmware.1 --to-tar /root/argocd-service-v1.1.0_vmware.1.tar --cosign-signatures
copy | exporting 6 images...
copy | will export projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service@sha256:079b2362c304475fce764e74787e2dfca0fa55c5c794f44ed8026b9a2dd165f4
copy | will export projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service@sha256:237208855f6ad246c635fb5eaf73c46fe15d44c3ee08b5b111c0af4133008991
copy | will export projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service@sha256:51dd21339a030e329342738655c982d51244e8d24d1418772e3c7a995c4a684b
copy | will export projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service@sha256:6770cfdad0e4948e9e83ccdee222dff2077c38c5b4e83901ac2d7e7cc3545246
copy | will export projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service@sha256:95f0c93ffd3876de6a0b74db120a4c948d0797dc433ab1bdcc324151e505bab9
copy | will export projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service@sha256:bfdc9cfebc7fc599fc8398de398efab8348a53135fb1a9da6cfdd16674b7a453
copy | exported 6 images
copy | writing layers...
copy | done: file 'manifest.json' (123.918µs)
copy | done: file 'sha256-89732bc7504122601f40269fc9ddfb70982e633ea9caf641ae45736f2846b004.tar.gz' (41.37µs)
copy | done: file 'sha256-0e2673e247e340616ac68d3bfc9d439ee9825a2321c06c376606951d68afa651.tar.gz' (1.268268482s)
copy | done: file 'sha256-3dcb03f45f00fff2a746579a51d7a1c48f3359adeac4c8ee55df0f9e749419da.tar.gz' (1.857008991s)
copy | done: file 'sha256-eff1258cabc354e8da257df391e6fce4cbd9e624e5ab7a1fd4e554d2d7c0924a.tar.gz' (541.315937ms)
copy | done: file 'sha256-8dd14c08c00bced3376ffb0cef8cb9364f41d00c3a1e26f8e8eba9dca0e82bdf.tar.gz' (2.139829259s)
copy | done: file 'sha256-e607b5afc2fa8c30850a7082dfcc6ca7a402834f4ad5d46399a13b9b85831fc2.tar.gz' (2.190791516s)
copy | done: file 'sha256-64bdbeb13ccb1e6d041927bec596e9485057c7d24bf00adeb69a683a87ff9da1.tar.gz' (545.350836ms)
copy | done: file 'sha256-88cf5c94a9d5c510ee08aef192e860502aea9abd2a559fa0136344cff1069d0e.tar.gz' (2.908892839s)
copy | done: file 'sha256-ffd20d454278823aa6dba732bd23f106319b1ce049ba31878cc3537ac02a022d.tar.gz' (447.531237ms)
copy | done: file 'sha256-24534aa455a803ae7325c9685c8e2f9485e40df8f84e9fa7518c5bfd75cb383d.tar.gz' (277.954606ms)
copy | done: file 'sha256-10aa01ab563021d2fa06e40a349e32fe17389fa8ecaf972e28b62c46e148fe45.tar.gz' (46.114054ms)
copy | done: file 'sha256-fbe23a1ed6d25711bad1553cabd6ccdb936f9327d91de460a68d45f1244e2abb.tar.gz' (132.365849ms)
copy | done: file 'sha256-70a675fdcbb066ad154692632dbd83ae786742a78f1e580c29163606055bcc0a.tar.gz' (686.94861ms)
copy | done: file 'sha256-229920928a00afd79a934178bb8c219d28b8bad61136d073d2d8e562fd7e360d.tar.gz' (120.601145ms)
copy | done: file 'sha256-ff3b6abf48df124ef6cd97ab1dd49a7321b958670214b23a01e0fd886456acaf.tar.gz' (5.100654ms)
copy | done: file 'sha256-0df5a351b85a9f0c0015eafecad3d5f6db0f68740134e96c87edc6dfe876220c.tar.gz' (18.868868ms)
copy | done: file 'sha256-c496065031ff611cda2c1b8860f04e8f967ff4c775780f28a28e50ee0a7d4441.tar.gz' (126.566043ms)
copy | done: file 'sha256-04e6897e12163e5f64eeeb09b6e9d456227dd0acb7e406f6022374d27519f032.tar.gz' (5.150078ms)
copy | done: file 'sha256-e7878035ed7caf7ae686119723f5d9ba32cf79f3624bfaa9737c6766349e9863.tar.gz' (99.18484ms)
copy | done: file 'sha256-bd708305c31669d27de98616bb363a2b1b1dd43ca96f5f7e7c5625d562c662a9.tar.gz' (122.526339ms)
copy | done: file 'sha256-156e2c2831cddb9b247bf58bb2529c96b83d064b6a94b737ac6b2783337633a9.tar.gz' (30.620344ms)
copy | done: file 'sha256-995c015c737e5d993c36e56294f1d2fcce682667db9bc8c299daadc641363c95.tar.gz' (90.747µs)
copy | done: file 'sha256-e9be946ab6ec0a377f10363b2aedd6e0f7775b27493ff242e5cf736f5072d5ec.tar.gz' (146.06µs)
copy | done: file 'sha256-7b5c0d30e77a40950ca0709bfb336b08101cacaf3b892ebe834706f1def2dd89.tar.gz' (38.688218ms)
copy | done: file 'sha256-88d8b6a90cade74273e793fdd4cab5371db24ee09f550acfb4078f81b9882503.tar.gz' (114.297µs)
copy | done: file 'sha256-b68d90d759408486ca26fb81227e263bf7b8b0d1a45c3c048259e76a6bcba822.tar.gz' (45.568µs)
copy | done: file 'sha256-e6e9a2df088e0a9c1ea32351db9a2b7961ac42feb28ba1892c1016da34236497.tar.gz' (38.772µs)
copy | done: file 'sha256-12b978624d737a557a5d02491823d4fbbced67c957b9e982e7245750628b7b83.tar.gz' (471.551µs)
copy | done: file 'sha256-5ccfff97b99f2d3add2430aebfa2d5d42c762b0d2b9c2bc9e4f488dfb09e55fc.tar.gz' (260.831µs)

Succeeded
/root/argocd-service-v1.1.0_vmware.1.tar
Done.
```
A bundle tar file named as `argocd-service-v1.1.0_vmware.1.tar` will be downloaded to the same directory as the python script by default, perform similar steps for other Supervisor Services that must be installed in the air-gapped environment. The configuration YAML files of Supervisor Services can be discovered on [Broadcom Support Portal](https://support.broadcom.com) by searching for `supervisor services` and clicking on `vSphere Supervisor Services` after login and navigating to `My Downloads`. For VKS service, the latest version 3.6.3 is released at the time of the guide writing, and this version should be downloaded for VKS upgrade later in this guide.

The table below provides the sample list of Supervisor Services that can be downloaded from Broadcom Support Portal and installed on the platform -

|Service Name|Type|Version|
|------------|----|-------|
|VKS Service|Core|3.6.3|
|ArgoCD|Standard|1.1.0|
|CA Cluster Issuer|Standard|0.0.2|
|Consumption Interface|Standard|9.1.0|
|Contour|Standard|1.33.1|
|ExternalDNS|Standard|0.18.0|
|Harbor|Standard|2.14.2|
|Metrics Aggregator|Standard|0.1.0|
|Supervisor Management Proxy|Standard|0.4.1|

### 1d. VKS Add-ons
VKS add-ons enable administrators and users to use the VCF CLI or Carvel Custom Resources to add and manage standard services and add-ons on Kubernetes clusters. With VKS add-ons, you can deploy various add-ons to VKS Clusters, such as cert-manager, Contour, Prometheus, Grafana, and more. Download the relevant the VKS add-on bundle using the following command via the [oci_image_depot_migrator.py](scripts/oci_image_depot_migrator.py) python script, which will download the OCI images as tar
file vks-standard-packages-3.6.0-20260211.tar into the local script directory -

```bash
./oci_image_depot_migrator.py download -s projects.packages.broadcom.com/vsphere/supervisor/vks-standard-packages/3.6.0-20260211/vks-standard-packages:3.6.0-20260211
```

### Summary
The following files, binaries, and packages have been successfully downloaded in this section and **must be transferred to the Admin host**.
* Kubernetes Release OVA files.
* VCF CLI tar (e.g. `VCF-Consumption-CLI-Linux_AMD64-9.1.0.tar.gz`).
* VCF CLI plugin bundle tar (e.g. `VCF-Consumption-CLI-PluginBundle-Linux_AMD64-9.1.0.tar.gz`).
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
`kubectl` is the command-line tool used to interact with Kubernetes clusters. It allows users to manage and inspect resources within a Kubernetes environment. `kubectl-vsphere` is a VMware-specific plugin for `kubectl` that enables administrators and developers to interact with the Supervisor and manage VKS clusters running on vSphere. It is deprecated and replaced by VCF CLI since vSphere 9.1.0, and not needed here.

You can download and install the `kubectl` plugin to your Admin host machine by accessing the Supervisor Cluster Kube-API server endpoint UI or using the command below.

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

## Sample Command to login and use context of namespace ns01 for VKS cluster deployment later.
vcf context create supervisor1 --endpoint https://supervisor0.env1.lab.test --username administrator@vsphere.local --type k8s --insecure-skip-tls-verify
vcf context use supervisor1:ns01
```

### 5c. Enable OCI image upload on Software Depot

The Software Depot in VCF Fleet runs a distribution docker registry, which doesn't allow OCI image push by default. Follow the following steps to enable OCI image upload on Fleet Software Depot.

#### 5c1. Create a config JSON file as config.json with the following config
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
```

#### 5c2. Apply the config.json to Software Depot via API by following commands below after login to VCF Ops
```
# Discover the VCF services runtime FQDN by login to VCF Ops and navigate to Build --> Lifecycle --> VCF management --> Components, and export as env variable.
export PLATFORM_HOST=https://<VCF_SERVICES_RUNTIME_FQDN>;

# Export Ops admin and password as env variable.
export ADMIN_PASSWORD='<OPS_ADMIN_PASSWORD>';
export ADMIN_USERNAME='<OPS_ADMIN_USERNAME>';

# Get access token via the Ops admin login.
export TOKEN=`curl -k -XPOST  ${PLATFORM_HOST}/api/v1/identity/token \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data grant_type=password \
  --data "username=${ADMIN_USERNAME}" \
  --data "password=${ADMIN_PASSWORD}" | jq -r '.access_token'`;

echo "token is $TOKEN";

# Discover the component ID of the `vcf-fleet-depot` component.
export VCF_FLEET_DEPOT_COMPONENT_ID=$(curl -H"Authorization: Bearer ${TOKEN}" -k ${PLATFORM_HOST}/api/v1/components | jq -r '.components[] | select(.name == "vcf-fleet-depot") | .id')

# Apply the config to the Software Depot, this will return a task ID.
export TASK_ID=$(curl -k -XPOST -H"Authorization: Bearer ${TOKEN}" ${PLATFORM_HOST}/api/v1/components/${VCF_FLEET_DEPOT_COMPONENT_ID}?action=apply -d @./config.json | jq -r '.id')

# monitor the task until the task status returns succeeded.
until [ "$(curl -ks -H "Authorization: Bearer ${TOKEN}" ${PLATFORM_HOST}/api/v1/tasks/${TASK_ID} | jq -r '.status')" == "Succeeded" ]; do echo "Still waiting..."; sleep 5; done
```

## 6. Ensure regional Harbor is configured on Supervisor.

In a VCF deployment with VCF Automation installed, follow this [documentation](https://author-techdocs2-prod.adobecqms.net/content/output/sites/docworks-preview/installing-and-configuring-supervisor-services-ditamap/using-harbor-as-vcf-service/using-harbor-as-a-vcf-service.html?wcmmode=disabled) to install and configure regional Harbor as a VCF service on a Supervisor in a VCF region. If the VCF deployment doesn't have VCF Automation or it's a VVF deployment, follow this [documentation](https://author-techdocs2-prod.adobecqms.net/content/output/sites/docworks-preview/instaiing-and-configuring-supervisor-services-ditamap/using-harbor-as-vcf-service/installing-and-configuring-harbor-and-contour/deploy-harbor-supervisor-service-in-vvf-without-vcfa.html?wcmmode=disabled) to manually install Harbor Supervisor Service on the Supervisor.

## 7. Upload Packages to the Software Depot

### 7a. Upload Supervisor Services to the distributon registry on Software Depot
All the Supervisor Services image bundle binaries downloaded in Step 1d must be uploaded to the Software Depot by using the provided [oci_image_depot_migrator.py](scripts/oci_image_depot_migrator.py) script. The same Software Depot FQDN is required for the upload.

```bash
./oci_image_depot_migrator.py upload -s <supervisor-service-package-image-on-projects.packages.broadcom.com> -t <software-depot-fqdn>

## Sample Command for ArgoCD Supervisor Service with example Software Depot FQDN as the target: fleet-10-144-79-70.vcfd.broadcom.net
./oci_image_depot_migrator.py upload -s projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service:v1.1.0_vmware.1 -t fleet-10-144-79-70.vcfd.broadcom.net

## Sample Output
oci_image_depot_migrator — upload operation:
  1) Use the existing local tar (must match the name derived from --source-image-repo).
  2) Map the source repo path to the target depot repo URL (see below).
  3) Fetch the target depot TLS certificate, then upload the tar with imgpkg.
  4) Remove the temporary tar and certificate files after a successful upload.

  Source bundle (for path mapping & tar name): projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service:v1.1.0_vmware.1
  Target depot FQDN: fleet-10-162-210-47.vcfd.broadcom.net
  Target repo URL:   fleet-10-162-210-47.vcfd.broadcom.net/vcf-service-argocd/ga/1.1.0/argocd-service
  Work directory:    /root
  Tar file:          /root/argocd-service-v1.1.0_vmware.1.tar
  Temporary CA file: /root/depot-ca.crt

Step 2: Source repo path maps to the target repo URL above (used as --to-repo).
Step 3: Fetching target depot TLS certificate…
+ openssl s_client -connect fleet-10-162-210-47.vcfd.broadcom.net:443 -showcerts | awk '/BEGIN CERTIFICATE/,/END CERTIFICATE/' > /root/depot-ca.crt
+ imgpkg copy --tar /root/argocd-service-v1.1.0_vmware.1.tar --to-repo fleet-10-162-210-47.vcfd.broadcom.net/vcf-service-argocd/ga/1.1.0/argocd-service --cosign-signatures --registry-ca-cert-path /root/depot-ca.crt
copy | importing 6 images...
....
```

In case the admin host is in DMZ and has connectivity to projects.packages.broadcom.com, the Supervisor service images can be copied from projects.packages.broadcom.com directly to Software Depot.

```bash
./oci_image_depot_migrator.py copy -s <supervisor-service-package-image-on-projects.packages.broadcom.com> -t <software-depot-fqdn>

## Sample Command for ArgoCD Supervisor Service with example Software Depot FQDN as the target: fleet-10-144-79-70.vcfd.broadcom.net
./oci_image_depot_migrator.py copy -s projects.packages.broadcom.com/vsphere/supervisor/argocd-service/1.1.0/argocd-service:v1.1.0_vmware.1 -t fleet-10-144-79-70.vcfd.broadcom.net
```

### 7b. Upload VKS Add-on Packages to the distributon registry on Software Depot
The VKS Add-on package bundle, downloaded in Step 1c, must be uploaded to the distribution docker registry on Software Depot using the provided [oci_image_depot_migrator.py](scripts/oci_image_depot_migrator.py) python script. The upload command requires the Software Depot FQDN, which can be discovered by login to VCF OPS and navigate to Build --> Lifecycle --> VCF management --> Components page and identify the Fleet components FQDN.

```bash
./oci_image_depot_migrator.py upload -s projects.packages.broadcom.com/vsphere/supervisor/vks-standard-packages/3.6.0-20260211/vks-standard-packages:3.6.0-20260211 -t <software-depot-fqdn>

## Sample Command with example Software Depot FQDN as the target: fleet-10-144-79-70.vcfd.broadcom.net
./oci_image_depot_migrator.py upload -s projects.packages.broadcom.com/vsphere/supervisor/vks-standard-packages/3.6.0-20260211/vks-standard-packages:3.6.0-20260211 -t fleet-10-144-79-70.vcfd.broadcom.net
```

In case the admin host is in DMZ and has connectivity to projects.packages.broadcom.com, the VKS Add-on packages can be copied from projects.packages.broadcom.com directly to Software Depot by using below command.

```bash
./oci_image_depot_migrator.py copy -s projects.packages.broadcom.com/vsphere/supervisor/vks-standard-packages/3.6.0-20260211/vks-standard-packages:3.6.0-20260211 -t  <software-depot-fqdn>

## Sample Command with example Software Depot FQDN as the target: fleet-10-144-79-70.vcfd.broadcom.net
./oci_image_depot_migrator.py copy -s projects.packages.broadcom.com/vsphere/supervisor/vks-standard-packages/3.6.0-20260211/vks-standard-packages:3.6.0-20260211 -t fleet-10-144-79-70.vcfd.broadcom.net
```

## 8. Deploy VKS Cluster(s)

### 8a. Update vSphere Kubernetes Service (VKS) to the latest version
When writing the documentation, the latest VKS release was 3.6.3. Since each VKS release introduces additional features and fixes, we must apply these updates to make the new features and fixes available. This document will update the core VKS from 3.6.1 to 3.6.3, this requires VKS 3.6.3 binary tar and configuration yaml files are already downloaded to the Baston host and uploaded to the distribution docker registry on Software Depot by the steps above. Follow the relevant sections in the [documentation](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vsphere-supervisor-services-and-standalone-components/latest/managing-vsphere-kubernetes-service/installing-and-upgrading-the-tkg-service/upgrade-the-tkg-service-version.html) to complete the upgrade.

### 8b. Deploy a Workload Cluster
Deploying a VKS Cluster (using an Ubuntu image). Review each section at a minimum and adjust the necessary fields as needed. Refer to the [“Workflow for Provisioning VKS Clusters Using kubectl” documentation](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vsphere-supervisor-services-and-standalone-components/9-1/managing-vsphere-kuberenetes-service-clusters-and-workloads/provisioning-tkg-service-clusters/workflow-for-provisioning-tkg-clusters-using-kubectl.html) for more details
and refer to the [cluster config yaml document](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vsphere-supervisor-services-and-standalone-components/9-1/managing-vsphere-kuberenetes-service-clusters-and-workloads/provisioning-tkg-service-clusters/using-the-cluster-v1beta1-api/using-the-versioned-clusterclass/v1beta1-example-default-cluster.html#GUID-2d377bf9-e51d-4e7d-b7dc-f7c892ad36ee-en_id-3e284ef2-486b-4a0c-9736-e292d2f83e36) for examples.

While `v1beta1` or `v1beta2` provides numerous configuration options, the following additional variables may be added for a default `podSecurityStandard`.
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
...
```

```bash
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
vcf context create supervisor1 --endpoint https://supervisor0.env1.lab.test --username administrator@vsphere.local --workload-cluster-namespace ns01 --workload-cluster-name workload-vsphere-vks1 --type k8s --insecure-skip-tls-verify
vcf context use supervisor1:workload-vsphere-vks1
```

The default package repository pointing to regional Harbor should be automatically configured and installed after the regional Harbor is installed and configured successfully, check addon repository and list the available packages.
```bash
vcf addon repository list

## Sample Output
  NAME                                           NAMESPACE                 SOURCE
  default-addonrepository-3.6.0                  vmware-system-vks-public  projects.packages.broadcom.com/vsphere/supervisor/vks-standard-packages/3.6.0-20260211/vks-standard-packages:3.6.0-20260211
  default-addonrepository-3.6.0-regional-harbor  vmware-system-vks-public  depot.kube-system.svc/vcf/vks-standard-packages/ga/3.6.0-20260211/vks-standard-packages:3.6.0-20260211

vcf addon repository-install list

## Sample Output
  NAME                        NAMESPACE                 ADDONREPOSITORY                                READY
  default-addon-repo-install  vmware-system-vks-public  default-addonrepository-3.6.0-regional-harbor  True

vcf addon available list

## Sample Output
  NAMESPACE                 ADDONNAME                    DESCRIPTION
  vmware-system-vks-public  ako                          Integrates VMware NSX Advanced Load Balancer with Kubernetes for L4-L7 services.
  vmware-system-vks-public  cert-manager                 Certificate management
  vmware-system-vks-public  contour                      An ingress controller
  vmware-system-vks-public  external-dns                 This package provides DNS synchronization functionality.
  vmware-system-vks-public  fluent-bit                   Fluent Bit is a fast Log Processor and Forwarder
  vmware-system-vks-public  harbor                       OCI Registry
  vmware-system-vks-public  istio                        networking service mesh solution for containers
  vmware-system-vks-public  prometheus                   A time series database for your metrics
  vmware-system-vks-public  sriov-network-device-plugin  The SR-IOV Network Device Plugin is Kubernetes device plugin for discovering and
                                                         advertising SR-IOV virtual functions (VFs) available on a Kubernetes host
  vmware-system-vks-public  telegraf                     collect and report metrics
  vmware-system-vks-public  vault-injector               Vault Agent Injector for Secret Store Service
  vmware-system-vks-public  velero                       Velero is an open source tool to safely backup and restore, perform disaster
                                                         recovery, and migrate Kubernetes cluster resources and persistent volumes.
  vmware-system-vks-public  vsphere-pv-csi-webhook       vSphere paravirtual CSI provider webhook
  vmware-system-vks-public  windows-gmsa-webhook         Windows Group Managed Service Accounts (GMSA) Kubernetes Webhook


vcf addon available list cert-manager

## Sample Output
  NAMESPACE                 ADDONNAME     VERSION                ADDON-RELEASE-NAME                                        PACKAGE
  vmware-system-vks-public  cert-manager  1.18.2+vmware.2-vks.2  cert-manager.kubernetes.vmware.com.1.18.2-vmware.2-vks.2  cert-manager.kubernetes.vmware.com/1.18.2+vmware.2-vks.2
  vmware-system-vks-public  cert-manager  1.18.3+vmware.1-vks.1  cert-manager.kubernetes.vmware.com.1.18.3-vmware.1-vks.1  cert-manager.kubernetes.vmware.com/1.18.3+vmware.1-vks.1
  vmware-system-vks-public  cert-manager  1.19.1+vmware.1-vks.1  cert-manager.kubernetes.vmware.com.1.19.1-vmware.1-vks.1  cert-manager.kubernetes.vmware.com/1.19.1+vmware.1-vks.1
  vmware-system-vks-public  cert-manager  1.19.2+vmware.1-vks.1  cert-manager.kubernetes.vmware.com.1.19.2-vmware.1-vks.1  cert-manager.kubernetes.vmware.com/1.19.2+vmware.1-vks.1
```

Install cert-manager using the commands below.
```bash
## Command to list the versions of cert-manager available
vcf addon available list cert-manager

## Sample Output
  NAMESPACE                 ADDONNAME     VERSION                ADDON-RELEASE-NAME                                        PACKAGE
  vmware-system-vks-public  cert-manager  1.18.2+vmware.2-vks.2  cert-manager.kubernetes.vmware.com.1.18.2-vmware.2-vks.2  cert-manager.kubernetes.vmware.com/1.18.2+vmware.2-vks.2
  vmware-system-vks-public  cert-manager  1.18.3+vmware.1-vks.1  cert-manager.kubernetes.vmware.com.1.18.3-vmware.1-vks.1  cert-manager.kubernetes.vmware.com/1.18.3+vmware.1-vks.1
  vmware-system-vks-public  cert-manager  1.19.1+vmware.1-vks.1  cert-manager.kubernetes.vmware.com.1.19.1-vmware.1-vks.1  cert-manager.kubernetes.vmware.com/1.19.1+vmware.1-vks.1
  vmware-system-vks-public  cert-manager  1.19.2+vmware.1-vks.1  cert-manager.kubernetes.vmware.com.1.19.2-vmware.1-vks.1  cert-manager.kubernetes.vmware.com/1.19.2+vmware.1-vks.1

## Command to install cert-manager
vcf addon install create cert-manager --addon-release-name <cert-manager.kubernetes.vmware.com.1.19.1-vmware.1-vks.1> --namespace <namespaceName> --cluster-name <clusterName>

## Sample command
vcf addon install create cert-manager --addon-release-name cert-manager.kubernetes.vmware.com.1.19.1-vmware.1-vks.1 --namespace ns01 --cluster-name vks-cluster
# Sample output
Installing addon 'cert-manager' for cluster 'vks-cluster'. Are you sure? [y/N]: y
Addon 'cert-manager' is being installed in the cluster vks-cluster

## Verify the cert-manager pods
kubectl get pods -n cert-manager

## Sample Output
NAME                                       READY   STATUS    RESTARTS   AGE
cert-manager-7c7fcc8598-zcwc6              1/1     Running   0          26s
cert-manager-cainjector-68c447777d-b92xj   1/1     Running   0          26s
cert-manager-webhook-7b9544c879-t4pg8      1/1     Running   0          26s
```

Note: In the sample commands provided, the cert-manager application will be deployed in the `namespaceName` namespace, with all required pods created in the `cert-manager` namespace. If a namespace named `cert-manager` already exists, the package deployment will use that existing namespace. If the package installation fails, label the `cert-manager` namespace with `pod-security.kubernetes.io/enforce=privileged` and delete all the ReplicaSets under the `cert-manager` namespace. This will prompt the deployment to recreate the ReplicaSets and the necessary pods.
