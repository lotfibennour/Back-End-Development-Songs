from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"}), 200

@app.route("/count", methods=['GET'])
def count():
    """Return the length of data (i.e., count of documents in the collection)"""
    count = db.songs.count_documents({})  # Count all documents in the collection
    return jsonify({"count": count}), 200  # Return the count with an HTTP 200 OK response code

@app.route('/song', methods=['GET'])
def get_songs():
    songs = list(db.songs.find({}))
    
    # Convert ObjectId to string
    for song in songs:
        song['_id'] = str(song['_id'])
    
    return jsonify({"songs": songs})

@app.route('/song/<int:id>', methods=['GET'])
def get_song_by_id(id):
    song = db.songs.find_one({"id": id})
    
    if song:
        # Convert the song to JSON and remove the _id field
        song_json = json.loads(json_util.dumps(song))
        song_json.pop('_id', None)
        return jsonify(song_json), 200
    else:
        return jsonify({"message": "song with id not found"}), 404

@app.route('/song', methods=['POST'])
def create_song():
    song_data = request.json
    
    # Check if a song with the given id already exists
    existing_song = db.songs.find_one({"id": song_data['id']})
    if existing_song:
        return jsonify({"Message": f"song with id {song_data['id']} already present"}), 302

    # Insert the new song
    result = db.songs.insert_one(song_data)
    
    # Prepare the response
    inserted_id = json.loads(json_util.dumps(result.inserted_id))
    return jsonify({"inserted id": inserted_id}), 201

@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    song_data = request.json
    
    # Find the song in the database
    existing_song = db.songs.find_one({"id": id})
    
    if existing_song:
        # Update the song
        result = db.songs.update_one(
            {"id": id},
            {"$set": song_data}
        )
        
        if result.modified_count > 0:
            # If the song was modified, return the updated song
            updated_song = db.songs.find_one({"id": id})
            return json.loads(json_util.dumps(updated_song)), 201
        else:
            # If no changes were made
            return jsonify({"message": "song found, but nothing updated"}), 200
    else:
        # If the song doesn't exist
        return jsonify({"message": "song not found"}), 404

@app.route('/song/<int:id>', methods=['DELETE'])
def delete_song(id):
    # Delete the song from the database
    result = db.songs.delete_one({"id": id})
    
    if result.deleted_count == 1:
        # If the song was successfully deleted
        return '', 204
    else:
        # If the song was not found
        return jsonify({"message": "song not found"}), 404