# Synthetic Data Project - Findings 
Author: Alessandra Polimeno \
Research: Paul Boon & Alessandra Polimeno \
Date: 08/05/2026

## Task description 
This report summarizes the work done in Project Task 1: Synthetic Data Tools. This task investigates what is needed for tools that generate synthetic data to be integrated into the [Data Station SSH](https://ssh.datastations.nl/). We focused on the [Metasyn](https://github.com/sodascience/metasyn) tool, which provides a way to generate synthetic data of tabular datasets with Python while ensuring a high privacy protection of the original data. 

The most common use case of synthetic data is concerned with transforming a restricted data file into a synthetic version that can be openly shared and used by others for, among other things, educational purposes, as test data, to check the reproducibility of code, or to start developing a program while access to the full data is pending. The scenario we envision allows a data owner to create synthetic datasets from their original dataset within the depositing page through the Dataverse External Tools module. The synthetic version can then be published openly at DANS while the original dataset may be restricted or unpublished. We do not cover the scenario in which a user would want to create or request a synthetic dataset of an existing restricted dataset. 

The task was carried out in two phases. The first phase focuses on the question whether the Dataverse API provides enough metadata to generate a synthetic version with Metasyn. The second phase takes these findings and proposes a solution that allows depositors to create a synthetic dataset without the need to adapt or create new Dataverse functionalities. 


## Phase 1: Metasyn and Dataverse


### Metasyn description 
[Metasyn](https://github.com/sodascience/metasyn?tab=readme-ov-file) is an open sorce, privacy-friendly generator for synthetic tabular data. The tool fits a model to an existing dataset, capturing the datatypes and distributions of individual variables. The user can save the model and use it to generate synthetic data that looks like the original datafile. The statistical information is strictly limited so that it avoids privacy leaks and capturing of relations between variables.

The model that Metasyn creates can be saved to a standard called [Generative Metadata Format](https://github.com/sodascience/generative_metadata_format), which stores statistical metadata in JSON. A GMF is modular and extensible, allowing for the addition of more distributions and privacy enhancing mechanisms by the user. With the GMF, the user can create synthetic versions of the data without needing access to the original dataset. 

Users can create synthetic data with Metasyn with a Python script or notebook. Both the GMF and synthetic data file can be saved for reuse. 

To create a synthetic dataset with Metasyn, two components are required: the original dataset and the corresponding schema that at least specifies the variable names and their data types.


### Dataverse ingest details
It should also be possible to generate synthetic data if the original dataset is not available, as long as there is enough schema information in the file metadata to create a GMF file. The Dataverse API allows for the extraction of file metadata, but it doest not provide enough information to populate a GMF. The missing information is mostly concerned with the distribution types of the data. See [this report](https://github.com/tdcc-synthetic-data/synthetic_metadata_interop/blob/main/research/dataverse_findings.md#summary-and-implications) for an overview of the missing information. 

We investigated the Dataverse Ingest Function to see if it could be extended to provide the necessary information during depositing. See [this report](https://github.com/tdcc-synthetic-data/synthetic_metadata_interop/blob/main/research/dataverse_ingest_details.md) for the full description of this process. We found that extending the ingest function is technically possible, but there are some issues that make it undesirable: 
- Calculating the distributions at ingest may take too much time to be acceptable for a depositor to wait for.  
- The code to calculate the distribution information would need to somehow be ported, as we cannot easily make changes to Dataverse. 
- Large files do not currently have an ingest configuration in the SSH Data Station. 

Due to these issues we decided it was not within scope of the project to follow the route of extending the Dataverse ingest function. The next section describes the alternative we propose instead. 


## Phase 2: Our solution - Dataverse External Tools and a Metasyn API 

This phase of the task explores how we can use the External Tools functionality within Dataverse to provide the generation of synthetic data of a tabular file. It also includes a prototype for a locally run Metasyn API that can be called as external tool. 


### DV External Tools 
The Dataverse [External Tools](https://guides.dataverse.org/en/latest/api/external-tools.html) functionality allows for the configuration of external tools that can be called from within Dataverse. It initiates a request to another service outside of Dataverse during depositing or editing a dataset, and allows for saving the output of the external tool to the dataset as an auxiliary file. See [this report](https://github.com/tdcc-synthetic-data/synthetic_metadata_interop/tree/main/dataverse_external_tools) for details on its setup and use. 
 
The External Tools functionality can, when properly configured, be used by navigating to the file you want to manipulate, clicking `Access File` on the download button of that file, and choosing a tool listed under `Explore Options` in the drop-down menu. The browser will then load an html page containing the external tool. 

In this window, the original tabular file can be used as long as the user calling the tool has access to the file (so it does not work for users wanting to work with restricted files they have not received access to). Any output generated by the external tool can be saved as an auxiliary file, which can be downloaded via the same `Access File` dropdown menu, and either saved to the user's disk or uploaded to the dataset.

During this experiment, one limitation of the External Tools functionality was discovered, namely that an auxiliary file can currently only be created for restricted files. For the current use case, this is unlikely to pose problems because synthetic data is most often generated from restricted data, but it may be a good idea to have the issue fixed to avoid later bugs. 

For this approach to work with Metasyn, we would need to turn it into a service that can be called within the External Tools menu. One way to do this would be to create an API that allows for creation of a GMF file and/or the resulting synthetic data. The next section describes the first attempt at developing such an API.  

### Metasyn API 
We created a simple fastAPI wrapper for the Metasyn functionalities of creating and downloading a GMF and generating synthetic data with the GMF. Both functionalities have their own endpoint which can be called separately. See [the github repo](https://github.com/tdcc-synthetic-data/synthetic_metadata_interop/tree/main/metasyn_api) for more details and instructions on installing and using the API. 

The API can currently only be run locally, and does not include any authentication or security features. It is intended as a starting point for further development, and for testing if it could work in tandem with the External Tools functionality. 


## Next steps
The next steps are tying it all together so that the API can be used as an external tool. That would require more development work on the API, for instance by making it more secure so that it can be openly accessible. 

## Summary 
- The goal of this task was to explore how Metasyn, a tool for synthetic data generation, can be integrated into the DANS Data Station SSH.
- We propose to use the External Tools functionality from Dataverse that allows external tools to be used without leaving the depositing/editing page of a dataset. 
- This option requires Metasyn to be callable from within the external tools page, for instance by creating a safe API that can output the synthetic data and/or GMF. 
- This way, depositors or data station managers who have access to the a restricted file can generate a synthetic data version that can be shared openly. 


## AI Statement 
No AI was used in writing this report. 


