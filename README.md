# World of Tanks Model Converter
Converts World of Tanks models to wavefront obj or collada dae format.
*obj contains only geometry mesh
*collada DAE contains everything including dummy nodes and skinned weight table. (tested under 3dsMax 2012)

This version requires numpy to work.
If you do not want to install numpy and do not need collada DAE export, a legacy version exists. 
It has no module dependency but only support obj format.
https://github.com/atacms/wot-model-converter-legacy

# Attention BigWorld SDK users:
# 'Portal' related error messages 
Because 'hull' is a reserved keyword to identify 'portal' object in BigWorld engine, the name of a model object in 3dsmax(perhaps maya aswell) should not contain the string 'hull', otherwise an error message will be produced by BigWorld 3dsMax exporter plugin saying no valid portal is found in the scene.
Because hull is the name of tank hull model file in WoT, this script will frequently creates objects with 'hull' in its name, causing this error.
Just rename it to something else.


## Notes
* script only parse diffuse textures
* all primitive groups are packed into one exported file at this time
* skinned weight are not supported by wavefront obj. Collada DAE can do the trick. Weight export is still in development but nodes can be exported ATM.
* support new primitives variant used in WoT v0.9.12+ HD models. 
* model mirroring is adapt to standard WG models. Results for models built by other parties are not guaranteed.
* a slightly modified version of pycollada is used. The changes are not final so it's currently not linked to pycollada's github repo but instead included a copy in this project's lib folder

## Additional credits (not mentioned on github)
Thanks to Phux_and_the_Wheel_Bearing (AKA Coffee_), from whose code this script originates

## Usage
Script requires .primitives and .visual files (or .primitives_processed and .visual_processed in case of WoT 0.9.12+) of model to create obj (and mtl) file. You can either specify only primitives file and script will assume visual file is in same folder with same name, but different extension, or you can specify path to visual file separatedly.
Script can compress result obj and mtl files using zlib.
```
usage: convert-primitive.py [-h] [-v VISUAL] [-o OBJ] [-m MTL] [-t TEXTURES]
                            [-sx SCALEX] [-sy SCALEY] [-sz SCALEZ]
                            [-tx TRANSX] [-ty TRANSY] [-tz TRANSZ] [-c] [-nm]
                            [-nvt] [-nvn] [-f FORMAT]
                            input

or convert-primitive.py [-gui]

Converts BigWorld primitives file to obj or dae.

positional arguments:
  input                 primitives file path (wildcard accepted)

optional arguments:
  -h, --help            show this help message and exit
  -v VISUAL, --visual VISUAL
                        visual file path
  -o OBJ, --output OBJ  result obj/dae path
  -m MTL, --mtl MTL     result mtl path
  -t TEXTURES, -t TEXTURES
                        path to textures
  -sx SCALEX, --scalex SCALEX
                        X scale
  -sy SCALEY, --scaley SCALEY
                        Y scale
  -sz SCALEZ, --scalez SCALEZ
                        Z scale
  -tx TRANSX, --transx TRANSX
                        X transform
  -ty TRANSY, --transy TRANSY
                        Y transform
  -tz TRANSZ, --transz TRANSZ
                        Z transform
  -c, --compress        Compress output using zlib
  -nm, --nomtl          don't output material
  -nvt, --novt          don't output UV coordinates
  -nvn, --novn          don't output normals
  -f FORMAT             choose output format. FORMAT accepts obj or collada. Default to wavefront obj
```

## Example
```convert-primitive.py *.primitives_processed```
will process all primitives_processed files and output .obj under current folder.

```convert-primitive.py -f collada *.primitives_processed```
will process all primitives_processed files and output .dae under current folder.

```convert-primitive.py -o Hull.obj Hull.primitives```
will output 'Hull.obj' with all model data and 'Hull.mtl' with materials

```convert-primitive.py -f collada -o Hull.dae Hull.primitives```
will output 'Hull.dae'


```convert-primitive.py -gui```
will open window with options of exports

## Requirements
Python 2.7x
numpy
and to install numpy you might need pip if your python version doesn't have one.