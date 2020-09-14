rem docker rm ctpbatch
rem docker build -t ctpbatch ../

docker run -it --rm ^
    -p 80:80 ^
    -v %cd%\config.json:/app/config.json ^
    -v %cd%\anonymizer.properties:/anonymizer.script ^
    -v %cd%\filter.script:/filter.script ^
    -v %cd%\lookup.properties:/lookup.properties ^
    -v %cd%\..\app\run.py:/app/run.py ^
    ctpbatch