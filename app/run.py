import subprocess
import os
import json
import pydicom
from pydicomtools.DicomDatabase import PatientDatabase, Patient, Series
import random
import string
import tempfile
import zipfile
import io
from flask import Flask, Response, request, send_file, abort, jsonify

with open("config.json") as f:
    config = json.load(f)

lookupLists = dict()

for lookupFileName in config["lookup_maintained"]:
    lookupFileNameJSON = lookupFileName + ".json"
    
    if not os.path.exists(lookupFileNameJSON):
        lookupLists[lookupFileName] = dict()
        
        for lookupConfig in config["lookup_maintained"][lookupFileName]:
            lookupLists[lookupFileName][lookupConfig["prefix"]] = dict()
    else:
        with open(lookupFileNameJSON) as f:
            lookupLists[lookupFileName] = json.load(f)

def randomString(stringLength=10):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

def generateUniqueId(lookupList, numericValue=False):
    newId = randomString()
    if numericValue:
        newId = random.randrange(100000000, 999999999)
    isUnique = False

    while not isUnique:
        foundInList = False
        for newIds in lookupList.values():
            if newIds==newId:
                foundInList = True
        
        if not foundInList:
            isUnique = True
        else:
            if numericValue:
                newId = random.randrange(1000000, 9999999)
            else:
                newId = randomString()
    
    return newId

def saveLookupList(lookupListName):
    lookupListNameJSON = lookupListName + ".json"

    lookupList = lookupLists[lookupListName]

    with open(lookupListNameJSON, "w") as f:
        json.dump(lookupList, f)
    
    with open(lookupListName, "w") as f:
        for lookupConfig in config["lookup_maintained"][lookupFileName]:
            prefix = lookupConfig["prefix"]
            for keyValue in lookupList[prefix]:
                outputString = "%s/%s=%s" % (prefix,keyValue,lookupList[prefix][keyValue])
                f.write(outputString + os.linesep)


def checkLookup(lookupListName, inputFolder):
    if not lookupListName in config["lookup_maintained"]:
        return
    
    dcmHeaders = getHeadersFromSeries(inputFolder)

    for dcmHeader in dcmHeaders:
        lookupItems = config["lookup_maintained"][lookupListName]
        lookupList = lookupLists[lookupListName]
        for lookupItem in lookupItems:
            prefixItem = lookupItem["prefix"]
            dicomTagItem = lookupItem["dicomTag"]

            curSubList = lookupList[prefixItem]
            currentValue = "DoesNotExist"
            if dcmHeader[dicomTagItem] is not None:
                currentValue = dcmHeader[dicomTagItem].value
            else:
                print("Warning, Tag %s does not always exist." % dicomTagItem)
                break
                
            if currentValue in curSubList:
                break #in this case, the current value is already in the lookup list as key
            else:
                newId = generateUniqueId(curSubList, numericValue=lookupItem["numeric"])
                curSubList[currentValue] = newId
            lookupFileNameJSON
            lookupList[prefixItem] = curSubList
        lookupLists[lookupListName] = lookupList

    saveLookupList(lookupListName)
    
def getHeadersFromSeries(folderToLook):
    headers = [ ]
    
    patientDb = PatientDatabase()
    patientDb.parseFolder(folderToLook)

    for ptId in patientDb.patient:
        curPatient = patientDb.patient[ptId]
        for seriesUid in curPatient.series:
            filePaths = list(curPatient.series[seriesUid].filePath.values())
            dcmHeader = pydicom.dcmread(filePaths[0])
            headers.append(dcmHeader)

    return headers

def runCtp(inputFolder, outputFolder, filterScript=None, anonymizerScript=None, lookupTable=None, nThreads=1):
    os.makedirs(outputFolder, exist_ok=True)

    checkLookup(lookupTable, inputFolder)

    cmd = "cd DicomAnonymizerTool && java -jar DAT.jar -v "
    cmd += "-in %s " % inputFolder
    cmd += "-out %s " % outputFolder
    if not filterScript is None:
        cmd += "-f %s " % filterScript
    if not anonymizerScript is None:
        cmd += "-da %s " % anonymizerScript
    if not lookupTable is None:
        cmd += "-lut %s " % lookupTable
    cmd += "-n %s" % nThreads

    print(cmd)

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    stdOut = out.decode("utf-8")
    stdErr = err.decode("utf-8")

    if len(stdErr) > 0:
        raise Exception("Error running CTP", stdErr)

    outputLines = stdOut.splitlines()
    errorLines = list()
    for line in outputLines:
        if "!quarantine!" in line:
            errorLines.append(str(line))
    return errorLines

