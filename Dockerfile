FROM openjdk:8-buster

RUN apt update && apt install -y unzip python3.7 python3-pip python3-dev git

################# Install pydicomtools from source repository
RUN python3 -m pip install --upgrade pip setuptools wheel

RUN git clone https://gitlab.com/UM-CDS/general-tools/pydicomtools.git
RUN python3 -m pip install -e /pydicomtools
################# Install ImageIO java libraries


RUN curl -o linux-x86_64.zip http://mirc.rsna.org/ImageIO/linux-x86_64.zip
RUN unzip linux-x86_64.zip
RUN cp linux-x86_64/clibwrapper_jiio-1.2-pre-dr-b04.jar $JAVA_HOME/jre/lib/ext
RUN cp linux-x86_64/jai_imageio-1.2-pre-dr-b04.jar $JAVA_HOME/jre/lib/ext
RUN cp linux-x86_64/libclib_jiio.so $JAVA_HOME/jre/lib/i386
RUN cp linux-x86_64/libclib_jiio.so $JAVA_HOME/jre/lib/amd64
RUN mkdir $JAVA_HOME/jre/i386
RUN cp linux-x86_64/libclib_jiio.so $JAVA_HOME/jre/i386

################# Install application

ADD ./app /app
WORKDIR /app
RUN python3 -m pip install -r requirements.txt


################# Install CTP

RUN curl -o DicomAnonymizerTool-installer.jar http://mirc.rsna.org/download/DicomAnonymizerTool-installer.jar
RUN jar xf DicomAnonymizerTool-installer.jar DicomAnonymizerTool

EXPOSE 80

CMD ["python3", "run.py"]
