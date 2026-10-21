Dataverse Metasyn
=================

This is a follow-up of the work in the [dataverse_external_tools](../dataverse_external_tools/README.md) folder. 
The goal is to connect the 'External Tools' page from Dataverse to the Metasyn API (web service). Using that service we can generate GMF JSON (model) file from a tabular file. The GMF can then be download. Alternatively, when initiated from such a GMF file, we can generate synthetic data and download it. 
In contrast with the previous example, it does not provide any 'AUX' file retrieval and storage. This is technically possible, but for this example/demo it was decided to put the emphasis on the synthetic data generation. 

Note that there is also Ansible code that was used to deploy the 'external tools' on the SSH test server. This can be found in the `ansible` folder, check the [README.md](ansible/README.md). 


## Setup

Similar to that previous setup we first need to have a running Dataverse (SSH) and have it configured correctly to use the 'tools' html file. 

1. Start the SSH datastation 'dev' box.
```
start-preprovisioned-box.py -s dev_ssh dev_vocabs
```
Note the `-s`, it will start a fresh box, can be omitted later on. 

2. Copy the files
```
cp ~/git/synthetic_metadata_interop/dataverse_metasyn/* ~/git/dans-core-systems/shared/
```
And on the vagrant box (`vagrant ssh dev_ssh`)
```
sudo cp /vagrant/shared/synth-file-tool.html /var/www/html/custom/
```

3. Configure the tools in Dataverse
In vagrant
For the tabular files
```
curl -X POST -H 'Content-type: application/json' http://localhost:8080/api/admin/externalTools --upload-file /vagrant/shared/synthFileTool.json
```
For the JSON (GMF) files
```
curl -X POST -H 'Content-type: application/json' http://localhost:8080/api/admin/externalTools --upload-file /vagrant/shared/synthFileToolGmf.json
```

__NOTE__: You can delete 'wrong' configs with `curl -X DELETE http://localhost:8080/api/admin/externalTools/<id>`, where `<id>` is the number for the config that you can discover with `curl http://localhost:8080/api/admin/externalTools`. 

4. Start the API
Read that documentation, it will explain how to get it running. 
[metasyn_api](../metasyn_api/README.md)


## Demo usage

With Dataverse and the Metasyn API running (see Setup), the tool can be used on both tabular files and GMF JSON files. A tabular file is used to create a GMF model file; a GMF file is used to create synthetic data. Both results can be downloaded. 

### 1. Select the tool

Open the 'Access File' menu of a file in Dataverse and choose 'Synthetic Replicant File Tool' under 'Explore Options'.

![Selecting the Synthetic Replicant File Tool from the Access File menu of a tabular file](Screenshot-select-tool-from-tabfile.png)

### 2. Generate a GMF model from a tabular file

The tool shows the selected file and detects that it is tabular. Press 'Fit model' to send it to the Metasyn API.

![Tool page for a tabular file with the Fit model button](Screenshot-tool-start-generate-gmf.png)

The result is a table of the columns with their type and fitted distribution, the GMF JSON in a scrollable block, and a button to download `model.json`.

![Generated GMF model with column table, GMF JSON and download button](Screenshot-tool-generated-gmf.png)

When the Dataset is in 'Draft' mode, there will also appear an 'Upload to Dataverse' button which allows to add the GMF file to your dataset. The name will be similar, but ends in `_gmf.json`, to indicate it is the GMF of that file. 


### 3. Generate synthetic data from a GMF file

Start the tool the same way, but from a GMF (JSON) file. The tool detects the GMF file and offers to generate synthetic data; choose the number of rows and press 'Generate synthetic data'.

![Tool page for a GMF JSON file with the number of rows and Generate synthetic data button](Screenshot-tool-start-generating-data.png)

The result shows the input GMF, a preview of the generated rows and a button to download `synthetic.csv`.

![Generated synthetic data preview with download button](Screenshot-tool-generated-data.png)


## Open issues

- After generating the GMF it would be nice to allow to generate Synthetic data with it, just like that API,s UI page has. But now it does not, instead you would need to store it and then initiate another 'Explore; Synthetic Replicant File Tool' from the GMF file's 'Access' dropdown. 

- If you generate synthetic data, you now can only download it, but it would be nice to also allow storing it in the dataset. 

- This for/UI does show the input data on the 'results' section when you issue the generate action. This is a bit strange, users expect this to happen when the input is available and thus before issuing the generate action. 

- There are many more UX inconveniences, but this is a demo, showing what integration from Dataverse with the 'metasyn' tool would be possible. 
