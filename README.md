# synthetic_metadata_interop
Exploration into interoperability of metasyn's GMF into existing metadata formats. 

It contains the following main parts: 
- [research](research/): notes and findings on Dataverse metadata, file ingest and how GMF could fit in.
- [dataverse_external_tools](dataverse_external_tools/README.md): first experiment using the Dataverse 'External Tools' mechanism to retrieve and store information (potentially the synthetic data or GMF) in Dataverse.
- [dataverse_metasyn](dataverse_metasyn/README.md): External Tools page that calls the Metasyn API to create a GMF model from a tabular file, or synthetic data from a GMF file.
- [metasyn_api](metasyn_api/README.md): FastAPI wrapper around metasyn with `/fit-model/` and `/synthesize/` endpoints, plus a 'user friendly' UI page.



Related READMEs: [metasyn](https://github.com/sodascience/metasyn#readme) · [GMF](https://github.com/sodascience/gmf#readme)


