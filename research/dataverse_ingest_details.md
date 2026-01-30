Dataverse Ingest Details
========================

Author: Paul Boon (without AI)\
Date: January 28, 2026


This document will describe (parts of) the Dataverse 'ingest' process in more detail in order to asses the possibilities to have it produce the information needed for the synthetic data generation. 

The ['findings document'](dataverse_findings.md) lists information needed for the 'GMF' that is missing in the 'ddi' metadata exposed by Dataverse. While some can be calculated from the existing metadata we certainly can not do that for the 'distribution info'. The synthetic data creation needs to have this in order to generate 'random' values resulting in a similar distribution. We can not assume some default here. The original data (or a representation thereof) has to be available to determine it. Therefore we will focus on that 'distribution info'. 


Code inspection was done on Dataverse version 6.5, where we assume the ingest process did not change much since that version, if at all. The Dataverse Github code repository is here: https://github.com/IQSS/dataverse. The Dataverse guides are here: https://guides.dataverse.org. Note that this will redirect to the guides of the latest version of Dataverse. The guides are extensive but it is not always obvious where certain information can be found. 


# Dataverse guides information on the ingest

The ingest is described in more detail here: https://guides.dataverse.org/en/latest/user/tabulardataingest/index.html.

Summary of the ingest functionality: 

Extract the data content from the user’s files and archive it in an application-neutral, easily-readable format; plain text, TAB-delimited files. 

Limitations: 

- It is explicitly limited to a set of formats, but even for a specific format it is not supporting all variations. 
- There is a configuration setting (`:TabularIngestSizeLimit`) that limits this ingest to files up to a specific size. If you set this at `0`, you disable it completely. 
  The DANS SSH Datastation now hat this set. 
  We can find the information in our deployment scripts in the `dans-core-systems`private Github repository. In `provisioning/group_vars/datastations.yml`. 
  ```
  shared_dataverse_options_tabularingestsizelimit: 5000000
  ```
  Which is in bytes, so equivalent to 5Mb. 
  This indicates that files larger than 5MB probably caused problems, also, this setting is there for a reason. 

# Dataverse ingest User Interface

The tabular file 'ingest' is initiated when a file is uploaded to a Dataset. The Dataset is being edited and in a 'Draft' mode for this to be possible. When the file upload is done, the 'Save' button must be pushed (otherwise you can cancel the Dataset edit). 
On that 'save' the ingest is started (if applicable for that file), there will be a visual indication that the file is being 'ingested'. This indication disappears when the ingest is done and the file details change to a `*.tab` file; which is the generated tabular file. The original file can now only be downloaded via selection of an item with 'Original' in the 'File Access' dropdown. While I have not tested it with a large file, I assume that when tis ingest takes longer than e few minute is will be a bad user experience. Also note that the longer it takes, the higher the risk that some timeout will break the user session. 


# Dataverse ingest code inspection

The Dataverse ingest code is placed in one directory: `src/main/java/edu/harvard/iq/dataverse/ingest`. 
The current code seems to be focussed on making it possible to add implementations for additional input file formats. There is an `IngestServiceProvider` abstract base class in a `edu.harvard.iq.dataverse.ingest.plugin.spi` package, which suggests that we could implement plugins, but there is no library (jar file) loading mechanism, so it is only for internal reuse. 
There are many more abstract base classes, forming a hierarchy. There are specific 'readers' for each file format. To get a better idea of what we could do to support that Synthetic data creation we could focus on one format; preferable a simple one like 'csv'. The csv 'reader' is here; `edu/harvard/iq/dataverse/ingest/tabulardata/impl/plugins/csv/CSVFileReader.java`. 
It actually stores the data into the database, via that `DataTable` class (`edu/harvard/iq/dataverse/DataTable.java`). 

If we inspect the DataTable class and what other classes it references we can produce the following list of 'information' that could be available in Dataverse, because it is persistently stored in the database via ORM. Below a summary of that information, with the descriptions partly copied from the code docs. 

DataTable:

- unf: the Universal Numeric Signature of the data table.
- caseQuantity: Number of observations
- varQuantity: Number of variables
- recordsPerCase: this property is specific to fixed-field data files
      in which rows of observations may represented by *multiple* lines.
      The only known use case (so far): the fixed-width data files from 
      ICPSR. 
- dataFile: (ManyToOne) DataFile that stores the data for this DataTable
- dataVariables(OneToMany):  DataVariables in this DataTable ( one to many !)
  DataVariable is mapped to a table!
- originalFileType: the format of the file from which this data table was
      extracted (STATA, SPSS, R, etc.)
      Note: this was previously stored in the StudyFile. 
- originalFormatVersion: the version/release number of the original file
      format; for example, STATA 9, SPSS 12, etc. 
- originalFileSize: Size of the original file
- originalFileName: the file name upon upload/ingest
- storedWithVariableHeader: The physical tab-delimited file is in storage with the list of variable
      names saved as the 1st line. This means that we do not need to generate 
      this line on the fly. (Also means that direct download mechanism can be
      used for this file!)


DataVariable:

- dataTable: (ManyToOne)
- name: Name of the Variable
- label: Variable Label
- weighted: indicates if this variable is weighted.
- fileStartPosition: this property is specific to fixed-width data; 
      this is a byte offset where the data column begins.
