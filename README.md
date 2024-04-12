# mimir2librechat

Trying out LibreChat as AI chatbot API frontend and want to migrate old conversations from the previous frontend. This script will migrate users, conversations and messages. Attached files would require much more work, skipping for now.

## Usage

```bash
usage: mimir2librechat.py [-h] -s SQLITE3 -m MONGODB

Migrate Mimir data to LibreChat

options:
  -h, --help            show this help message and exit
  -s SQLITE3, --sqlite3 SQLITE3
                        Path to the sqlite3 database
  -m MONGODB, --mongodb MONGODB
                        URI to the mongodb database

Ex.
python mimir2librechat.py -s db.sqlite3 -m localhost:27017
```
