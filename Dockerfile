FROM openjdk:8-stretch

RUN apt update && apt install -y unzip python3 python3-pip python3-dev
RUN curl -o linux-x86_64.zip http://mirc.rsna.org/ImageIO/linux-x86_64.zip
RUN unzip linux-x86_64.zip
RUN cp linux-x86_64/clibwrapper_jiio-1.2-pre-dr-b04.jar $JAVA_HOME/jre/lib/ext
RUN cp linux-x86_64/jai_imageio-1.2-pre-dr-b04.jar $JAVA_HOME/jre/lib/ext
RUN cp linux-x86_64/libclib_jiio.so $JAVA_HOME/jre/lib/i386
RUN cp linux-x86_64/libclib_jiio.so $JAVA_HOME/jre/lib/amd64
RUN mkdir $JAVA_HOME/jre/i386
RUN cp linux-x86_64/libclib_jiio.so $JAVA_HOME/jre/i386

################# To be fixed

ADD ./app /app
WORKDIR /app
RUN pip3 install -r requirements.txt

RUN curl -o DicomAnonymizerTool-installer.jar http://mirc.rsna.org/download/DicomAnonymizerTool-installer.jar
RUN jar xf DicomAnonymizerTool-installer.jar DicomAnonymizerTool

EXPOSE 80

CMD ["python3", "run.py"]
