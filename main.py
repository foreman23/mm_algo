import os

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import auth

from datetime import datetime

from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()


def getWaitingPool():
    """
    Returns the current uids in the waiting pool from firestore
    """
    doc_ref = db.collection("pairing_system").document("waiting")
    doc = doc_ref.get()
    if doc.exists:
        waitingPool = doc.to_dict()
        return waitingPool

    else:
        print("No such document!")


@app.route("/match")
def pairUsers():
    """
    Pairs users from the waiting pool
    """
    waitingPool = getWaitingPool()
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
        doc_ref2 = db.collection("pairing_system").document("pairs")

        # Get the document data
        doc_data = doc_ref2.get().to_dict()

        # Append the uids to new array within pairs document
        pairID = pair[0] + "_" + pair[1]

        # Check if matched with this user previously
        if (pairID in doc_data or (pair[1] + "_" + pair[0]) in doc_data):
            return "Duplicate match! Trying again.."

        # Remove uids from the waiting list
        print("DELETING uids from pairing_system/waiting/uidArr")
        doc_ref.update({"uidArr": firestore.ArrayRemove([pair[0]])})
        doc_ref.update({"uidArr": firestore.ArrayRemove([pair[1]])})


        # Create empty map with uid arrays for holding user messages
        doc_ref2.update({
            pairID: {
                pair[0]: [],
                pair[1]: [],
            }
        })

        # Create a timestamp for last found match in users' firestore docs
        timestampMatchFound(pair[0], pair[1], pairID)

        return "Pair found!"

    else:
        return "Could not find pair..."


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


@app.route("/")
def greeting():
    return "<p>Valid routes: /match</p>"

@app.route("/test")
def test():
    return "test"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

