Dataverse External Tools
========================

Investigate how we can use the 'External Tools' functionality of Dataverse to provide the synthetic data generation for a (tabular) file. 

Documentation on this functionality can be found here: 
https://guides.dataverse.org/en/latest/installation/external-tools.html
and more specific
https://guides.dataverse.org/en/latest/api/external-tools.html


## Setup

As a starting point we will have a look at the file previewers because those are able to read the file data even if it is restricted but the user is allowed to see it. 

These previewers are implemented as html pages with Javascript doing the information retrieval and processing. 

For simplicity this experiment is using a single page with the script code embedded: `synth-file-tool.html`. In order for Dataverse to provide this it needs to be configured. The configuration JSON is in the `synthFileTool.json`. As a development environment we use the code from the `dans-core-systems` Github repository with the `dev_ssh` vagrant box running a Dataverse development version of the SSH Datastation. 

To enable the tool we need to do two things: 

1. Copy the html file in to `/var/www/html/custom/` directory on the `dev_ssh` vagrant box. This can be done via the shared directory in the `dans-core-systems` root directory. As an example I will show the copy commands that I use: 
   ```
   cp ~/git/synthetic_metadata_interop/dataverse_external_tools/* ~/git/dans-core-systems/shared/
   ```
   And on the vagrant box
   ```
   sudo cp /vagrant/shared/synth-file-tool.html /var/www/html/custom/
   ```

2. Configure Dataverse to use the tool. Copy the JSON file also into that shared folder and run the following curl on the `dev_ssh` box. 
   ```
   curl -X POST -H 'Content-type: application/json' http://localhost:8080/api/admin/externalTools --upload-file /vagrant/shared/synthFileTool.json
   ```

Notice that the configuration has the line; `  "toolUrl": "https://dev.ssh.datastations.nl/custom/synth-file-tool.html",`, which would need to be changed if you move the html file to another location. 

For testing we need at least one Dataset with at least one tabular file. This is specified by the following line in the configuration JSON: `"contentType": "text/tab-separated-values",`. 
The `test.csv` file is an very simple and small file that can be used for that. Once uploaded Dataverse will generate the 'tab' file for it.  

With a working setup and a datset that has this tes.csv uploaded you would get the folowing...
when selecting the 'Access File' dropdown for that tab file. 
Just below the 'Explore Options' line it should have the 'Synthetic Replicant File Tool' option. 
If you select that one the browser will load that html page. 

![Screenshot showing the 'Synthetic Replicant File Tool' option in the Dataverse file access dropdown.](Screenshot-FileAccessExploreOptions.png)



## Tool functionality

### Getting the data

As a starting point for the script code I inspected (and copied from) the code for the previewers. The first step is done with the `retriever.js` script code, which can be found here: 
`https://github.com/gdcc/dataverse-previewers/blob/develop/previewers/v1.5/js/retriever.js`. 
Besides skipping some code that's of less importance for this experiment (like i18n); I also do not use jQuery; so no `$.ajax`, but using `fetch` instead. 

The previewer code was a working example of how toi retrieve the file data, which normally will be 'viewed'. Getting the data is needed in order to generate the 'schema' that is in turn needed for the synthetic data generation. 

The following screenshot show the output of the (fake) tool for the test.tab (csv originally) file: 
![Screenshot showing parameters and retrieved file data](Screenshot-FileRetrieveAndDisplayData.png).


### Storing related data

The idea would be to store the MetaSynth schema file (Generative Metadata Format), which would allow for the synthetic data generation without having to look at the original data again. There is a mechanism in Dataverse for storing files related to archived files called; auxiliary files. 
This is probably also what is being used by the 'OpenDP' tool, but I do not know the details. You could also use this aux files mechanism to store the synthetic data, but I am not going to test that. 

While there is no connection to the synthetic data generation tool yet, which should ideally be a web service, we can use some fake content instead. 

Documentation on the auxiliary file functionality can be found here: 
https://guides.dataverse.org/en/latest/developers/aux-file-support.html

Note that the guide shows how you can manipulate (create, list, delete) these aux files from the commandline with `curl` while experimenting. 

#### Aux file and external tools limitations

During experimenting a limitation was discovered for the aux file creation; we do not get signed URLs when the file is publicly available, making the POST request fail. 
The workaround is to make the Dataset into Draft (for instance by restricting it) and or make the file restricted.  

Maybe it is better to create an issue for this on the Github Repo, and at least have this limitation explicitly mentioned in the documentation of the external tools.  

#### Preliminary evaluation

The aux files mechanism can be used in conjunction with the external tools mechanism. 
It is possible to extract the data, do some processing and store a result in an aux file. 


### Appendix

Screenshots of the web page. 

The first time there will be no aux file yet, and it will create one. 
![First time](Screenshot-NeededToCreateAuxFile.png)

The second (or later) times it will show the aux file content. 
![Next time](Screenshot-AuxFileAlreadyCreated.png)
