import subprocess
import os
import json
import pydicom
import random
import string
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
    
    dcmHeader = getheaderFirstFile(inputFolder)

    lookupItems = config["lookup_maintained"][lookupListName]
    lookupList = lookupLists[lookupListName]
    for lookupItem in lookupItems:
        prefixItem = lookupItem["prefix"]
        dicomTagItem = lookupItem["dicomTag"]

        curSubList = lookupList[prefixItem]
        currentValue = dcmHeader[dicomTagItem].value
        if currentValue in curSubList:
            break #in this case, the current value is already in the lookup list as key
        else:
            newId = generateUniqueId(curSubList, numericValue=lookupItem["numeric"])
            curSubList[currentValue] = newId
        lookupFileNameJSON
        lookupList[prefixItem] = curSubList
    lookupLists[lookupListName] = lookupList

    saveLookupList(lookupListName)
    
def getheaderFirstFile(folderToLook):
    for root, subdirs, files in os.walk(folderToLook):
        for filename in files:
            if(filename.endswith(".dcm") or filename.endswith(".DCM")):
                return pydicom.dcmread(os.path.join(root, filename))
    
    return None

def runCtp(inputFolder, outputFolder, filterScript=None, anonymizerScript=None, lookupTable=None, nThreads=1):
    os.makedirs(outputFolder, exist_ok=True)

    checkLookup(lookupTable, inputFolder)

    cmd = "java -jar DicomAnonymizerTool/DAT.jar -v "
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

    for root, subdirs, files in os.walk(outputFolder):
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
    return jsonify(deidentify("default"))

@app.route("/<string:route>", methods=["POST"])
def deidentifyCustomRoute(route):
    return jsonify(deidentify(route))

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

        inputFolder = inputData["inputFolder"]
        outputFolder = inputData["outputFolder"]

    ctpResult = runCtp(inputFolder, 
        outputFolder, 
        filterScript=filterScript, 
        anonymizerScript=anonymizerScript,
        lookupTable=lookupTable,
        nThreads=nThreads)
    deidentifiedFiles = renameAndReturnFiles(outputFolder)

    return {
        "ctpErrors": ctpResult,
        "deidentifiedFiles": deidentifiedFiles}

app.run(debug=True, host='0.0.0.0', port=80)