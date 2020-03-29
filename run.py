import subprocess
import os
import json

with open("config.json") as f:
    config = json.load(f)

currentConfig = config["default"]

os.makedirs(currentConfig["outputFolder"], exist_ok=True)

cmd = "java -jar DicomAnonymizerTool/DAT.jar -v "
cmd += "-in %s " % currentConfig["inputFolder"]
cmd += "-out %s " % currentConfig["outputFolder"]
cmd += "-f %s " % currentConfig["filterScript"]
cmd += "-da %s " % currentConfig["anonymizerScript"]
cmd += "-lut %s " % currentConfig["lookupTable"]
cmd += "-n %s" % currentConfig["threads"]

print(cmd)

p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = p.communicate()
stdOut = out.decode("utf-8")
stdErr = err.decode("utf-8")

print("===============================Output log===============================")
outputLines = stdOut.splitlines()
for line in outputLines:
    if "!quarantine!" in line:
        print(line)
print(outputLines[len(outputLines)-1])

print("===============================Error log===============================")
print(stdErr)