from nytimes/blender:2.93-gpu-ubuntu18.04

RUN apt-get update && apt-get install -y sudo 

RUN apt-get install -y chromium-chromedriver
RUN apt-get install -y git less vim 

RUN /bin/2.93/python/bin/pip install wheel
RUN /bin/2.93/python/bin/pip install ipython matplotlib pdbpp

USER ${USER}

# Install the Archipack extension
WORKDIR /tmp
RUN wget https://github.com/s-leger/archipack/archive/master.zip -O archipack.zip && \
    blender -b --python-expr \
     "import bpy;"`\
    `"bpy.ops.preferences.addon_install(filepath='/tmp/archipack.zip');"`\
    `"bpy.ops.preferences.addon_enable(module='archipack');"`\
    `"bpy.ops.wm.save_userpref()" && \
    rm archipack.zip


WORKDIR /workspace/