def renameAndReturnFiles(outputFolder):
    newFileNames = list()

    for root, _, files in os.walk(outputFolder):
        for filename in files:
            if(filename.endswith(".dcm") or filename.endswith(".DCM")):
                currentFilePath = os.path.join(root, filename)
                
                dcmHeader = pydicom.dcmread(currentFilePath)
                sopInstanceUid = dcmHeader[0x8,0x18].value
                targetFilePath = os.path.join(root, sopInstanceUid + ".dcm")
                os.rename(currentFilePath, targetFilePath)
                newFileNames.append(targetFilePath)
    
    return newFileNames

app = Flask('CTP Anonymizer Service')

@app.route("/", methods=["GET"])
def index():
    return "Please send instructions via HTTP-POST"

@app.route("/", methods=["POST"])
def deidentifyDefaultRoute():
    return deidentify("default")

@app.route("/<string:route>", methods=["POST"])
def deidentifyCustomRoute(route):
    return deidentify(route)

def deidentify(routeName):
    currentConfig = config["routes"][routeName]
    
    inputFolder = currentConfig["inputFolder"]
    outputFolder = currentConfig["outputFolder"]
    filterScript = currentConfig["filterScript"]
    anonymizerScript = currentConfig["anonymizerScript"]
    lookupTable = currentConfig["lookupTable"]
    nThreads = currentConfig["threads"]

    contentType = request.content_type

    if contentType == "application/json":
        inputData = request.get_json()
        return jsonify(deidentify_json_input(inputData, filterScript, anonymizerScript, lookupTable, nThreads))
    if contentType == "application/zip":
        tmpDirIn = tempfile.TemporaryDirectory()
        tmpDirOut = tempfile.TemporaryDirectory()
        zf = zipfile.ZipFile(io.BytesIO(request.get_data()))
        zf.extractall(tmpDirIn.name)
        return deidentify_folder_input(tmpDirIn.name, tmpDirOut.name, filterScript, anonymizerScript, lookupTable, nThreads)

def deidentify_folder_input(inputFolderString, outputFolderString, filterScript, anonymizerScript, lookupTable, nThreads):
    ctpResult = runCtp(inputFolderString, 
        outputFolderString, 
        filterScript=filterScript, 
        anonymizerScript=anonymizerScript,
        lookupTable=lookupTable,
        nThreads=nThreads)
    
    deidentifiedFiles = dict()
    patientDb = PatientDatabase()
    patientDb.parseFolder(outputFolderString)

    for patient in patientDb.patient.values():
        for serie in patient.series.values():
            deidentifiedFiles.update(serie.filePath)

    fileName = tempfile.NamedTemporaryFile()
    fileZip = zipfile.ZipFile(fileName, 'w', zipfile.ZIP_DEFLATED)

    print("{} files found after deidentification".format(len(deidentifiedFiles)))

    for myFileUid in deidentifiedFiles:
        myFile = deidentifiedFiles[myFileUid]
        try:
            fileZip.write(myFile, myFileUid)
        except:
            print("Could not find file: " + myFile)

    fileZip.close()
    return send_file(fileName.name, mimetype='application/zip')

def deidentify_json_input(inputData, filterScript, anonymizerScript, lookupTable, nThreads):
    inputFolder = inputData["inputFolder"]
    outputFolder = inputData["outputFolder"]

    ctpResult = runCtp(inputFolder, 
        outputFolder, 
        filterScript=filterScript, 
        anonymizerScript=anonymizerScript,
        lookupTable=lookupTable,
        nThreads=nThreads)
    deidentifiedFiles = renameAndReturnFiles(outputFolder)

    os.system("chmod -R 777 %s" % outputFolder)
    
    return {
        "ctpErrors": ctpResult,
        "deidentifiedFiles": deidentifiedFiles}

app.run(debug=True, host='0.0.0.0', port=80)