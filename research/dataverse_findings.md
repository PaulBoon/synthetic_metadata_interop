# Findings of "[investigate Dataverse tabular data ingest function](https://github.com/tdcc-synthetic-data/synthetic_metadata_interop/issues/4)" issue

Author: Alessandra Polimeno \
Date: January 6, 2026

## Context 
Dataverse allows you to upload plain‑text tables (CSV, TSV, etc.) and automatically creates a DDI codebook and a visual preview that stores variable metadata. The issue is that we don’t clearly know how the variable information for those tables is stored inside Dataverse, or whether there’s extra metadata not shown in the DDI codebook. If we can discover that internal representation and a way to retrieve it programmatically, we could extract the information that is require to write a schema of the file that can be used by metasyn to create a synthetic version of the data. The information we are looking for minimally includes variable names and data types. 

TL;DR: How is the metadata of a tabular file represented in Dataverse, and how can we programmatically access it? 



## Synthesizing data with Metasyn
This section outlines some steps that are required to generate synthetic data based on a CSV file. It is based on the [metasyn documentation](https://metasyn.readthedocs.io/en/latest/quick_start.html) and assumes the processing is done in Python. Only the information that is relevant for this report is included, so please consult the official documentation for a tutorial on synthesizing your data.  

Skip to the [Summary and implications](/findings.md#summary-and-implications) header if you don't want to know the specifics. 

### Specify the data types 
You begin with specifying the schema of the data. For this schema declaration only the **variable name** and **data type** are required. (`pl` stands for `polars`, a Python package that handles data.) 

``` python
data_types = {
   "Sex": pl.Categorical,
   "Embarked": pl.Categorical,
   "Birthday": pl.Date,
   "Board time": pl.Time,
   "Married since": pl.DateTime,
}
```
### Read data as DataFame
When loading the data you should specify the schema you declared in the previous step. 

```python
df, file_format = ms.read_csv(csv_path, schema_overrides = data_types)

```

### Generate a MetaFrame and save it to a GMF file
Metasyn works with so-called MetaFrames that store the variable metadata that is required to synthesize the data. 

``` python
mf = ms.MetaFrame.fit_dataframe(df, file_format=file_format)
```

Below you see an example of the information that is contained in a MetaFrame. This information is inferred from the DataFrame created in previous step.  

``` c#
Column 1: "PassengerId"
- Variable Type: discrete
- Data Type: Int64
- Proportion of Missing Values: 0.0000
- Distribution:
   - Type: core.uniform
   - Provenance: builtin
   - Parameters:
      - lower: 1
      - upper: 892

Column 2: "Name"
# ...
```

The MetaFrame can be saved for later usage with the `save` method. It will create a [GMF](https://github.com/sodascience/generative_metadata_format) (Generative Metadata Format) that was created by the developers for this project. A GMF file can be saved and loaded as a JSON. 

```
mf.save("saved_metaframe.json")
```

### Synthesizing the data 
All this step requires as input is a MetaFrame (either generated directly or through a loaded GMF file).

``` python
synthetic_data = mf.synthesize(5)
```

### Summary and implications 
- There are two things that are needed to create a synthetic data set: **your original dataset** and the corresponding **schema** (which can be quite minimal: the variable names and data types are sufficient). 
  - This information is obtainable through Dataverse for open access files (see below how).
  - For restricted access files, however, schema information and data access is only reserved for the depositor or users that have explicitly received access rights to the restricted file. 


## File metadata in Dataverse
This section outlines how the metadata for tabular files is stored in Dataverse, and how it can be accessed. 


### Metadata storage 
The following information was found in the [Dataverse documentation](https://guides.dataverse.org/en/latest/user/tabulardataingest/ingestprocess.html). Metadata that describes the content of a tab-delimited file in Dataverse is stored separately in a relational database. The structure of this metadata was originally based on the DDI Codebook format, and can be exported accordingly. 

### Accessing file metadata 
The relational database that stores the tabular datafile metadata cannot be accessed directly through an API (as far as we could find so far), but an export as DDI Codebook can be obtained manually by going to the file landing page and choosing Access File > Download Metadata > DDI Codebook v2. 

You can programmatically access the metadata using a REST endpoint: 
```bash
GET /api/access/datafile/{fileId}/metadata/ddi
```
Use this example to download the metadata for a random open tabular file in the SSH Data Station. It should result in an XML file describing the file variables. 
```
https://ssh.datastations.nl/api/access/datafile/617598/metadata/ddi
``` 
As expected (and intended) this does not work for restricted access files: 
```
https://ssh.datastations.nl/api/access/datafile/617262/metadata/ddi
```

The contents of the metadata file will be discussed in more detail in the section [below](/findings.md#scenario-we-have-the-file-metadata-but-not-the-original-data). 

Note that the Dataverse API outputs an XML file that holds the metadata. We would have to write a simple wrapper that parses the XML, extracts the relevant variable information and formats it in a way that can be ingested by Metasyn.  


## Scenario: We have the file metadata but not the original data. 
It could be the case that the original dataset is not available, but a file metadata export is. You could create the [GMF](https://github.com/sodascience/generative_metadata_format) directly based on the schema and variable information and apply the metasyn `synthesize` function. Now the question becomes: does the Dataverse metadata export (as XML) give us enough information to create a GMF for that file? This section explores that question. 


> The table below displays the information that should be found in a GMF file, as well as whether this information can be found in the Dataverse file metadata export. 

| info in GMF | Dataverse export |   
| --- | --- | 
| variable name | 'name' | 
| variable type (e.g. discrete) | 'intrvl' | 
| data type | 'varFormat type' | 
| proportion NaN | **not present** | 
| distribution info: type (e.g. uniform)| **not present?**| 
| distribution info: provenance (e.g. builtin) | **not present?**| 
| distribution info: parameters (e.g. lower/upper) | **not present,** but mean/stdev/max/min etc info is present under 'sumStat' for numericals. | 

> You can inspect an example of the metadata for one numerical variable in a Dataverse file metadata export below. 
```xml
<var ID="xxx" name="Starttime" intrvl="contin">
    <location fileid="xxx"/>
    <labl level="variable">Starttime</labl>
    <sumStat type="stdev">12.781264817232628</sumStat>
    <sumStat type="vald">504.0</sumStat>
    <sumStat type="mean">45428.67453469466</sumStat>
    <sumStat type="mode">.</sumStat>
    <sumStat type="max">45446.7087037037</sumStat>
    <sumStat type="min">45411.6659722222</sumStat>
    <sumStat type="invd">0.0</sumStat>
    <sumStat type="medn">45426.6613310185</sumStat>
    <varFormat type="numeric"/>
    <notes subject="Universal Numeric Fingerprint"level="variable" type="VDC:UNF">UNF:6:xxx</notes>
</var>
```
This information is included in a textual variable: 
```xml
<var ID="xxx" name="waarde" intrvl="discrete">
    <location fileid="xxx"/>
    <labl level="variable">waarde</labl>
    <varFormat type="character"/>
    <notes subject="Universal Numeric Fingerprint"level="variable" type="VDC:UNF">UNF:6:xxx</notes>
</var>
```

> Conclusion: the Dataverse file metadata export does not provide enough information to create a GMF file. 



## Takeaways 
- To create a synthetic dataset with metasyn, two components are required: the original dataset and the corresponding schema that at least specifies the variable names and their data types. 
- It should also be possible to generate synthetic data if the original dataset is not available, as long as there is enough schema information in the file metadata to create a GMF (Generative Metadata Format) file. With the metadata we accessed so far using the Dataverse API, this is not the case, so we would have to look for alternative ways to obtain this information. 
- The current bottleneck in implementing a synthetic data generation tool into Dataverse is the inherent fact that data and schema information of restricted files are not accessible unless this is granted to a user explicitly. This is problematic because synthetic data generation is mostly useful for restricted files. 
  - A possible workaround would be to let the depositor create the synthetic dataset when depositing the restricted file. 
  - Another workaround would be for us to ask the depositors for access so we can add a synthetic open version if met with a positive reply.    