- fileEndPosition: similarly, byte offset where the variable column 
      ends in the fixed-width data file.
- interval: VariableInterval = { DISCRETE, CONTINUOUS, NOMINAL, DICHOTOMOUS }
- type: VariableType = { NUMERIC, CHARACTER }
- format: 
      used for format strings - such as "%D-%Y-%M" for date values, etc. 
      former formatSchemaName
- formatCategory: 
      Used for "time", "date", etc.
- recordSegmentNumber: this property is specific to fixed-width data 
      files.
- invalidRanges: (OneToMany) value ranges that are defined as "invalid" for this
      variable. 
      Note that VariableRange is itself an entity.
- invalidRangeItems: (OneToMany) a collection of individual value range items defined 
      as "invalid" for this variable.
      Note that VariableRangeItem is itself an entity. 
- summaryStatistics: (OneToMany) Summary Statistics for this variable.
      Note that SummaryStatistic is itself an entity.
- unf: printable representation of the UNF, Universal Numeric Fingerprint
      of this variable.
- categories: (OneToMany) Variable Categories, for categorical variables.
      VariableCategory is itself an entity. 
- orderedFactor: The boolean "ordered": identifies ordered categorical variables ("ordinals"). 
- factor: On ingest, we set "factor" to true only if the format is RData and the
      variable is a factor in R. See also "orderedFactor" above.
- fileOrder: the numeric order in which this variable occurs in the 
      physical file. 
- numberOfDecimalPoints: number of decimal points, where applicable.
- variableMetadatas: (OneToMany) VariableMetadata


VariableMetadata:

- dataVariable: (ManyToOne) DataVariable to which this metadata belongs.
- fileMetadta: (ManyToOne) FileMetadata to which this metadata belongs.
- label: variable label.
- literalquestion: literal question, metadata variable field.
- postquestion: post question, metadata variable field.
- interviewinstruction: Interview Instruction, metadata variable field.
- universe: metadata variable field.
- notes: notes, metadata variable field (CDATA).
- isweightvar: It defines if variable is a weight variable
- weighted: It defines if variable is weighted
- categoriesMetadata: (OneToMany) CategoryMetadata; variable metadata for categories that includes weighted frequencies
- weightvariable: DataVariable with which this variable is weighted.


CategoryMetadata:

- category: (ManyToOne)
- variableMetadata (ManyToOne)


VariableCategory: 

- dataVariable:(ManyToOne)
- value
- label
- missing
- catOrder
- frequency


SummaryStatistic:

- dataVariable: (ManyToOne) DataVariable for which this range is defined.
- SummaryStatisticType: type of this Summary Statistic value (for ex., "median", "mean", etc.) 
  {MEAN, MEDN, MODE, MIN, MAX, STDEV, VALD, INVD}
- value: string representation of this Summary Statistic value.


There is more, but the most relevant is the `SummaryStatistic`, because to produce it some statistics must have been calculated, like the 'mean'. 
It might be that `VariableMetadata.categoriesMetadata` has useful information about non numeric (textual/labeled) values, but we do not inspect this further. 


The `IngestServiceBean` is the starting point of the ingest; it has a method `produceSummaryStatistics`, which takes the `dataFile` and the `generatedTabularFile`. The calculations are done using the values from that generated tabular file. 
The `produceSummaryStatistics` is called by the `ingestAsTabular` method, which is calling methods to generate the tabular file before. 
The generation of the tab data (file) is done via the `TabularDataFileReader.read` method implementation.
That the tab file is created inside this `CSVFileReader`; it actually creates a file as tab delimited with the `csvFilePrinter`. It writes it in two passes, not sure why, but that was apparently needed. Note that the name 'Reader' and 'read' are a bit misleading because it also 'writes'. 

After the tabular file has been generated in the ingest process, the statistics is calculated. 
It is possible to add extra code and metadata (database) fields to store extra information, like that distribution info. But for this the 'tabular' data from the ingest must be there. If the original data is needed the ingest functionality would need to be refactored or another 'ingest like' process has to be implemented. The code would then also need to handle the different formats. 
And in all cases, some refactoring would be needed to improve support for larger files. 


# Conclusion

Extending the code is technically possible, but there are some issues that make it undesirable:
- We could calculate the GMF 'distribution info' type and parameters, but we would need to code that or use (port) the existing Python code from `metasyn`. 
- Calculation at ingest might take more time that what is acceptable on a UI for a depositor to wait for, especially for large files. 
- For large files we do not have an ingest configured in our SSH Datastation; assuming large is `> 5MB`. 


# Suggestions for integration with Dataverse

Instead of trying to change the Dataverse 'ingest' process I want to propose a different approach.  
Support synthetic data generation (and GMF) via the external tools configuration option in Dataverse. 
Similar approach was implemented by people from 'OpenDP' (Open Differential Privacy) six years ago; see their video: https://www.youtube.com/watch?v=0vfqPZcpi90

We should investigate the possibility to use the 'Secure External Tools': https://guides.dataverse.org/en/latest/api/external-tools.html. 

This 'external tools' functionality would allow to initiate a request to another service from the File page in Dataverse, passing file information that enables that service to do its work. 

