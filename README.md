# CTP Batch Service

This repository contains the code for a CTP service batch processor.

## How does it work?

The docker container (or the code in [app/run.py](app/run.py)) creates a Flask webservice which listens for HTTP POST requests (Content-Type = application/json), which specifies which (mounted volume) the dicom files are located to be deidentified.

The JSON for the HTTP-POST call looks as follows:
```
{
    "inputFolder": "data/original",
    "outputFolder": "data/deidentified"
}
```

**Mind that this input/output location is relative to the /app folder within the docker container.** Other paths (including absolute paths) can be specified as well.

## How to setup?

The [app/run.py](app/run.py) file contains the main application. It requires a file in [app/config.json](app/config.json), which is included by default, but can be overridden with a file mount in docker.

An example of starting the service could look as follows:
```
docker run -d \
    --name ctp-service \
    -p 80:80 \
    -v $(pwd)/anonymizer.script:/anonymizer.script \
    -v $(pwd)/filter.script:/filter.script \
    -v $(pwd)/lookup.properties:/lookup.properties \
    -v $(pwd)/data:/app/data \
    registry.gitlab.com/um-cds/projects/covid-19/ctp-batch-service:master
```

Mind that the volume mounts for `anonymizer.script`, `filter.script`, `lookup.properties` and `/app/data` are based on the **given** [config.json](app/config.json). When updating config.json, these volume mounts need to be changed accordingly!

## Routes

In [config.json](app/config.json) it is possible to define multiple `routes`. This means that instead of only `http://my-url/` also multiple subdirectories can be used (such as `http://my-url/myRoute`). For every route (subdirectory) a separate entry is being made next to `default`. An example for `default` and `myRoute` is given below.

```
    "routes": {
        "default": {
            "inputFolder": "data/original",
            "outputFolder": "data/deidentified",
            "filterScript": "/filter.script",
            "anonymizerScript": "/anonymizer.script",
            "lookupTable": "/lookup.properties",
            "threads": 1
        },
        "myRoute": {
            "inputFolder": "/myRoute/data/original",
            "outputFolder": "/myRoute/data/deidentified",
            "filterScript": "/myRoute/filter.script",
            "anonymizerScript": "/myRoute/anonymizer.script",
            "lookupTable": "/myRoute/lookup.properties",
            "threads": 2
        }
    }
```

**Mind that in this case, all additional files (in the folder `/myRoute` should be mounted in the docker configuration)**

## Lookup list maintenance

In [config.json](app/config.json), the option exists to append lookup tables with random values automatically. This is configured in the dictionary called `lookup_maintained` where lookup tables for different application routes (see application routes above) can be configured. The key in this dictionary corresponds to a lookup table file location, defined in the route. For every item in the lookup list, the following elements should be described:

* dicomTag: The dicomTag where the lookup list is defined for
* prefix: The keyword used for this tag in the anonymizer script (used in [@lookup(tag,keyword)](https://mircwiki.rsna.org/index.php?title=DICOM_Anonymizer_Configuration_for_Assigning_Subject_IDs#The_.40lookup_Function))
* numeric: Boolean indicating whether the random value generated for the lookup list should be a string ([a-z]) or an integer.
