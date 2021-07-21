#!/bin/sh -l

# sh -c "echo Hello world my name is $INPUT_MY_NAME"
ssh -v -i __TEMP_INPUT_KEY_FILE -P "${INPUT_PORT}" "${INPUT_USER}"@"${INPUT_HOST}" 
cd sumpf
svn update
svn add protocoldude3.py
svn commit -m"Protocoldude3: auto new version"
