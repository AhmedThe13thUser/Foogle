# Foogle The Search Engine.

# Installation
Here are the insturctions step by step to install Foogle and Run it
## for Windows
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```
### for Mac and Linux (Unix Based Machines)
```bash
pip3 install -r requirements.txt
python -m spacy download en_core_web_lg
```

# Updating the files

If You want to index more files because currently we just indexed around 5000 URLs, you can just run

```bash
python crawler.py
python indexer.py
```
or
```bash
python3 crawler.py
python3 indexer.py
```
and if it asks you for a file location, just hit enter.

## Usage
and to run you can just

```bash
python Search.py
```
or
```bash
python3 Search.py
```
this will start a webserver running on `localhost:8000`

# Enjoy!

## this work was made by Ahmed Abdalbaset.