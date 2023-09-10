import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import auth

import asyncio


from datetime import datetime

from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

@firestore.transactional
def getWaitingPool(transaction):
    """
    Returns the current uids in the waiting pool from firestore
    """
    doc_ref = db.collection("pairing_system").document("waiting")
    snapshot = doc_ref.get(transaction=transaction)
    # doc = doc_ref.get()
    if snapshot.exists:
        waitingPool = snapshot.to_dict()
        return waitingPool

    else:
        print("No such document!")


def timestampMatchFound(uid1, uid2, pairID):
    dt = datetime.utcnow()

    # Dictionary for pairID and dt
    pair_info = {
        "pairID": pairID,
        "timestamp": dt
    }

    # Update or create the "matches" document in the "pairing" subcollection for user 1
    doc_ref_user1 = db.collection("userInfo").document(uid1)
    doc_ref_user1.collection("pairing").document("matches").set({}, merge=True)
    doc_ref_user1.collection("pairing").document("matches").update(
        {"pairArr": firestore.ArrayUnion([pair_info])})

    # Update or create the "matches" document in the "pairing" subcollection for user 2
    doc_ref_user2 = db.collection("userInfo").document(uid2)
    doc_ref_user2.collection("pairing").document("matches").set({}, merge=True)
    doc_ref_user2.collection("pairing").document("matches").update(
        {"pairArr": firestore.ArrayUnion([pair_info])})
    

async def createDocument(col_ref, pairID):
    data = {}
    chat_ref = col_ref.document(pairID)
    chat_ref.set(data)

async def createSubCollection(pairID):
    chat_ref = db.collection("chat_rooms").document(pairID)
    dummy_doc_ref = chat_ref.collection('messages').document('(dummy_message)')
    dummy_doc_ref.set({})


@app.route("/match")
async def pairUsers():
    """
    Pairs users from the waiting pool
    """
    transaction = db.transaction()
    waitingPool = getWaitingPool(transaction)
    pair = []
    for uid in waitingPool["uidArr"]:
        print("Pairing...")
        if len(pair) == 2:
            break
        else:
            pair.append(uid)
    if len(pair) == 2:
        print("Pair found:", pair[0], ":", pair[1])

        doc_ref = db.collection("pairing_system").document("waiting")
        col_ref = db.collection("chat_rooms")

        # Get the document data
        # doc_data = doc_ref2.get().to_dict()

        # Append the uids to new array within pairs document
        pairID = pair[0] + "_" + pair[1]

        # Check if matched with this user previously
        # if (pairID in doc_data or (pair[1] + "_" + pair[0]) in doc_data):
        #     return "Duplicate match! Trying again.."

        # Query db to check if matched with this user previously
        query_ref = col_ref.document(pairID)
        query = query_ref.get()
        if query.exists:
            return "Duplicate match! Trying again.."
        query_ref2 = col_ref.document(pair[1] + "_" + pair[0])
        query2 = query_ref2.get()
        if query2.exists:
            return "Duplicate match! Trying again.."

        # Remove uids from the waiting list
        print("DELETING uids from pairing_system/waiting/uidArr")
        doc_ref.update({"uidArr": firestore.ArrayRemove([pair[0]])})
        doc_ref.update({"uidArr": firestore.ArrayRemove([pair[1]])})

        # Create new chat document within chat_rooms collection
        await createDocument(col_ref, pairID)

        # Call function to create subcollection
        await createSubCollection(pairID)

        # Create a timestamp for last found match in users' firestore docs
        timestampMatchFound(pair[0], pair[1], pairID)

        return "Pair found!"

    else:
        return "Could not find pair..."


@app.route("/")
def greeting():
    return "<p>Valid routes: /match</p>"


@app.route("/test")
def test():
    return "test"
