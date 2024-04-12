import sqlite3
import pymongo
import argparse
import pdb
from bson.objectid import ObjectId
import uuid
import sys
from datetime import datetime
from pprint import pprint


# Argument parser
parser = argparse.ArgumentParser(description='Migrate Mimir data to LibreChat')
parser.add_argument('-s', '--sqlite3', type=str, help='Path to the sqlite3 database', required=True)
parser.add_argument('-m', '--mongodb', type=str, help='URI to the mongodb database', required=True)
args = parser.parse_args()

# Sqlite3 connection
conn = sqlite3.connect(args.sqlite3)
conn.row_factory = sqlite3.Row  # Set row_factory to sqlite3.Row
cursor = conn.cursor()

# MongoDB connection
mdb_client = pymongo.MongoClient(f"mongodb://{args.mongodb}")
mdb_db = mdb_client["LibreChat"]
mdb_users = mdb_db["users"]
mdb_conversations = mdb_db["conversations"]
mdb_messages = mdb_db["messages"]


# Query all users from auth_user table
cursor.execute("SELECT * FROM auth_user")
rows = cursor.fetchall()

# create user id mapping
uid_s2m = {}
uid_m2s = {}

for row in rows:

    # Check if user already exists based on email
    existing_user = mdb_users.find_one({"email": row['email']})
    if existing_user:
        # save user mapping
        uid_s2m[row['id']] = existing_user["_id"]
        uid_m2s[existing_user["_id"]] = row['id']
        continue

    # save user mapping
    object_id = ObjectId()
    uid_s2m[row['id']] = object_id
    uid_m2s[object_id] = row['id']

    # Transform Sqlite3 data to Mongodb schema
    user = {
        "_id": object_id,  # New _id using ObjectId
        "name": f"{row['first_name']} {row['last_name']}",
        "username": row['username'],
        "email": row['email'],
        "emailVerified": False,  # Default value
        "password": row['password'],
        "avatar": None,  # Default value
        "provider": 'local',  # Default value
        "role": 'ADMIN' if row['is_superuser'] else 'USER',  # Assuming is_superuser indicates ADMIN role
        "plugins": [],  # Default value
        "refreshToken": [],  # Default value
        "createdAt": datetime.fromisoformat(row['date_joined']),  # Assuming date_joined is the createdAt
        "updatedAt": datetime.fromisoformat(row['last_login']) if row['last_login'] else datetime.fromisoformat(row['date_joined']),  # Assuming last_login is the updatedAt
        "__v": 0  # Default value
    }

    # Insert into MongoDB
    mdb_users.insert_one(user)







# Query all conversations from conversation table
cursor.execute("SELECT * FROM chat_conversation")
rows = cursor.fetchall()
conversations = {}
for row in rows:
   conversations[row['id']] = dict(row)
   conversations[row['id']]['messages'] = []

# Query all messages from chat_message table
cursor.execute("SELECT * FROM chat_message")
rows = cursor.fetchall()
messages = {}
for row in rows:
   messages[row['id']] = dict(row)
   conversations[row['conversation_id']]['messages'].append(row['id'])


# create conversation and message id mapping
cids = {}
mids = {}

# create LibreChat conversation
for s_conversation_id, s_conversation in conversations.items():

    # generate new conversation ids
    m_conversation_id = ObjectId()
    m_conversation_uuid = str(uuid.uuid4())

    # create conversation object
    m_conversation = {
        "_id": m_conversation_id,
        "conversationId": m_conversation_uuid,
        "user": str(uid_s2m[s_conversation['user_id']]),
        '__v': 0,  # Default value
        "_meiliIndex": True,
        "chatGptLabel": None,  # Default value
        "createdAt": datetime.fromisoformat(s_conversation['created_at']),
        "endpoint": 'openAI',  # Default value
        "frequency_penalty": 0,  # Default value
        "imageDetail": 'auto',  # Default value
        "messages": [],
        "model": 'gpt-3.5-turbo',  # Default value
        "presence_penalty": 0,  # Default value
        "promptPrefix": None,  # Default value
        "resendFiles": True,  # Default value
        "temperature": 1,  # Default value
        "title": s_conversation['topic'],
        "top_p": 1,  # Default value
        "updatedAt": datetime.fromisoformat(s_conversation['created_at']),
        }
    
    
    # save conversation mapping
    cids[s_conversation_id] = m_conversation_id
    cids[m_conversation_id] = s_conversation_id


    # create LibreChat messages
    for s_message_id in s_conversation['messages']:

        # get message
        s_message = messages[s_message_id]

        # generate new message ids
        m_message_id = ObjectId()
        m_message_uuid = str(uuid.uuid4())

        # create message object
        m_message = {
            "_id": m_message_id,
            "messageId": m_message_uuid,
            "__v": 0,  # Default value
            "_meiliIndex": True,
            "conversationId": m_conversation_uuid,
            "user": str(uid_s2m[s_message['user_id']]),
            "error": False,  # Default value
            "text": s_message['message'],
            "createdAt": datetime.fromisoformat(s_message['created_at']),
            "updatedAt": datetime.fromisoformat(s_message['created_at']),
            "isEdited": False,  # Default value
            "unfinished": False,  # Default value
            "endpoint": 'openAI',  # Default value
            "tokenCount": s_message['tokens'],
            }

        # add sender specific fields
        if row['is_bot']:
            m_message.update({
                "model": "gpt-3.5-turbo",  # Default value
                "isCreatedByUser": False,  # Default value
                "finish_reason": 'stop',  # Default value
                "sender": 'GPT-3.5',  # Default value
            })

        else:
            m_message.update({
                "model": None,  # Default value
                "isCreatedByUser": True,  # Default value,
                "sender": 'User',
            })

        # save message mapping
        mids[s_message_id]   = {"m_id": m_message_id, "m_uuid":m_message_uuid}
        mids[m_message_id]   = {"s_id": s_message_id, "m_uuid": m_message_uuid}
        mids[m_message_uuid] = {"s_id": s_message_id, "m_id": m_message_id}

        # add parent message if exists
        if m_conversation['messages']:
            m_message.update({
                "parentMessageId": mids[m_conversation['messages'][-1]]['m_uuid']
            })

        else:
            # add default parent message if it is the first message in the conversation
            m_message.update({
                "parentMessageId": '00000000-0000-0000-0000-000000000000'
            })

        # add message to conversation
        m_conversation['messages'].append(m_message_id)





        # Insert into MongoDB
        mdb_messages.insert_one(m_message)

    # Insert into MongoDB
    mdb_conversations.insert_one(m_conversation)


