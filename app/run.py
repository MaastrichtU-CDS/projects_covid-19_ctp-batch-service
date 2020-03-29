import subprocess
import os
import json
from flask import Flask, Response, request, send_file, abort, jsonify

with open("config.json") as f:
    config = json.load(f)

def runCtp(inputFolder, outputFolder, filterScript=None, anonymizerScript=None, lookupTable=None, nThreads=1):
    os.makedirs(outputFolder, exist_ok=True)

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

def deidentify(configName):
    currentConfig = config[configName]
    
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
    
    return ctpResult

app.run(debug=True, host='0.0.0.0', port=80)