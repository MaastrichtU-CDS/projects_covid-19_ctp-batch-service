import zipfile
import requests

with open('./CT.zip', 'rb') as f:
    ctData = f.read()
binary_return = requests.post(url="http://localhost/",
                data=ctData,
                headers={'Content-Type': 'application/zip'})

with open("output.zip", "wb") as fout:
    fout.write(binary_return.content)
    fout.close()